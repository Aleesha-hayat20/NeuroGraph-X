"""POST /analyses, the model side (memo 0013, parts 3 and 4; backlog W5-09, card #73).

One analysis is three calls, exactly as memo 0013 names them, and this module writes
nothing itself:

    1. api.analysis_checks.check_request(participant_id, atlas)
           the five checks of part 4, in their fixed order (422, 404, 409, 503, 503);
    2. m3_model.inference.predict(...)
           the registered model for the atlas, on the graph built with the settings that
           model was trained with (from its run in the run log), calibrated when the run
           has a calibration file (memo 0010);
    3. analysis_log.log_prediction(prediction)
           Aleesha's writer: validates, adds analysis_id, time and code version, appends.
           Its return value is the response body.

Problems that are not the caller's fault but the data's (a connectome missing for one
participant, a checkpoint that does not match its logged hash, a run missing from the run
log) are 503 with a plain sentence, as memo 0013 asks for unavailable data.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from neurographx import analysis_log, datasource
from neurographx.api import errors
from neurographx.api.analysis_checks import check_request
from neurographx.m3_model.run_logger import get_run


@lru_cache(maxsize=4)
def _connectomes(connectome_dir: str, atlas_key: str, stamp: int):
    """Load one atlas's connectomes once per file version (`stamp` = file time).

    Loading CC200 for all participants takes a moment; a demo asks many questions of the
    same atlas, so the loaded set is kept. A rebuilt file has a new time, so a new entry.
    """
    from neurographx.m3_model.data import load_connectomes

    return load_connectomes(connectome_dir, atlas_key)


def _connectome_stamp(connectome_dir: Path, atlas_key: str) -> int:
    from neurographx.m2_connectome.engine import atlas_paths
    from neurographx.m3_model.data import PIPELINE, STRATEGY

    npz, _ = atlas_paths(Path(connectome_dir), PIPELINE, STRATEGY, atlas_key)
    return npz.stat().st_mtime_ns if npz.exists() else 0


def graph_source(run: dict, root: Path | None = None):
    """`get_graph` for the graph settings a training run used (its `data_config`).

    Shared by POST /analyses and regenerate (api/reproduce.py), so both build a
    participant's graph in exactly the same way.
    """
    from neurographx.m3_model.data import make_get_graph

    cfg = run["data_config"]
    cdir = datasource.connectome_dir(root)
    cset = _connectomes(str(cdir), cfg["atlas_key"], _connectome_stamp(cdir, cfg["atlas_key"]))
    return make_get_graph(cset, cfg["density"], cfg["fill_nan"])


def run_analysis(participant_id: str, atlas: str, root: Path | None = None) -> dict:
    """Check, predict, log. Returns the analysis record (memo 0013, part 2)."""
    ok = check_request(participant_id, atlas, root)                    # 1
    pid, entry = ok["participant"]["participant_id"], ok["model"]

    run = get_run(entry["run_id"], datasource.run_log(root))
    if run is None:
        raise errors.unavailable(
            f"The model registered for atlas '{atlas}' (run {entry['run_id']}) is not in "
            "the run log, so its graph settings are unknown.")
    get_graph = graph_source(run, root)

    from neurographx.m3_model.inference import predict

    try:                                                                # 2
        prediction = predict(pid, atlas, get_graph, datasource.model_registry(root),
                             device="cpu")
    except KeyError:
        raise errors.unavailable(
            f"Participant {pid} has no connectome for atlas '{atlas}' in this dataset."
        ) from None
    except ValueError as err:  # checkpoint does not match the SHA-256 in the run log
        raise errors.unavailable(f"The model for atlas '{atlas}' cannot be used: {err}") from None

    try:                                                                # 3
        return analysis_log.log_prediction(prediction, datasource.analysis_log(root),
                                           datasource.run_log(root))
    except analysis_log.AnalysisLogError as err:
        raise errors.unavailable(f"The analysis could not be recorded: {err}") from None
