"""The fixture dataset (decision memo 0014): a small SYNTHETIC cohort in the real file formats.

A "fixture" is a small, fake, fixed dataset that tests, CI and the dashboard can run on
without the 1 GB of real ABIDE data. Nothing in it describes a real person.

What makes it trustworthy is that only the *inputs* are invented. Every output file is
written by the same project code that wrote the real one:

    invented here                           written by the real project code
    -------------------------------------   ------------------------------------------------
    phenotypic table (106 real columns)     QC cohort + exclusion log      m1_ingestion.qc
    region time series (temporary .1D)      frozen set + meta, CV folds    m1_ingestion.splits
                                            connectome .npz + manifest     m2_connectome.engine
                                            run log, registry              m3_model.run_logger
                                            checkpoint                     m3_model.model (GCN)

The layout under the output folder mirrors the repository, so `NGX_DATA=fixtures`
only changes the root folder (see neurographx.datasource).

Regenerate with:  python scripts/build_fixtures.py --force
"""

from __future__ import annotations

import json
import shutil
import statistics
import tempfile
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from neurographx.config import load
from neurographx.m1_ingestion import metadata as md
from neurographx.m1_ingestion.qc import apply_qc
from neurographx.m1_ingestion.splits import (
    assert_no_leakage,
    make_folds,
    sha256_text,
    stratified_draw,
    write_frozen,
)
from neurographx.m2_connectome.engine import ENGINE_VERSION, build_atlas, sha256_file

GENERATOR_VERSION = "1.0.0"
SEED = 20261024

# The 106 columns of Phenotypic_V1_0b_preprocessed1.csv, in file order, as listed in
# docs/reports/metadata_report.md section 8. A test compares the two.
PHENOTYPIC_COLUMNS = [
    "Unnamed: 0.1", "Unnamed: 0", "SUB_ID", "X", "subject", "SITE_ID", "FILE_ID",
    "DX_GROUP", "DSM_IV_TR", "AGE_AT_SCAN", "SEX", "HANDEDNESS_CATEGORY",
    "HANDEDNESS_SCORES", "FIQ", "VIQ", "PIQ", "FIQ_TEST_TYPE", "VIQ_TEST_TYPE",
    "PIQ_TEST_TYPE", "ADI_R_SOCIAL_TOTAL_A", "ADI_R_VERBAL_TOTAL_BV", "ADI_RRB_TOTAL_C",
    "ADI_R_ONSET_TOTAL_D", "ADI_R_RSRCH_RELIABLE", "ADOS_MODULE", "ADOS_TOTAL",
    "ADOS_COMM", "ADOS_SOCIAL", "ADOS_STEREO_BEHAV", "ADOS_RSRCH_RELIABLE",
    "ADOS_GOTHAM_SOCAFFECT", "ADOS_GOTHAM_RRB", "ADOS_GOTHAM_TOTAL",
    "ADOS_GOTHAM_SEVERITY", "SRS_VERSION", "SRS_RAW_TOTAL", "SRS_AWARENESS",
    "SRS_COGNITION", "SRS_COMMUNICATION", "SRS_MOTIVATION", "SRS_MANNERISMS",
    "SCQ_TOTAL", "AQ_TOTAL", "COMORBIDITY", "CURRENT_MED_STATUS", "MEDICATION_NAME",
    "OFF_STIMULANTS_AT_SCAN", "VINELAND_RECEPTIVE_V_SCALED",
    "VINELAND_EXPRESSIVE_V_SCALED", "VINELAND_WRITTEN_V_SCALED",
    "VINELAND_COMMUNICATION_STANDARD", "VINELAND_PERSONAL_V_SCALED",
    "VINELAND_DOMESTIC_V_SCALED", "VINELAND_COMMUNITY_V_SCALED",
    "VINELAND_DAILYLVNG_STANDARD", "VINELAND_INTERPERSONAL_V_SCALED",
    "VINELAND_PLAY_V_SCALED", "VINELAND_COPING_V_SCALED", "VINELAND_SOCIAL_STANDARD",
    "VINELAND_SUM_SCORES", "VINELAND_ABC_STANDARD", "VINELAND_INFORMANT", "WISC_IV_VCI",
    "WISC_IV_PRI", "WISC_IV_WMI", "WISC_IV_PSI", "WISC_IV_SIM_SCALED",
    "WISC_IV_VOCAB_SCALED", "WISC_IV_INFO_SCALED", "WISC_IV_BLK_DSN_SCALED",
    "WISC_IV_PIC_CON_SCALED", "WISC_IV_MATRIX_SCALED", "WISC_IV_DIGIT_SPAN_SCALED",
    "WISC_IV_LET_NUM_SCALED", "WISC_IV_CODING_SCALED", "WISC_IV_SYM_SCALED",
    "EYE_STATUS_AT_SCAN", "AGE_AT_MPRAGE", "BMI", "anat_cnr", "anat_efc", "anat_fber",
    "anat_fwhm", "anat_qi1", "anat_snr", "func_efc", "func_fber", "func_fwhm",
    "func_dvars", "func_outlier", "func_quality", "func_mean_fd", "func_num_fd",
    "func_perc_fd", "func_gsr", "qc_rater_1", "qc_notes_rater_1", "qc_anat_rater_2",
    "qc_anat_notes_rater_2", "qc_func_rater_2", "qc_func_notes_rater_2",
    "qc_anat_rater_3", "qc_anat_notes_rater_3", "qc_func_rater_3",
    "qc_func_notes_rater_3", "SUB_IN_SMP",
]

