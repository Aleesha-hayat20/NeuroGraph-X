"""Run logging and model registry for NeuroGraph-X (L5).

Every training run appends ONE JSON line to runs/run_log.jsonl holding its
configuration and its result. The model registry (runs/model_registry.json)
records which run is the current model for each atlas (decision 0004: one
model per atlas).

Both files are plain text on purpose: they can be read without any tool, they
diff cleanly in git, and they map directly onto the run-log and model-registry
tables of the database schema.
"""
import json
import platform
import subprocess
import uuid
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

SCHEMA_VERSION = 2
LOG_PATH = Path("runs/run_log.jsonl")
REGISTRY_PATH = Path("runs/model_registry.json")

# Every record must carry these keys. `atlas` may be None for non-brain data.
REQUIRED_FIELDS = (
    "run_id",
    "dataset",
    "atlas",
    "seed",
    "hyperparameters",
    "metrics",
    "checkpoint_path",
)


def new_run_id() -> str:
    return uuid.uuid4().hex[:8]


def git_commit() -> str | None:
    """Short hash of the code that produced the run, or None outside git."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True, timeout=5,
        )
        return out.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def environment() -> dict:
    """Library versions, so a result can be tied to the setup that made it."""
    env = {"python": platform.python_version()}
    for name in ("torch", "torch_geometric"):
        try:
            env[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            env[name] = None
    return env


def read_runs(path: Path = LOG_PATH) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def get_run(run_id: str, path: Path = LOG_PATH) -> dict | None:
    for record in read_runs(path):
        if record.get("run_id") == run_id:
            return record
    return None


def log_run(record: dict, path: Path = LOG_PATH) -> str:
    """Validate and append one run record. Returns the run_id.

    Raises ValueError if a required field is missing or the run_id is already
    in the log, so a bad record fails loudly instead of being half-written.
    """
    path = Path(path)
    missing = [k for k in REQUIRED_FIELDS if k not in record]
    if missing:
        raise ValueError(f"run record is missing required fields: {missing}")
    if get_run(record["run_id"], path) is not None:
        raise ValueError(f"run_id {record['run_id']} is already in {path}")

    full = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "schema_version": SCHEMA_VERSION,
        "git_commit": git_commit(),
        "environment": environment(),
        **record,
    }
    line = json.dumps(full)  # serialise first: a failure writes nothing
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(line + "\n")
    return full["run_id"]


def read_registry(path: Path = REGISTRY_PATH) -> dict:
    path = Path(path)
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def register_model(run_id: str, log_path: Path = LOG_PATH,
                   registry_path: Path = REGISTRY_PATH) -> dict:
    """Make `run_id` the current model for its atlas.

    The entry is copied from the run log, so the registry can never point at
    a run that was not logged. The model it replaces is kept under
    `previous_run_ids`.
    """
    run = get_run(run_id, log_path)
    if run is None:
        raise ValueError(f"run_id {run_id} is not in {log_path}")
    if not run.get("atlas"):
        raise ValueError(f"run {run_id} has no atlas, so it cannot be registered")

    registry = read_registry(registry_path)
    atlas = run["atlas"]
    old = registry.get(atlas)
    previous = []
    if old and old["run_id"] != run_id:
        previous = [*old.get("previous_run_ids", []), old["run_id"]]
    elif old:
        previous = old.get("previous_run_ids", [])

    entry = {
        "atlas": atlas,
        "run_id": run_id,
        "checkpoint_path": run["checkpoint_path"],
        "metrics": run["metrics"],
        "registered_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "previous_run_ids": previous,
    }
    registry[atlas] = entry
    registry_path = Path(registry_path)
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    with open(registry_path, "w") as f:
        json.dump(registry, f, indent=2, sort_keys=True)
        f.write("\n")
    return entry


def get_model(atlas: str, path: Path = REGISTRY_PATH) -> dict:
    """Registry entry for an atlas. Raises KeyError if none is registered."""
    registry = read_registry(path)
    if atlas not in registry:
        raise KeyError(f"no model registered for atlas '{atlas}'")
    return registry[atlas]
