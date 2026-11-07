"""The API's error contract (decision memo 0013, part 4), in one place.

Every error the API returns has the body {"detail": "<one plain-language sentence>"}:

    404  unknown participant or analysis
    409  participant excluded by quality control (the gate and reasons are in the detail)
    422  invalid atlas name, filter value or request body
    503  no model registered for the atlas, its checkpoint missing, or data not available
    500  anything unexpected (the traceback goes to the server log, not to the user)

Endpoints never build an HTTPException by hand; they call one of the helpers below, so
the wording and the status codes stay consistent across the whole API.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

log = logging.getLogger("neurographx.api")


class DataUnavailable(Exception):
    """A data file the API needs is missing or inconsistent. Always answered with 503.

    Raised by the data layer (participants.py, cohort.py), which does not know about HTTP.
    """


# ---------------------------------------------------------------------------
# One helper per status code
# ---------------------------------------------------------------------------

def not_found(what: str, value: object) -> HTTPException:
    """404: "Unknown participant: 0059999", "Unknown analysis: 3f9c2a7b10de"."""
    return HTTPException(status_code=404, detail=f"Unknown {what}: {value}")


def excluded(participant_id: str, gate: str | None, reasons: Sequence[str]) -> HTTPException:
    """409: the participant failed quality control, so no analysis may run on them."""
    gate_text = f" ({gate})" if gate else ""
    reason_text = "; ".join(reasons) if reasons else "no reason recorded"
    return HTTPException(
        status_code=409,
        detail=f"Participant {participant_id} was excluded by quality control{gate_text}: "
               f"{reason_text}",
    )


def invalid(detail: str) -> HTTPException:
    """422: the request names something that does not exist or is not allowed."""
    return HTTPException(status_code=422, detail=detail)


def unknown_value(field: str, value: str, allowed: Iterable[str]) -> HTTPException:
    """422 for a filter or field value outside its allowed set."""
    allowed = list(allowed)
    return invalid(f"Unknown {field} '{value}'. Use one of: {', '.join(allowed)}")


def unavailable(detail: str) -> HTTPException:
    """503: the request is valid but the data, model or checkpoint it needs is missing."""
    return HTTPException(status_code=503, detail=detail)


# ---------------------------------------------------------------------------
# FastAPI's own validation errors, as one plain sentence
# ---------------------------------------------------------------------------

def _field_name(loc: Sequence) -> str:
    """('query', 'qc_status') -> 'qc_status'; ('body', 'atlas') -> 'atlas'."""
    parts = [str(p) for p in loc if p not in ("query", "path", "body", "header", "cookie")]
    return ".".join(parts) or "request"


def validation_message(errors: Sequence[dict]) -> str:
    """Turn FastAPI's list of validation errors into one readable sentence per error.

        [{'loc': ('query', 'qc_status'), 'msg': "Input should be 'included' or 'excluded'",
          'input': 'maybe', 'type': 'literal_error'}]
        -> "Invalid value 'maybe' for qc_status: input should be 'included' or 'excluded'."
    """
    sentences = []
    for err in errors:
        field = _field_name(err.get("loc", ()))
        msg = str(err.get("msg", "invalid value"))
        msg = msg[:1].lower() + msg[1:]
        if err.get("type") == "missing":
            sentences.append(f"Missing required field: {field}.")
        elif "input" in err and not isinstance(err["input"], (dict, list)):
            sentences.append(f"Invalid value '{err['input']}' for {field}: {msg}.")
        else:
            sentences.append(f"Invalid {field}: {msg}.")
    return " ".join(sentences) or "Invalid request."


async def _validation_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": validation_message(exc.errors())})


async def _data_handler(_request: Request, exc: DataUnavailable) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(exc)})


async def _unexpected_handler(request: Request, exc: Exception) -> JSONResponse:
    log.exception("Unexpected error on %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse(status_code=500,
                        content={"detail": "Internal error; see the server log."})


def install(app: FastAPI) -> None:
    """Register the handlers that keep every error body a plain-language `detail`."""
    app.add_exception_handler(RequestValidationError, _validation_handler)
    app.add_exception_handler(DataUnavailable, _data_handler)
    app.add_exception_handler(Exception, _unexpected_handler)
