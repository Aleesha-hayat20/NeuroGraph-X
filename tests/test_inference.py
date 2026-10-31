"""Tests for the inference path (L7), end to end on small synthetic graphs.

Skipped automatically where PyTorch or PyTorch Geometric is not installed.
"""
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("torch_geometric")

from neurographx.m3_model.inference import predict  # noqa: E402
from neurographx.m3_model.model import GCN  # noqa: E402
from neurographx.m3_model.run_logger import log_run, register_model  # noqa: E402
from neurographx.m3_model.synthetic_brain import make_dataset  # noqa: E402

N_ROIS = 20
ATLAS = f"synthetic{N_ROIS}"


@pytest.fixture
def setup(tmp_path):
    """A logged, registered checkpoint plus a participant -> graph lookup."""
    torch.manual_seed(0)
    graphs = {g.subject_id: g for g in make_dataset(n_subjects=6, n_rois=N_ROIS, seed=0)}
    model = GCN(N_ROIS, 8, 2, num_layers=2, dropout=0.5)
    ckpt_path = tmp_path / "model.pt"
    torch.save({"state_dict": model.state_dict(), "in_dim": N_ROIS, "num_classes": 2,
                "hidden": 8, "layers": 2, "dropout": 0.5}, ckpt_path)
    log, registry = tmp_path / "run_log.jsonl", tmp_path / "registry.json"
    run_id = log_run({"run_id": "abc12345", "dataset": "synthetic_brain", "atlas": ATLAS,
                      "seed": 0, "hyperparameters": {}, "metrics": {},
                      "checkpoint_path": str(ckpt_path)}, log)
    register_model(run_id, log, registry)
    return graphs.__getitem__, registry, run_id


def test_response_matches_the_contract(setup):
    get_graph, registry, run_id = setup
    out = predict("SYN_0000", ATLAS, get_graph, registry)
    assert set(out) == {"participant_id", "atlas", "prediction", "confidence",
                        "calibrated", "run_id"}
    assert out["participant_id"] == "SYN_0000"
    assert out["atlas"] == ATLAS
    assert out["prediction"] in {"autism", "control"}
    assert 0.5 <= out["confidence"] <= 1.0
    assert out["calibrated"] is False
    assert out["run_id"] == run_id


def test_same_participant_gives_same_answer(setup):
    get_graph, registry, _ = setup
    first = predict("SYN_0001", ATLAS, get_graph, registry)
    second = predict("SYN_0001", ATLAS, get_graph, registry)
    assert first == second  # dropout is off at inference


def test_unknown_atlas_is_an_error(setup):
    get_graph, registry, _ = setup
    with pytest.raises(KeyError, match="no model registered"):
        predict("SYN_0000", "cc200", get_graph, registry)


def test_unknown_participant_is_an_error(setup):
    get_graph, registry, _ = setup
    with pytest.raises(KeyError):
        predict("NOT_A_PARTICIPANT", ATLAS, get_graph, registry)


def test_graph_from_the_wrong_atlas_is_rejected(setup):
    _, registry, _ = setup
    wrong = make_dataset(n_subjects=1, n_rois=N_ROIS + 5, seed=1)[0]
    with pytest.raises(ValueError, match="expects"):
        predict("SYN_0000", ATLAS, lambda _pid: wrong, registry)


def test_nan_features_are_rejected(setup):
    get_graph, registry, _ = setup
    bad = get_graph("SYN_0002").clone()
    bad.x[0, 0] = float("nan")
    with pytest.raises(ValueError, match="NaN"):
        predict("SYN_0002", ATLAS, lambda _pid: bad, registry)


def test_missing_checkpoint_file_is_an_error(setup, tmp_path):
    get_graph, registry, _ = setup
    (tmp_path / "model.pt").unlink()
    with pytest.raises(FileNotFoundError):
        predict("SYN_0000", ATLAS, get_graph, registry)


def test_relative_checkpoint_resolves_against_the_registry_data_root(tmp_path, monkeypatch):
    """Memo 0009: a registry in <root>/runs/ finds <root>/checkpoints/ from any folder."""
    from neurographx.m3_model.inference import checkpoint_path, load_model

    root = tmp_path / "root"
    (root / "runs").mkdir(parents=True)
    (root / "checkpoints").mkdir()
    model = GCN(N_ROIS, 8, 2, num_layers=2, dropout=0.5)
    torch.save({"state_dict": model.state_dict(), "in_dim": N_ROIS, "num_classes": 2,
                "hidden": 8, "layers": 2, "dropout": 0.5}, root / "checkpoints" / "m.pt")
    log, registry = root / "runs" / "run_log.jsonl", root / "runs" / "model_registry.json"
    log_run({"run_id": "rel12345", "dataset": "synthetic_brain", "atlas": ATLAS, "seed": 0,
             "hyperparameters": {}, "metrics": {}, "checkpoint_path": "checkpoints/m.pt"}, log)
    entry = register_model("rel12345", log, registry)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    assert checkpoint_path(entry, registry) == root / "checkpoints" / "m.pt"
    loaded, _ = load_model(ATLAS, registry)
    assert not loaded.training  # eval mode: dropout off
