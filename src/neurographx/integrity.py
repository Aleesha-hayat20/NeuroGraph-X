"""Integrity check: do the logs, the registry, the checkpoints and the data agree?

Several people write to the run log, the model registry, the analysis log and the
checkpoints, on Kaggle, on laptops and in CI. This module checks that they still describe
one consistent system (work plan Section 2.2 and Week 6; memos 0008, 0009, 0011, 0013):

1. Run log          every line is a record; every run_id is unique (the union merge of
                    memo 0013 keeps lines from both branches, so duplicates are possible).
2. Models           every registry entry names a final run of its atlas in the run log,
                    the same checkpoint path, a checkpoint file whose SHA-256 is the one
                    the run recorded, and the run's own frozen-set metrics; every archived
                    run (previous_run_ids) is in the run log.
3. Training files   for every served run (registered or archived) and its cross-validation
                    run: the folds and frozen files and the out-of-fold file match the
                    hashes recorded in the run log; each calibration file names its run and
                    the out-of-fold file it was fitted on (memo 0010).
4. Cohort           the frozen set and the development folds are disjoint and together are
                    the QC cohort; every participant in the phenotypic table is in exactly
                    one of the QC cohort and the exclusion log (memo 0013, part 3).
5. Connectomes      each stored atlas matches its own manifest; the manifest hash is the one
                    the served runs recorded, or, for a store built on another machine,
                    the replay below shows the models get the same inputs.
6. Replay           (needs PyTorch) each registered model, run again on this machine on the
                    participants of its saved frozen-set predictions, gives the same
                    probabilities within 0.001 (memo 0009, section 4). Labels are not read
                    and nothing is scored, so this is not a frozen-set measurement.
7. Analysis log     every record is valid (memo 0013, part 2), every analysis_id unique,
                    every analysis made by a registered or archived run of its atlas, every
                    regenerated analysis points to an earlier one with the same participant,
                    atlas and run.

Why a different connectome hash is not on its own a failure: the arrays are what the
model reads, but the hash is of the .npz file, and the same arrays saved by different
numpy versions give different file bytes. (Checked on 8 November 2026: the Mac's HO store
and a rebuild with numpy 2.0.2 hold bit-identical arrays and have different file hashes.)
The replay checks what matters, the model's inputs, through the model itself.

Text files are compared with either line ending (LF or CRLF), because a checkout on
Windows rewrites line endings and the run log holds whichever version the training
session saw. Any other difference in content still fails.

Usage: scripts/check_integrity.py (exit status 0 only when nothing fails).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from neurographx import analysis_log, datasource

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"
REPLAY_TOLERANCE = 0.001  # memo 0009, section 4: CPU and GPU differ in the last decimals


@dataclass
class Finding:
    status: str
    section: str
    message: str


@dataclass
class Report:
    root: Path
    mode: str
    findings: list[Finding] = field(default_factory=list)

    def add(self, status: str, section: str, message: str) -> None:
        self.findings.append(Finding(status, section, message))

    def count(self, status: str) -> int:
        return sum(f.status == status for f in self.findings)

    @property
    def ok(self) -> bool:
        return self.count(FAIL) == 0

    def lines(self, verbose: bool = True) -> list[str]:
        """The printed report: one line per finding, grouped by section, then a summary."""
        out = [f"NeuroGraph-X integrity check ({self.mode} data: {self.root})"]
        section = None
        for f in self.findings:
            if not verbose and f.status == PASS:
                continue
            if f.section != section:
                section = f.section
                out.append("")
                out.append(section)
            out.append(f"  {f.status}  {f.message}")
        out.append("")
        verdict = "passed" if self.ok else "FAILED"
        out.append(f"Integrity check {verdict}: {self.count(PASS)} passed, "
                   f"{self.count(FAIL)} failed, {self.count(WARN)} warnings.")
        return out


# ---------------------------------------------------------------------------
# Hashes
# ---------------------------------------------------------------------------

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def text_hash_matches(path: Path, logged: str) -> bool:
    """True if the file's SHA-256, with LF or with CRLF line endings, is `logged`."""
    data = Path(path).read_bytes()
    lf = data.replace(b"\r\n", b"\n")
    variants = (data, lf, lf.replace(b"\n", b"\r\n"))
    return logged in {hashlib.sha256(v).hexdigest() for v in variants}