# Three invented sites: SITE_ID, FILE_ID prefix (differs in case, as PITT / Pitt_ does in
# ABIDE), and scan length in timepoints (real lengths vary by site, 78 to 316).
SITES = [("SYN_A", "SynA", 100), ("SYN_B", "SynB", 120), ("SYN_C", "SynC", 150)]
PER_SITE = 8                    # 4 autism + 4 control per site, 24 participants in all
FIRST_SUB_ID = 90001            # the real file's 1,112 SUB_IDs run 50002 to 51607

# Real region counts per atlas (memo 0001, docs/reports/atlas_summary.md).
REGION_COUNTS = {"rois_aal": 116, "rois_cc200": 200, "rois_ho": 111,
                 "rois_dosenbach160": 161}
CONNECTOME_ATLASES = ("rois_cc200", "rois_ho")    # stored connectomes: two atlases
MODEL_ATLAS = "rois_cc200"                        # the tiny registered model

FROZEN_SIZE = 6        # one per (site, group) cell
DATASET_NAME = "synthetic_fixture"

# Planted quality-control cases. Every gate and every edge of a rule appears once.
EXCLUDED = {
    90007: {"FILE_ID": "no_filename", "qc_rater_1": "fail", "qc_func_rater_2": "fail",
            "qc_func_rater_3": "fail"},            # like ABIDE 50002: no data, three fails
    90008: {"qc_func_rater_2": "fail"},             # one rater fails
    90015: {"qc_anat_rater_3": "fail"},             # a different rater fails
    90016: {"func_mean_fd": 0.62},                  # head motion above 0.5 mm
    90023: {"func_mean_fd": None},                  # head motion missing
    90024: {"qc_rater_1": "maybe", "func_mean_fd": 0.71},  # two gates; "maybe" not OK for rater 1
}
RETAINED_EDGE_CASES = {
    90002: {"qc_anat_rater_2": "maybe"},            # "maybe" accepted for rater 2
    90003: {"qc_func_rater_2": "maybe"},
    90010: {"func_mean_fd": 0.5},                   # exactly at the limit: accepted
}
# Flat (zero-variance) regions, 0-based column indices, per participant and atlas.
FLAT_REGIONS = {
    ("rois_cc200", 90011): [7],
    ("rois_ho", 90005): [0, 1, 2],
    ("rois_ho", 90020): [57],
}

# Tiny model: small enough to train in seconds on a laptop CPU.
MODEL_HYPERPARAMETERS = {"hidden": 8, "layers": 2, "dropout": 0.2, "lr": 0.02,
                         "batch_size": 4, "epochs": 60}
MODEL_SEED = 42
DENSITY = 0.10
FILL_NAN = 0.0

# Files that are written at run time in fixture mode and never committed.
RUNTIME_FILES = ("runs/analysis_log.jsonl",)


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------

