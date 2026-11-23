"""Measure analysis time on this machine's CPU (#139, NFR-9) and write the report table.

The server is started as uvicorn starts it, so its start-up hook loads the model code
once (the start-up time is reported). Then, for each atlas with a registered model, through
the real API code (FastAPI TestClient, no network):

  1. the first POST /analyses, which also loads the atlas's connectomes ("cold");
  2. then `--repeats` more requests for the same participant ("warm"): their median and
     maximum time, and whether every repeat gave the same prediction and confidence;
  3. NFR-9: every warm analysis within 5 seconds.

The records go to a temporary analysis log, never to runs/analysis_log.jsonl, so the
demonstration log is untouched. Writes docs/reports/performance.md (real data) and prints
the same table.

Usage (from the repository root):
    python scripts/benchmark_api.py                      # real data
    python scripts/benchmark_api.py --data fixtures      # quick check on the fixtures
"""
import argparse
import os
import platform
import statistics
import tempfile
import time
from datetime import date
from pathlib import Path

LIMIT_S = 5.0  # NFR-9
PARTICIPANT = {"real": "0050011", "fixtures": "0090001"}


def _machine() -> str:
    import torch

    cpu = platform.processor() or platform.machine()
    return (f"{platform.system()} {platform.release()}, {cpu}, {os.cpu_count()} logical "
            f"cores; Python {platform.python_version()}, PyTorch {torch.__version__} (CPU)")


def _measure(client, atlas: str, participant: str, repeats: int, startup_s: float) -> dict:
    """One first request and `repeats` more for one atlas: times and whether all agree."""
    body = {"participant_id": participant, "atlas": atlas}
    times, answers = [], set()
    for _ in range(repeats + 1):
        start = time.perf_counter()
        response = client.post("/analyses", json=body)
        elapsed = time.perf_counter() - start
        if response.status_code != 201:
            raise SystemExit(f"{atlas}: {response.status_code} "
                             f"{response.json().get('detail')}")
        record = response.json()
        answers.add((record["prediction"], record["confidence"]))
        times.append(elapsed)
    warm = times[1:]
    return {"atlas": atlas, "run_id": record["run_id"], "cold_s": times[0],
            "warm_median_s": statistics.median(warm), "warm_max_s": max(warm),
            "repeats": repeats, "identical": len(answers) == 1,
            "prediction": record["prediction"], "confidence": record["confidence"],
            "within_limit": max(warm) <= LIMIT_S, "startup_s": startup_s}


def benchmark(repeats: int = 20, participant: str | None = None) -> list[dict]:
    from fastapi.testclient import TestClient

    from neurographx import datasource
    from neurographx.api.main import app
    from neurographx.m3_model.run_logger import read_registry

    mode = "fixtures" if os.environ.get("NGX_DATA") == "fixtures" else "real"
    participant = participant or PARTICIPANT[mode]
    registry = read_registry(datasource.model_registry())
    with tempfile.TemporaryDirectory() as tmp:
        log = Path(tmp) / "analysis_log.jsonl"
        real_log = datasource.analysis_log
        datasource.analysis_log = lambda root=None: log  # keep the demonstration log clean
        try:
            start = time.perf_counter()
            with TestClient(app) as client:  # runs the start-up hook, as uvicorn does
                startup_s = time.perf_counter() - start
                rows = [_measure(client, atlas, participant, repeats, startup_s)
                        for atlas in registry]
        finally:
            datasource.analysis_log = real_log
    return rows


def table(rows: list[dict], participant: str) -> str:
    lines = [
        "| Atlas | Run | First request, incl. loading (s) | Repeat median (ms) | "
        "Repeat max (ms) | Repeats identical | Within 5 s (NFR-9) |",
        "|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['atlas']} | `{r['run_id']}` | {r['cold_s']:.2f} | "
                     f"{r['warm_median_s'] * 1000:.0f} | {r['warm_max_s'] * 1000:.0f} | "
                     f"{'yes' if r['identical'] else 'NO'} ({r['repeats']}) | "
                     f"{'yes' if r['within_limit'] else 'NO'} |")
    startup = (f"Server start-up, which loads the model code once: {rows[0]['startup_s']:.2f} s. "
               if rows and "startup_s" in rows[0] else "")
    return "\n".join(lines) + f"\n\n{startup}Participant {participant}; prediction and " \
        "confidence of every repeat compared with the first.\n"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data", choices=["real", "fixtures"], default="real")
    p.add_argument("--repeats", type=int, default=20)
    p.add_argument("--participant", default=None)
    args = p.parse_args()
    if args.data == "fixtures":
        os.environ["NGX_DATA"] = "fixtures"
    participant = args.participant or PARTICIPANT[args.data]
    rows = benchmark(args.repeats, participant)
    text = table(rows, participant)
    print(_machine())
    print(text)
    if args.data == "real":
        out = Path("docs/reports/performance.md")
        out.write_text(
            "# Performance on the CPU (NFR-9)\n\n"
            "Generated by `scripts/benchmark_api.py` on "
            f"{date.today().isoformat()}. Re-run it on the demonstration laptop before the "
            "final evaluation.\n\n"
            f"**Machine:** {_machine()}.\n\n" + text, encoding="utf-8", newline="\n")
        print(f"Wrote {out}")
    if not all(r["within_limit"] and r["identical"] for r in rows):
        raise SystemExit("NFR-9 or repeatability not met: see the table")


if __name__ == "__main__":
    main()