# ---------------------------------------------------------------------------
# Reading the logs without trusting them
# ---------------------------------------------------------------------------

def _read_jsonl(path: Path) -> tuple[list[dict], list[int]]:
    """Records and the line numbers that are not JSON objects (blank lines are ignored)."""
    records, bad = [], []
    if not path.exists():
        return records, bad
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            bad.append(number)
            continue
        if isinstance(value, dict):
            records.append(value)
        else:
            bad.append(number)
    return records, bad


def _duplicates(values: Iterable[str]) -> list[str]:
    seen, dup = set(), set()
    for v in values:
        (dup if v in seen else seen).add(v)
    return sorted(dup)


def _relative(path: Path, root: Path) -> str:
    try:
        return str(Path(path).relative_to(root))
    except ValueError:
        return str(path)


# ---------------------------------------------------------------------------
# The checks
# ---------------------------------------------------------------------------

class _Checker:
    def __init__(self, root: Path, mode: str, replay: bool):
        self.root = Path(root)
        self.report = Report(self.root, mode)
        self.replay_wanted = replay
        self.runs: dict[str, dict] = {}
        self.registry: dict[str, dict] = {}
        self.served: dict[str, dict] = {}       # run_id -> run, registered or archived
        self.allowed: dict[str, set[str]] = {}  # atlas -> run_ids an analysis may name
        self.different_builds: dict[str, list[str]] = {}  # atlas_key -> run_ids
        self.replayed_ok: set[str] = set()

    # helpers ---------------------------------------------------------------
    def add(self, status: str, section: str, message: str) -> None:
        self.report.add(status, section, message)

    def path(self, relative: str | Path) -> Path:
        return datasource.checkpoint(relative, self.root)  # relative to the data root

    # 1 ---------------------------------------------------------------------
    def run_log(self) -> None:
        s = "1. Run log"
        path = datasource.run_log(self.root)
        if not path.exists():
            self.add(FAIL, s, f"{_relative(path, self.root)} not found")
            return
        records, bad = _read_jsonl(path)
        if bad:
            self.add(FAIL, s, f"lines that are not JSON records: {bad[:10]}")
        ids = [str(r.get("run_id")) for r in records]
        dup = _duplicates(ids)
        if dup:
            self.add(FAIL, s, f"run_id used more than once: {dup[:10]}")
        else:
            self.add(PASS, s, f"{len(records)} runs, every run_id unique")
        self.runs = {str(r.get("run_id")): r for r in records}

    # 2 ---------------------------------------------------------------------
    def models(self) -> None:
        s = "2. Registered models and checkpoints"
        path = datasource.model_registry(self.root)
        if not path.exists():
            self.add(FAIL, s, f"{_relative(path, self.root)} not found")
            return
        self.registry = json.loads(path.read_text(encoding="utf-8"))
        if not self.registry:
            self.add(WARN, s, "the registry is empty: no model is served")
        for atlas, entry in sorted(self.registry.items()):
            self._model(s, atlas, entry)

    def _model(self, s: str, atlas: str, entry: dict) -> None:
        run_id = entry.get("run_id")
        allowed = self.allowed.setdefault(atlas, set())
        if entry.get("atlas") != atlas:
            self.add(FAIL, s, f"{atlas}: entry says atlas {entry.get('atlas')!r}")
        run = self.runs.get(run_id)
        if run is None:
            self.add(FAIL, s, f"{atlas}: registered run {run_id} is not in the run log")
            return
        problems = []
        if run.get("stage") != "final":
            problems.append(f"its stage is {run.get('stage')!r}, not 'final'")
        if run.get("atlas") != atlas:
            problems.append(f"it was trained on atlas {run.get('atlas')!r}")
        if run.get("checkpoint_path") != entry.get("checkpoint_path"):
            problems.append(f"the registry names {entry.get('checkpoint_path')} but the run "
                            f"saved {run.get('checkpoint_path')}")
        if (entry.get("metrics") or {}).get("frozen") != (run.get("metrics") or {}).get("frozen"):
            problems.append("the registry's frozen-set metrics differ from the run's")
        if problems:
            self.add(FAIL, s, f"{atlas}: run {run_id}: " + "; ".join(problems))
        else:
            self.add(PASS, s, f"{atlas}: run {run_id} is a final {atlas} run; path and "
                              "metrics agree with the run log")
        self.served[run_id] = run
        allowed.add(run_id)
        self._checkpoint(s, atlas, run, required=True)

        for old in entry.get("previous_run_ids") or []:
            archived = self.runs.get(old)
            if archived is None:
                self.add(FAIL, s, f"{atlas}: archived run {old} is not in the run log")
                continue
            self.served[old] = archived
            allowed.add(old)
            self._checkpoint(s, atlas, archived, required=False)

    def _checkpoint(self, s: str, atlas: str, run: dict, required: bool) -> None:
        run_id, relative = run.get("run_id"), run.get("checkpoint_path")
        role = "registered" if required else "archived"
        if not relative:
            self.add(FAIL if required else WARN, s,
                     f"{atlas}: {role} run {run_id} saved no checkpoint")
            return
        ckpt = self.path(relative)
        if not ckpt.exists():
            if required:
                self.add(FAIL, s, f"{atlas}: checkpoint {relative} of run {run_id} is missing")
            else:
                self.add(WARN, s, f"{atlas}: archived run {run_id}: {relative} is not on this "
                                  "machine, so its analyses cannot be regenerated here")
            return
        logged = run.get("checkpoint_sha256")
        if logged is None:
            self.add(WARN, s, f"{atlas}: {role} run {run_id} recorded no checkpoint SHA-256 "
                              f"(schema {run.get('schema_version', 1)}); file present")
        elif sha256_file(ckpt) != logged:
            self.add(FAIL, s, f"{atlas}: {relative} does not match the SHA-256 run {run_id} "
                              "recorded")
        else:
            self.add(PASS, s, f"{atlas}: {relative} matches the SHA-256 of run {run_id}")

    # 3 ---------------------------------------------------------------------
    def training_files(self) -> None:
        s = "3. Training files recorded by the served runs"
        if not self.served:
            self.add(WARN, s, "no served runs to check")
            return
        cv_runs, matched = {}, []
        for run_id, run in sorted(self.served.items()):
            matched += self._data_files(s, run)
            cv_id = (run.get("metrics") or {}).get("cv_run_id")
            if cv_id:
                cv = self.runs.get(cv_id)
                if cv is None or cv.get("stage") != "cv":
                    self.add(FAIL, s, f"run {run_id}: its cross-validation run {cv_id} is not "
                                      "a cv run in the run log")
                else:
                    cv_runs[cv_id] = cv
            self._frozen_predictions(s, run)
        for cv_id, cv in sorted(cv_runs.items()):
            matched += self._data_files(s, cv)
            self._oof(s, cv)
        if matched:
            self.add(PASS, s, f"folds and frozen files match the hashes recorded by "
                              f"{len(matched)} runs: {', '.join(matched)}")
        for atlas, entry in sorted(self.registry.items()):
            self._calibration(s, atlas, entry)

    def _data_files(self, s: str, run: dict) -> list[str]:
        """[run_id] when every recorded split file matches; failures are reported here."""
        dc = run.get("data_config") or {}
        run_id = run.get("run_id")
        checked, failed = [], False
        for file_key, hash_key in (("folds_file", "folds_sha256"),
                                   ("frozen_file", "frozen_sha256")):
            if not dc.get(file_key) or not dc.get(hash_key):
                continue
            path = self.path(dc[file_key])
            if not path.exists():
                self.add(FAIL, s, f"run {run_id}: {dc[file_key]} not found")
                failed = True
            elif not text_hash_matches(path, dc[hash_key]):
                self.add(FAIL, s, f"run {run_id}: {dc[file_key]} differs from the file it "
                                  "trained with")
                failed = True
            else:
                checked.append(file_key)
        return [run_id] if checked and not failed else []

    def _frozen_predictions(self, s: str, run: dict) -> None:
        meta = ((run.get("metrics") or {}).get("frozen") or {}).get("predictions")
        if not meta:
            return
        path = self.path(meta["file"])
        if not path.exists():
            self.add(FAIL, s, f"run {run['run_id']}: {meta['file']} not found")
        elif not text_hash_matches(path, meta["sha256"]):
            self.add(FAIL, s, f"run {run['run_id']}: {meta['file']} does not match its hash")
        else:
            self.add(PASS, s, f"run {run['run_id']}: frozen-set predictions match their hash")

    def _oof(self, s: str, cv: dict) -> None:
        meta = (cv.get("metrics") or {}).get("oof")
        if not meta:
            self.add(WARN, s, f"cv run {cv['run_id']} saved no out-of-fold file (it predates "
                              "them; Week 4)")
            return
        path = self.path(meta["file"])
        if not path.exists():
            self.add(FAIL, s, f"cv run {cv['run_id']}: {meta['file']} not found")
        elif not text_hash_matches(path, meta["sha256"]):
            self.add(FAIL, s, f"cv run {cv['run_id']}: {meta['file']} does not match its hash")
        else:
            self.add(PASS, s, f"cv run {cv['run_id']}: out-of-fold file matches its hash")

    def _calibration(self, s: str, atlas: str, entry: dict) -> None:
        run_id = entry.get("run_id")
        path = datasource.model_registry(self.root).parent / "calibration" / \
            f"{atlas}_{run_id}.json"
        if not path.exists():
            self.add(WARN, s, f"{atlas}: no calibration file for run {run_id}; its analyses "
                              "are served uncalibrated")
            return
        cal = json.loads(path.read_text(encoding="utf-8"))
        problems = [f"{k} is {cal.get(k)!r}" for k, v in (("atlas", atlas), ("run_id", run_id))
                    if k in cal and cal[k] != v]
        cv_id = (self.runs.get(run_id, {}).get("metrics") or {}).get("cv_run_id")
        if "cv_run_id" in cal and cal["cv_run_id"] != cv_id:
            problems.append(f"fitted on cv run {cal['cv_run_id']}, not {cv_id}")
        oof = ((self.runs.get(cv_id) or {}).get("metrics") or {}).get("oof") or {}
        if "oof_sha256" in cal and cal["oof_sha256"] != oof.get("sha256"):  # memo 0010
            problems.append("fitted on an out-of-fold file other than the one its cv run "
                            "recorded")
        if problems:
            self.add(FAIL, s, f"{atlas}: calibration file of run {run_id}: " + "; ".join(problems))
        else:
            self.add(PASS, s, f"{atlas}: calibration file belongs to run {run_id} and was "
                              "fitted on its cv run's out-of-fold file")

    # 4 ---------------------------------------------------------------------
    def cohort(self) -> None:
        s = "4. Cohort and splits"
        paths = {"QC cohort": datasource.qc_cohort(self.root),
                 "exclusion log": datasource.exclusion_log(self.root),
                 "frozen set": datasource.frozen_set(self.root),
                 "development folds": datasource.cv_folds(self.root),
                 "phenotypic table": datasource.phenotypic_table(self.root)}
        missing = [name for name, p in paths.items() if not p.exists()]
        for name in missing:
            self.add(FAIL, s, f"{name} not found: {_relative(paths[name], self.root)}")
        if missing:
            return

        def ids(name: str) -> set[int]:
            return set(pd.read_csv(paths[name], usecols=["SUB_ID"])["SUB_ID"].astype(int))

        cohort, excluded = ids("QC cohort"), ids("exclusion log")
        frozen, development = ids("frozen set"), ids("development folds")
        table = ids("phenotypic table")

        overlap = frozen & development
        if overlap:
            self.add(FAIL, s, f"in both the frozen set and the folds: {sorted(overlap)[:10]}")
        elif frozen | development != cohort:
            self.add(FAIL, s, f"frozen set + folds ({len(frozen | development)}) is not the "
                              f"QC cohort ({len(cohort)})")
        else:
            self.add(PASS, s, f"frozen set ({len(frozen)}) and development folds "
                              f"({len(development)}) are disjoint and make up the QC cohort "
                              f"({len(cohort)})")
        both, neither = cohort & excluded, table - cohort - excluded
        extra = (cohort | excluded) - table
        if both or neither or extra:
            parts = []
            if both:
                parts.append(f"retained and excluded: {sorted(both)[:5]}")
            if neither:
                parts.append(f"in neither file: {sorted(neither)[:5]}")
            if extra:
                parts.append(f"not in the phenotypic table: {sorted(extra)[:5]}")
            self.add(FAIL, s, "participants out of place: " + "; ".join(parts))
        else:
            self.add(PASS, s, f"each of the {len(table)} participants is either retained "
                              f"({len(cohort)}) or excluded ({len(excluded)})")
        meta_path = datasource.frozen_meta(self.root)
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            if meta.get("frozen_sha256") and not text_hash_matches(paths["frozen set"],
                                                                   meta["frozen_sha256"]):
                self.add(FAIL, s, "the frozen set does not match the hash in its .meta.json")
            elif meta.get("frozen_sha256"):
                self.add(PASS, s, "the frozen set matches the hash in its .meta.json")

    # 5 ---------------------------------------------------------------------
    def connectomes(self) -> None:
        s = "5. Connectome store"
        from neurographx.m2_connectome.engine import atlas_paths

        pipeline = datasource.data_config(self.root)["pipeline"]  # memo 0002; no PyTorch

        by_key: dict[str, list[dict]] = {}
        for run in self.served.values():
            key = (run.get("data_config") or {}).get("atlas_key")
            if key:
                by_key.setdefault(key, []).append(run)
        if not by_key:
            self.add(WARN, s, "no served run records connectome settings")
        cdir = datasource.connectome_dir(self.root)
        for key, runs in sorted(by_key.items()):
            npz, manifest_path = atlas_paths(cdir, pipeline["name"], pipeline["strategy"],
                                             key)
            if not npz.exists() or not manifest_path.exists():
                self.add(FAIL, s, f"{key}: {_relative(npz, self.root)} or its manifest is "
                                  "missing")
                continue
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if sha256_file(npz) != manifest.get("output_sha256"):
                self.add(FAIL, s, f"{key}: the stored file does not match its own manifest "
                                  "(changed after it was built)")
                continue
            self.add(PASS, s, f"{key}: stored file matches its manifest "
                              f"({manifest.get('n_participants')} participants)")
            same = [r["run_id"] for r in runs
                    if r["data_config"].get("connectome_sha256") == manifest["output_sha256"]]
            other = sorted(r["run_id"] for r in runs if r["run_id"] not in same)
            if same:
                self.add(PASS, s, f"{key}: same build as run(s) {', '.join(sorted(same))}")
            if other:
                self.different_builds[key] = other

    # 6 ---------------------------------------------------------------------
    def replay(self) -> None:
        s = "6. Replay of the registered models on this machine"
        if not self.replay_wanted:
            self.add(WARN, s, "skipped (--no-replay)")
        else:
            try:
                import torch  # noqa: F401
                import torch_geometric  # noqa: F401
            except ImportError:
                self.add(WARN, s, "skipped: PyTorch or PyTorch Geometric is not installed")
            else:
                for atlas, entry in sorted(self.registry.items()):
                    self._replay_one(s, atlas, entry)
        registered = {e.get("run_id") for e in self.registry.values()}
        for key, run_ids in sorted(self.different_builds.items()):
            confirmed = [r for r in run_ids if r in self.replayed_ok]
            missing = [r for r in run_ids if r not in self.replayed_ok and r in registered]
            archived = [r for r in run_ids if r not in self.replayed_ok and r not in registered]
            if confirmed:
                self.add(PASS, s, f"{key}: built on another machine than run(s) "
                                  f"{', '.join(confirmed)}, and the replay gives the same "
                                  "probabilities, so the models get the same inputs")
            if missing:
                self.add(FAIL, s, f"{key}: the stored file is not the build run(s) "
                                  f"{', '.join(missing)} trained on, and no replay "
                                  "confirmed the same inputs")
            if archived:
                self.add(WARN, s, f"{key}: archived run(s) {', '.join(archived)} trained on "
                                  "another build of this store and are not replayed")

    def _replay_one(self, s: str, atlas: str, entry: dict) -> None:
        run = self.runs.get(entry.get("run_id"))
        meta = ((run or {}).get("metrics", {}).get("frozen") or {}).get("predictions")
        if run is None or not meta or not self.path(meta["file"]).exists():
            self.add(WARN, s, f"{atlas}: no saved frozen-set predictions to replay")
            return
        ckpt = self.path(run.get("checkpoint_path") or "")
        if not run.get("checkpoint_path") or not ckpt.exists():
            self.add(FAIL, s, f"{atlas}: cannot replay run {run['run_id']}: checkpoint missing")
            return
        from neurographx.api.analyses import graph_source
        from neurographx.m3_model.inference import load_model, predict_graph

        saved = pd.read_csv(self.path(meta["file"]), usecols=["SUB_ID", "prob_autism"])
        try:
            model, _ = load_model(atlas, datasource.model_registry(self.root), "cpu",
                                  entry=entry)
            get_graph = graph_source(run, self.root)
            worst = 0.0
            for sub_id, saved_p in zip(saved["SUB_ID"], saved["prob_autism"], strict=True):
                label, confidence = predict_graph(model, get_graph(f"{int(sub_id):07d}"))
                p_autism = confidence if label == 1 else 1.0 - confidence
                worst = max(worst, abs(p_autism - float(saved_p)))
        except (KeyError, ValueError, FileNotFoundError) as err:
            self.add(FAIL, s, f"{atlas}: replay of run {run['run_id']} failed: {err}")
            return
        if worst <= REPLAY_TOLERANCE:
            self.replayed_ok.add(run["run_id"])
            self.add(PASS, s, f"{atlas}: run {run['run_id']} gives the saved probabilities for "
                              f"all {len(saved)} participants (largest difference "
                              f"{worst:.6f}, tolerance {REPLAY_TOLERANCE})")
        else:
            self.add(FAIL, s, f"{atlas}: run {run['run_id']} differs from its saved "
                              f"probabilities by up to {worst:.4f} (tolerance "
                              f"{REPLAY_TOLERANCE})")

    # 7 ---------------------------------------------------------------------
    def analyses(self) -> None:
        s = "7. Analysis log"
        path = datasource.analysis_log(self.root)
        if not path.exists():
            self.add(PASS, s, "no analyses recorded yet")
            return
        records, bad = _read_jsonl(path)
        if bad:
            self.add(FAIL, s, f"lines that are not JSON records: {bad[:10]}")
        problems = []
        seen: dict[str, dict] = {}
        for i, rec in enumerate(records, 1):
            aid = rec.get("analysis_id")
            try:
                analysis_log.validate(rec)
            except analysis_log.AnalysisLogError as err:
                problems.append(f"record {i}: {err}")
                continue
            if aid in seen:
                problems.append(f"analysis_id {aid} is used more than once")
            run = self.runs.get(rec["run_id"])
            if run is None:
                problems.append(f"{aid}: run {rec['run_id']} is not in the run log")
            elif rec["run_id"] not in self.allowed.get(rec["atlas"], set()):
                problems.append(f"{aid}: run {rec['run_id']} is neither registered nor "
                                f"archived for atlas {rec['atlas']}")
            elif run.get("atlas") != rec["atlas"]:
                problems.append(f"{aid}: run {rec['run_id']} is a {run.get('atlas')} model")
            rep = rec["reproduces_analysis_id"]
            if rep is not None:
                first = seen.get(rep)
                if first is None:
                    problems.append(f"{aid} reproduces {rep}, which is not an earlier record")
                elif any(first[k] != rec[k] for k in ("participant_id", "atlas", "run_id")):
                    problems.append(f"{aid} reproduces {rep} but with another participant, "
                                    "atlas or run")
            seen.setdefault(aid, rec)
        if problems:
            for p in problems[:20]:
                self.add(FAIL, s, p)
        else:
            n_rep = sum(r.get("reproduces_analysis_id") is not None for r in records)
            self.add(PASS, s, f"{len(records)} analyses ({n_rep} regenerated): valid, unique, "
                              "each made by a registered or archived run of its atlas")


def check(root: Path | None = None, mode: str | None = None, replay: bool = True) -> Report:
    """Run every check on the dataset at `root` (default: the active data mode's root)."""
    mode = mode or datasource.mode()
    root = Path(root) if root is not None else datasource.data_root(mode)
    c = _Checker(root, mode, replay)
    c.run_log()
    c.models()
    c.training_files()
    c.cohort()
    c.connectomes()
    c.replay()
    c.analyses()
    return c.report