def make_phenotypic(seed: int = SEED) -> pd.DataFrame:
    """24 invented participants with the 106 real column names, in the real order.

    Only the columns the project reads are filled. Every other column is left empty,
    which is how missing values already appear for many columns of the real file.
    """
    rng = np.random.default_rng(seed)
    rows = []
    for s, (site, prefix, n_tp) in enumerate(SITES):
        for i in range(PER_SITE):
            sub_id = FIRST_SUB_ID + PER_SITE * s + i
            row = dict.fromkeys(PHENOTYPIC_COLUMNS)
            row.update({
                "Unnamed: 0.1": len(rows), "Unnamed: 0": len(rows), "X": len(rows) + 1,
                "SUB_ID": sub_id, "subject": sub_id, "SITE_ID": site,
                "FILE_ID": f"{prefix}_{sub_id:07d}",
                "DX_GROUP": 1 if i % 2 == 0 else 2,
                "AGE_AT_SCAN": round(float(rng.uniform(7.0, 35.0)), 2),
                "SEX": int(rng.choice([1, 2], p=[0.8, 0.2])),
                "func_mean_fd": round(float(rng.uniform(0.03, 0.3)), 4),
                "qc_rater_1": "OK", "qc_anat_rater_2": "OK", "qc_func_rater_2": "OK",
                "qc_anat_rater_3": "OK", "qc_func_rater_3": "OK",
                "SUB_IN_SMP": 1,
            })
            row.update(EXCLUDED.get(sub_id, {}))
            row.update(RETAINED_EDGE_CASES.get(sub_id, {}))
            rows.append(row)
    return pd.DataFrame(rows, columns=PHENOTYPIC_COLUMNS)


def make_timeseries(sub_id: int, dx_group: int, n_timepoints: int, n_regions: int,
                    atlas_key: str, seed: int = SEED) -> np.ndarray:
    """(timepoints, regions) signal: seven latent networks plus noise.

    Autism participants get weaker coupling in network 0, so the two groups differ a
    little and the tiny model has something to learn. This is NOT a model of autism;
    it only keeps the predictions from being constant.
    """
    rng = np.random.default_rng([seed, sub_id, REGION_COUNTS[atlas_key]])
    networks = np.arange(n_regions) % 7
    factors = rng.standard_normal((n_timepoints, 7))
    loading = np.full(n_regions, 0.6)
    if dx_group == 1:
        loading[networks == 0] = 0.3
    ts = factors[:, networks] * loading + rng.standard_normal((n_timepoints, n_regions))
    for column in FLAT_REGIONS.get((atlas_key, sub_id), []):
        ts[:, column] = 0.0
    return ts


def write_1d(path: Path, ts: np.ndarray) -> None:
    """A .1D file as ABIDE distributes them: a '#' header of labels, then one row per timepoint."""
    header = "\t".join(f"#{k}" for k in range(1, ts.shape[1] + 1))
    np.savetxt(path, ts, fmt="%.6f", delimiter="\t", header=header, comments="")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def fixture_config(real: dict[str, Any] | None = None) -> dict[str, Any]:
    """configs/data.yaml for the fixture: the real file with only the sizes changed."""
    cfg = json.loads(json.dumps(real if real is not None else load("data.yaml")))
    cfg["dataset"]["name"] = "ABIDE Preprocessed format, SYNTHETIC fixture (memo 0014)"
    fz = cfg["frozen_evaluation_set"]
    fz["size"] = FROZEN_SIZE
    fz["file"] = f"data/frozen/frozen_eval_{FROZEN_SIZE}.csv"
    fz["meta"] = f"data/frozen/frozen_eval_{FROZEN_SIZE}.meta.json"
    return cfg


