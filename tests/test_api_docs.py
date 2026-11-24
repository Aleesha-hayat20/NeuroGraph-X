"""docs/api.md lists exactly the endpoints the API serves (#183).

The endpoint table is the reference people read; FastAPI's OpenAPI schema is what the code
serves. If an endpoint is added, removed or renamed without updating the page, this fails.
"""
import re

from neurographx.api.main import app
from neurographx.utils.paths import project_root

DOC = project_root() / "docs/api.md"
ROW = re.compile(r"^\| `(GET|POST|PUT|PATCH|DELETE) (/[^`]*)` \|", re.M)


def _served() -> set[tuple[str, str]]:
    paths = app.openapi()["paths"]
    return {(method.upper(), path) for path, ops in paths.items() for method in ops}


def _documented() -> set[tuple[str, str]]:
    section = DOC.read_text(encoding="utf-8").split("## Endpoints", 1)[1]
    table = section.split("\n### ", 1)[0]
    return set(ROW.findall(table))


def test_every_served_endpoint_is_documented():
    missing = _served() - _documented()
    assert not missing, f"served but not in docs/api.md: {sorted(missing)}"


def test_every_documented_endpoint_is_served():
    extra = _documented() - _served()
    assert not extra, f"in docs/api.md but not served: {sorted(extra)}"


def test_every_endpoint_has_a_summary():
    for path, ops in app.openapi()["paths"].items():
        for method, op in ops.items():
            assert op.get("summary"), f"{method.upper()} {path} has no OpenAPI summary"
