"""Regenerate and export one past analysis (memo 0013, part 3; work plan Section 5.1).

Regenerate answers one question: run the same participant through the same model again,
do we get the same answer? So it uses the model of the original analysis's training run
(`run_id`), not whichever model is registered for the atlas today, with that run's graph
settings and that run's calibration, through the same inference code as POST /analyses.
The new analysis is written through the analysis-log writer with
`reproduces_analysis_id` set to the original's `analysis_id`.

`identical` is true when `prediction`, `confidence` (both stored to 4 decimals) and
`calibrated` all match; `differences` names the fields that do not.

Export returns one stored record, unchanged, as a JSON or CSV file.

Order of checks for regenerate (each answered with the documented status):

    1. the analysis exists                                      404
    2. its training run is in the run log                       503
    3. that run saved a checkpoint                              503
    4. the checkpoint file is present on this machine           503
    5. the checkpoint matches the SHA-256 its run recorded      503
    6. the participant has a connectome for the atlas           503
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from neurographx import analysis_log, datasource
from neurographx.api import errors
from neurographx.api.analyses import graph_source
from neurographx.m3_model.run_logger import get_run

# The fields that decide whether a regenerated analysis repeats the original.
COMPARED = ("prediction", "confidence", "calibrated")
EXPORT_FORMATS = ("json", "csv")


def compare(original: dict, repeat: dict) -> list[str]:
    """Names of the compared fields that differ, in a fixed order (empty when identical)."""
    return [f for f in COMPARED if original[f] != repeat[f]]


def _original(analysis_id: str, root: Path | None) -> dict:
    record = analysis_log.get_analysis(analysis_id, datasource.analysis_log(root))
    if record is None:                                                  # 1
        raise errors.not_found("analysis", analysis_id)
    return record


def _model_of(record: dict, root: Path | None) -> tuple[dict, dict]:
    """The training run of `record` and the {atlas, run_id, checkpoint_path} to load it."""
    run_id, aid = record["run_id"], record["analysis_id"]
    run = get_run(run_id, datasource.run_log(root))
    if run is None:                                                     # 2
        raise errors.unavailable(
            f"Analysis {aid} was made by run {run_id}, which is not in the run log, "
            "so it cannot be regenerated.")
    relative = run.get("checkpoint_path")
    if not relative or "data_config" not in run:                        # 3
        raise errors.unavailable(
            f"Run {run_id} saved no checkpoint, so analysis {aid} cannot be regenerated.")
    if not datasource.checkpoint(relative, root).exists():              # 4
        raise errors.unavailable(
            f"The checkpoint of run {run_id} ({relative}) is not available on this machine, "
            f"so analysis {aid} cannot be regenerated.")
    entry = {"atlas": record["atlas"], "run_id": run_id, "checkpoint_path": relative}
    return run, entry


def regenerate(analysis_id: str, root: Path | None = None) -> dict:
    """Re-run a past analysis with its original model and record the repeat.

    Returns {"analysis": new record, "original": stored record,
             "identical": bool, "differences": [field, ...]}.
    """
    original = _original(analysis_id, root)
    run, entry = _model_of(original, root)

    from neurographx.m3_model.inference import predict

    pid, atlas = original["participant_id"], original["atlas"]
    try:
        prediction = predict(pid, atlas, graph_source(run, root),
                             datasource.model_registry(root), device="cpu", entry=entry)
    except KeyError:                                                    # 6
        raise errors.unavailable(
            f"Participant {pid} has no connectome for atlas '{atlas}' in this dataset."
        ) from None
    except ValueError as err:                                           # 5
        raise errors.unavailable(
            f"The model of run {entry['run_id']} cannot be used: {err}") from None

    try:
        repeat = analysis_log.log_prediction(
            prediction, datasource.analysis_log(root), datasource.run_log(root),
            reproduces_analysis_id=original["analysis_id"])
    except analysis_log.AnalysisLogError as err:
        raise errors.unavailable(f"The analysis could not be recorded: {err}") from None

    differences = compare(original, repeat)
    return {"analysis": repeat, "original": original, "identical": not differences,
            "differences": differences}


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def _csv_value(value) -> str:
    """CSV cell for one field: true/false as in JSON, an empty cell for null."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def export_text(record: dict, fmt: str) -> tuple[str, str, str]:
    """(file content, media type, file name) for one analysis record.

    JSON is the record exactly as stored. CSV is a header row of the ten fields in the
    order of db/schema.sql, then one row.
    """
    if fmt not in EXPORT_FORMATS:
        raise errors.unknown_value("format", fmt, EXPORT_FORMATS)
    name = f"analysis_{record['analysis_id']}.{fmt}"
    ordered = {f: record[f] for f in analysis_log.FIELDS}
    if fmt == "json":
        return json.dumps(ordered, indent=2) + "\n", "application/json", name
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(analysis_log.FIELDS)
    writer.writerow([_csv_value(ordered[f]) for f in analysis_log.FIELDS])
    return buffer.getvalue(), "text/csv", name


def export(analysis_id: str, fmt: str, root: Path | None = None) -> tuple[str, str, str]:
    """Export a stored analysis; 404 when it does not exist, 422 for an unknown format."""
    if fmt not in EXPORT_FORMATS:
        raise errors.unknown_value("format", fmt, EXPORT_FORMATS)
    return export_text(_original(analysis_id, root), fmt)