# Keys whose values may differ between configs/data.yaml and the fixture's copy.
CONFIG_DIFFERENCES = {
    ("dataset", "name"),
    ("frozen_evaluation_set", "size"),
    ("frozen_evaluation_set", "file"),
    ("frozen_evaluation_set", "meta"),
}


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build(out: Path, train_model: bool = True, force: bool = False,
          log=print) -> dict[str, Any]:
    """Write the complete fixture dataset under `out`. Returns a summary."""
    out = Path(out)
    if out.exists() and any(out.iterdir()):
        if not force:
            raise FileExistsError(f"{out} is not empty. Pass force=True (--force) to rebuild.")
        if not (out / "MANIFEST.json").exists():
            # Safety: only ever delete a folder this generator wrote.
            raise FileExistsError(f"{out} has files but no MANIFEST.json, so it was not "
                                  "written by this generator. Refusing to delete it.")
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)

    real_cfg = load("data.yaml")
    qc_cfg = load("qc_criteria.yaml")          # the REAL rules, never a copy
    cfg = fixture_config(real_cfg)
    (out / "configs").mkdir()
    (out / "configs" / "data.yaml").write_text(
        "# SYNTHETIC FIXTURE configuration (decision memo 0014). Generated by\n"
        "# scripts/build_fixtures.py from configs/data.yaml; only the frozen-set size\n"
        "# and file names differ. Do not edit by hand: regenerate instead.\n"
        + yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")

    pipeline, strategy = cfg["pipeline"]["name"], cfg["pipeline"]["strategy"]
    atlases = {a["key"]: a for a in cfg["atlases"]}

    # 1. Phenotypic table
    pheno = make_phenotypic()
    raw = out / cfg["paths"]["raw"]
    raw.mkdir(parents=True)
    pheno_path = raw / cfg["dataset"]["phenotypic_file"]
    pheno.to_csv(pheno_path, index=False, lineterminator="\n")
    log(f"phenotypic table: {len(pheno)} participants, {pheno.shape[1]} columns")

    with tempfile.TemporaryDirectory() as tmp:
        # 2. Region time series for every participant with data, all four atlases
        ts_folder = Path(tmp) / "ABIDE_pcp" / pipeline / strategy
        ts_folder.mkdir(parents=True)
        site_length = {site: n for site, _, n in SITES}
        for row in pheno.itertuples(index=False):
            if row.FILE_ID == "no_filename":
                continue
            for key in atlases:
                ts = make_timeseries(row.SUB_ID, row.DX_GROUP, site_length[row.SITE_ID],
                                     REGION_COUNTS[key], key)
                write_1d(ts_folder / f"{row.FILE_ID}_{key}.1D", ts)

        # 3. Quality control, exactly as scripts/05_apply_qc.py does it
        df = md.load_phenotypic(pheno_path)
        cohort, excl = apply_qc(df, qc_cfg, ts_folder, list(atlases))
        cohort_path = out / cfg["cohort"]["file"]
        cohort_path.parent.mkdir(parents=True, exist_ok=True)
        cohort.to_csv(cohort_path, index=False, lineterminator="\n")
        excl_path = out / cfg["cohort"]["exclusion_log"]
        excl_path.parent.mkdir(parents=True, exist_ok=True)
        excl.to_csv(excl_path, index=False, lineterminator="\n")
        log(f"quality control: {len(cohort)} retained, {len(excl)} excluded")

        # 4. Frozen set and folds, exactly as scripts/06_draw_frozen_set.py does it
        fz, dv = cfg["frozen_evaluation_set"], cfg["development_splits"]
        frozen, table = stratified_draw(cohort, fz["size"], fz["stratify_by"], fz["seed"])
        write_frozen(frozen, table, out / fz["file"], out / fz["meta"], cohort_path,
                     fz["seed"], fz["stratify_by"])
        pool = cohort[~cohort["SUB_ID"].isin(frozen["SUB_ID"])]
        folds = make_folds(pool, dv["folds"], dv["stratify_by"], dv["seed"])
        assert_no_leakage(folds, frozen, context="fixture cv folds")
        folds.to_csv(out / dv["file"], index=False, lineterminator="\n")
        log(f"frozen set: {len(frozen)}; development pool: {len(pool)} in {dv['folds']} folds")

        # 5. Connectomes for two atlases, exactly as scripts/07_build_connectomes.py does it
        cc = cfg["connectome"]
        for key in CONNECTOME_ATLASES:
            cset, _ = build_atlas(key, cohort, ts_folder, out / cc["output_dir"], pipeline,
                                  strategy, clip=cc["fisher_clip"], dtype=cc["dtype"],
                                  force=True, label=atlases[key]["label"])
            log(f"connectomes {key}: {len(cset)} x {cset.n_regions} regions")

    # 6. The tiny registered model
    model = None
    if train_model:
        model = train_tiny_model(out, cfg, log=log)

    write_readme(out, cfg, cohort, excl, frozen, folds, model)
    manifest = write_manifest(out)
    log(f"manifest: {len(manifest['files'])} files hashed")
    return {"participants": len(pheno), "retained": len(cohort), "excluded": len(excl),
            "frozen": len(frozen), "development": len(pool), "model": model}


# ---------------------------------------------------------------------------
# Tiny model (needs PyTorch and PyTorch Geometric)
# ---------------------------------------------------------------------------

def _scores(model, graphs, device, batch_size):
    """The metrics scripts/train_gnn.py records, computed the same way."""
    import torch
    from sklearn.metrics import balanced_accuracy_score, confusion_matrix, roc_auc_score
    from torch_geometric.loader import DataLoader

    from neurographx.m3_model.training import evaluate

    acc, logits = evaluate(model, DataLoader(graphs, batch_size=batch_size), device)
    y = np.array([int(g.y) for g in graphs])
    prob_autism = torch.softmax(logits, dim=1)[:, 1].numpy()
    pred = logits.argmax(dim=1).numpy()
    with warnings.catch_warnings():  # a fold of 2 or 3 may hold one class only
        warnings.simplefilter("ignore", UserWarning)
        balanced = balanced_accuracy_score(y, pred)
    return {
        "n": int(len(y)),
        "accuracy": round(float(acc), 4),
        "balanced_accuracy": round(float(balanced), 4),
        "auc": round(float(roc_auc_score(y, prob_autism)), 4) if len(set(y)) == 2 else None,
        "majority_baseline": round(float(max(np.mean(y == 0), np.mean(y == 1))), 4),
        "confusion_tn_fp_fn_tp": confusion_matrix(y, pred, labels=[0, 1]).ravel().tolist(),
        "predicted_autism": int(pred.sum()),
    }, logits


def _fit(train, val, hp, device):
    import torch
    from torch_geometric.loader import DataLoader

    from neurographx.m3_model.model import GCN
    from neurographx.m3_model.training import evaluate, set_seed, train_epoch

    set_seed(MODEL_SEED)
    model = GCN(train[0].x.shape[1], hp["hidden"], 2, hp["layers"], hp["dropout"]).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=hp["lr"])
    loader = DataLoader(train, batch_size=hp["batch_size"], shuffle=True)
    best = {"acc": -1.0, "epoch": hp["epochs"], "state": None}
    for epoch in range(1, hp["epochs"] + 1):
        train_epoch(model, loader, optimizer, device)
        if val:
            acc, _ = evaluate(model, DataLoader(val, batch_size=hp["batch_size"]), device)
            if acc > best["acc"]:
                best = {"acc": acc, "epoch": epoch,
                        "state": {k: v.clone() for k, v in model.state_dict().items()}}
    if val:
        model.load_state_dict(best["state"])
    return model, best["epoch"]


