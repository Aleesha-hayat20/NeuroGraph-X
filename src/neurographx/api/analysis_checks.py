"""Can this analysis run? The fixed order of checks for POST /analyses (memo 0013, part 4).

The same request must always get the same error, so the checks always run in this order:

    1. the atlas name is one of the four          422  "Unknown atlas 'cc400'. Use one of: ..."
    2. the participant exists                      404  "Unknown participant: 0059999"
    3. the participant passed quality control      409  "Participant 0050002 was excluded ..."
    4. connectomes exist for the atlas             503  "Connectome data for atlas 'aal' ..."
    5. a model is registered, and its checkpoint   503  "No model is registered for atlas 'ho'"
       file is present

`check_request` returns everything the model side needs to run the prediction, so the
POST /analyses endpoint (backlog W5-09) calls it first and then only does inference and
writes the record through neurographx.analysis_log.
"""

from __future__ import annotations

from pathlib import Path

from neurographx import datasource
from neurographx.api import cohort, errors
from neurographx.api.participants import find_participant, load_participants
from neurographx.m3_model.run_logger import read_registry


def check_request(participant_id: str, atlas: str, root: Path | None = None) -> dict:
    """Run checks 1 to 5. Raises the matching HTTPException; returns, when all pass:

        {"participant": <participant record>, "atlas": <atlas record>,
         "model": <registry entry>, "checkpoint": <absolute Path of the checkpoint>}
    """
    atlases = {a["atlas"]: a for a in cohort.atlas_records(root)}
    if atlas not in atlases:                                              # 1
        raise errors.unknown_value("atlas", atlas, atlases)

    record = find_participant(load_participants(root), participant_id)   # 2
    if record is None:
        raise errors.not_found("participant", participant_id)

    if record["qc_status"] != "included":                                 # 3
        raise errors.excluded(record["participant_id"], record["exclusion_gate"],
                              record["exclusion_reasons"])

    info = atlases[atlas]
    if not info["data_available"]:                                        # 4
        raise errors.unavailable(
            f"Connectome data for atlas '{atlas}' is not available in this dataset.")

    entry = read_registry(datasource.model_registry(root)).get(atlas)     # 5
    if entry is None:
        raise errors.unavailable(f"No model is registered for atlas '{atlas}'.")
    checkpoint = datasource.checkpoint(entry["checkpoint_path"], root)
    if not checkpoint.exists():
        raise errors.unavailable(
            f"The checkpoint of the model registered for atlas '{atlas}' "
            f"(run {entry['run_id']}) is missing: {checkpoint.name}.")

    return {"participant": record, "atlas": info, "model": entry, "checkpoint": checkpoint}