def train_tiny_model(out: Path, cfg: dict, log=print) -> dict:
    """Cross-validate, train once on the development pool, measure the frozen set once,
    log both runs and register the model: the same steps as scripts/train_gnn.py."""
    import torch

    from neurographx.m2_connectome.engine import atlas_paths, load_atlas
    from neurographx.m3_model.data import build_graphs, short_atlas_name
    from neurographx.m3_model.model import model_from_checkpoint
    from neurographx.m3_model.run_logger import log_run, new_run_id, register_model

    device = torch.device("cpu")
    pipeline, strategy = cfg["pipeline"]["name"], cfg["pipeline"]["strategy"]
    npz, manifest = atlas_paths(out / cfg["connectome"]["output_dir"], pipeline, strategy,
                                MODEL_ATLAS)
    cset = load_atlas(npz, manifest)
    folds_file = cfg["development_splits"]["file"]
    frozen_file = cfg["frozen_evaluation_set"]["file"]
    folds = pd.read_csv(out / folds_file)
    frozen = pd.read_csv(out / frozen_file)
    assert_no_leakage(folds, frozen, context="fixture training")
    atlas = short_atlas_name(MODEL_ATLAS)
    log_path, registry_path = out / "runs" / "run_log.jsonl", out / "runs" / "model_registry.json"
    hp = dict(MODEL_HYPERPARAMETERS)
    data_config = {"atlas_key": MODEL_ATLAS, "density": DENSITY, "fill_nan": FILL_NAN,
                   "folds_file": folds_file, "folds_sha256": sha256_file(out / folds_file),
                   "frozen_file": frozen_file, "frozen_sha256": sha256_file(out / frozen_file),
                   "connectome_engine": cset.manifest.get("engine_version"),
                   "connectome_sha256": cset.manifest.get("output_sha256")}

    # Cross-validation on the development pool. The frozen set is not read.
    graphs = build_graphs(cset, folds, DENSITY, FILL_NAN)
    fold_of = folds["fold"].to_numpy()
    per_fold = []
    for k in sorted(set(fold_of)):
        train = [g for g, f in zip(graphs, fold_of) if f != k]
        val = [g for g, f in zip(graphs, fold_of) if f == k]
        model, best_epoch = _fit(train, val, hp, device)
        metrics, _ = _scores(model, val, device, hp["batch_size"])
        metrics["best_epoch"] = best_epoch
        per_fold.append(metrics)

    def summary(key):
        values = [m[key] for m in per_fold if m[key] is not None]
        if not values:
            return None
        return {"mean": round(statistics.mean(values), 4),
                "sd": round(statistics.stdev(values), 4) if len(values) > 1 else 0.0}

    cv_metrics = {"cv_accuracy": summary("accuracy"),
                  "cv_balanced_accuracy": summary("balanced_accuracy"),
                  "cv_auc": summary("auc"),
                  "cv_majority_baseline": summary("majority_baseline"),
                  "chosen_epochs": int(statistics.median(m["best_epoch"] for m in per_fold)),
                  "per_fold": per_fold}
    cv_id = log_run({"run_id": new_run_id(), "stage": "cv", "dataset": DATASET_NAME,
                     "atlas": atlas, "seed": MODEL_SEED, "hyperparameters": hp,
                     "metrics": cv_metrics, "data_config": data_config,
                     "split_sizes": {"development_pool": len(folds),
                                     "folds": len(per_fold)},
                     "checkpoint_path": "none (cross-validation)"}, log_path)
    log(f"tiny model, cross-validation run {cv_id}: accuracy {cv_metrics['cv_accuracy']}")

    # One final model on the whole pool. Unlike scripts/train_gnn.py it trains for the full
    # declared epochs: with validation folds of two or three participants, the epoch count
    # chosen by cross-validation is noise, and an under-trained model gives confidences so
    # close to 0.5 that a different CPU could flip a prediction.
    final_hp = dict(hp)
    model, _ = _fit(graphs, None, final_hp, device)
    run_id = new_run_id()
    ckpt_rel = Path("checkpoints") / f"{atlas}_{run_id}.pt"
    (out / ckpt_rel).parent.mkdir(parents=True, exist_ok=True)
    torch.save({"state_dict": model.state_dict(), "in_dim": cset.n_regions, "num_classes": 2,
                "hidden": hp["hidden"], "layers": hp["layers"], "dropout": hp["dropout"],
                "atlas": atlas, "atlas_key": MODEL_ATLAS, "density": DENSITY,
                "fill_nan": FILL_NAN, "run_id": run_id}, out / ckpt_rel)

    # The frozen set, measured once, on the reloaded checkpoint.
    frozen_graphs = build_graphs(cset, frozen, DENSITY, FILL_NAN)
    reloaded = model_from_checkpoint(torch.load(out / ckpt_rel, map_location="cpu"))
    frozen_metrics, logits_a = _scores(reloaded, frozen_graphs, device, hp["batch_size"])
    again = model_from_checkpoint(torch.load(out / ckpt_rel, map_location="cpu"))
    _, logits_b = _scores(again, frozen_graphs, device, hp["batch_size"])

    log_run({"run_id": run_id, "stage": "final", "dataset": DATASET_NAME, "atlas": atlas,
             "seed": MODEL_SEED, "hyperparameters": final_hp,
             "metrics": {"frozen": frozen_metrics, "cv_run_id": cv_id,
                         "cv_accuracy": cv_metrics["cv_accuracy"]},
             "data_config": data_config,
             "split_sizes": {"train": len(graphs), "frozen": len(frozen_graphs)},
             "checkpoint_path": ckpt_rel.as_posix(),
             "reload_identical": bool(torch.allclose(logits_a, logits_b, atol=1e-6)),
             "repeat_frozen_measurement": False}, log_path)
    register_model(run_id, log_path, registry_path)
    n_params = sum(p.numel() for p in model.parameters())
    log(f"tiny model, final run {run_id}: {n_params} parameters, registered for '{atlas}'")
    return {"atlas": atlas, "cv_run_id": cv_id, "run_id": run_id,
            "checkpoint": ckpt_rel.as_posix(), "parameters": n_params}


# ---------------------------------------------------------------------------
# README and manifest
# ---------------------------------------------------------------------------

def _hash(path: Path) -> str:
    """Text files are hashed with line endings normalised (a Windows checkout still matches)."""
    if path.suffix in {".csv", ".json", ".jsonl", ".md", ".yaml", ".yml"}:
        return sha256_text(path)
    return sha256_file(path)


def fixture_files(out: Path) -> list[Path]:
    """Every generated file, as paths relative to `out` (runtime files excluded)."""
    files = []
    for p in sorted(Path(out).rglob("*")):
        rel = p.relative_to(out)
        if p.is_file() and rel.as_posix() not in RUNTIME_FILES \
                and rel.as_posix() != "MANIFEST.json" and "__pycache__" not in rel.parts:
            files.append(rel)
    return files


def write_manifest(out: Path) -> dict:
    manifest = {
        "description": "SYNTHETIC fixture dataset, decision memo 0014. Regenerate with "
                       "scripts/build_fixtures.py; never edit files by hand.",
        "generator_version": GENERATOR_VERSION,
        "seed": SEED,
        "connectome_engine": ENGINE_VERSION,
        "files": {rel.as_posix(): _hash(out / rel) for rel in fixture_files(out)},
    }
    (out / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def manifest_problems(out: Path) -> list[str]:
    """Differences between the files on disk and MANIFEST.json. Empty means intact."""
    out = Path(out)
    recorded = json.loads((out / "MANIFEST.json").read_text(encoding="utf-8"))["files"]
    on_disk = {rel.as_posix() for rel in fixture_files(out)}
    problems = [f"missing: {f}" for f in sorted(set(recorded) - on_disk)]
    problems += [f"not in manifest: {f}" for f in sorted(on_disk - set(recorded))]
    problems += [f"changed: {f}" for f in sorted(set(recorded) & on_disk)
                 if _hash(out / f) != recorded[f]]
    return problems


def write_readme(out: Path, cfg: dict, cohort: pd.DataFrame, excl: pd.DataFrame,
                 frozen: pd.DataFrame, folds: pd.DataFrame, model: dict | None) -> None:
    gates = excl["first_gate_failed"].value_counts().to_dict()
    model_line = (f"- **Model:** {model['atlas']}, final run `{model['run_id']}` "
                  f"(cross-validation run `{model['cv_run_id']}`), {model['parameters']} "
                  f"parameters, checkpoint `{model['checkpoint']}`. "
                  "Harvard-Oxford has connectomes but no model, so the API's "
                  "\"no model registered\" path can be tested.\n"
                  if model else "- **Model:** not built (generated with --skip-model).\n")
    text = (
        "# Fixture dataset: SYNTHETIC, not real participants\n\n"
        "Generated by `scripts/build_fixtures.py` (decision memo 0014). Do not edit these "
        "files by hand: change `src/neurographx/fixture_data.py` and regenerate with\n"
        "`python scripts/build_fixtures.py --force`. `MANIFEST.json` holds the hash of every "
        "file and a test fails if any file no longer matches it.\n\n"
        "Use it with one setting: `NGX_DATA=fixtures` (see `src/neurographx/datasource.py`).\n\n"
        "## Contents\n\n"
        f"- **Participants:** {len(cohort) + len(excl)} invented people at 3 invented sites "
        f"(SUB_ID 90001 onwards), in the 106-column format of the real phenotypic file.\n"
        f"- **Quality control** (the real rules in `configs/qc_criteria.yaml`): "
        f"{len(cohort)} retained, {len(excl)} excluded "
        f"(rater {gates.get('rater', 0)}, motion {gates.get('motion', 0)}, "
        f"completeness {gates.get('completeness', 0)}).\n"
        f"- **Frozen set:** {len(frozen)} participants; **development pool:** {len(folds)} "
        f"in {cfg['development_splits']['folds']} folds.\n"
        f"- **Connectomes:** {', '.join(CONNECTOME_ATLASES)} with the real region counts "
        f"(200 and 111). AAL and Dosenbach 160 have no stored connectomes here, so the "
        f"\"data unavailable\" path can be tested.\n"
        + model_line +
        "\n## What the numbers mean\n\n"
        "Nothing. The time series are random signals with a small built-in group difference "
        "so the tiny model's predictions are not constant. No accuracy measured on this "
        "dataset may be reported anywhere.\n"
    )
    (out / "README.md").write_text(text, encoding="utf-8")
