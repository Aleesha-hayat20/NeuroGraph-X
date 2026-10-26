#!/usr/bin/env python3
"""Start the real API server on a dataset and check it answers (memo 0014).

Usage (from the repository root):
    python scripts/smoke_api.py                  # fixture dataset (the default; works anywhere)
    python scripts/smoke_api.py --data real      # real data (needs data/raw)

Unlike the pytest API tests, this starts uvicorn as a separate process with only the
environment variable NGX_DATA set, exactly as a teammate or CI would, then calls
/health and /participants over HTTP and checks the counts against the dataset's QC
outputs. Exit code 0 means the server ran and answered correctly.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

import pandas as pd

from neurographx import datasource


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", choices=datasource.MODES, default="fixtures")
    ap.add_argument("--timeout", type=float, default=30.0, help="seconds to wait for start-up")
    args = ap.parse_args()

    os.environ["NGX_DATA"] = args.data
    if not datasource.qc_cohort().exists():
        print(f"FAIL: {datasource.qc_cohort()} not found")
        return 1
    cohort = pd.read_csv(datasource.qc_cohort())
    excluded = pd.read_csv(datasource.exclusion_log())

    port = free_port()
    base = f"http://127.0.0.1:{port}"
    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "neurographx.api.main:app", "--port", str(port),
         "--log-level", "warning"],
        env={**os.environ, "NGX_DATA": args.data},
    )
    failures: list[str] = []
    try:
        deadline = time.time() + args.timeout
        health = None
        while time.time() < deadline:
            if server.poll() is not None:
                print(f"FAIL: the server exited with code {server.returncode}")
                return 1
            try:
                health = get(f"{base}/health")
                break
            except (urllib.error.URLError, ConnectionError):
                time.sleep(0.3)
        if health is None:
            print(f"FAIL: no answer from {base}/health within {args.timeout} s")
            return 1

        print(f"/health        {health}")
        if health.get("data_mode") != args.data:
            failures.append(f"data_mode is {health.get('data_mode')!r}, expected {args.data!r}")
        if not health.get("participant_table_found"):
            print(f"FAIL: participant table not found ({datasource.phenotypic_table()})")
            return 1

        body = get(f"{base}/participants")
        print(f"/participants  total {body['total']}, included {body['included']}, "
              f"excluded {body['excluded']}")
        expected = (len(cohort) + len(excluded), len(cohort), len(excluded))
        if (body["total"], body["included"], body["excluded"]) != expected:
            failures.append(f"counts {body['total'], body['included'], body['excluded']} "
                            f"differ from the QC outputs {expected}")

        first = f"{int(cohort.SUB_ID.iloc[0]):07d}"
        record = get(f"{base}/participants/{first}")
        print(f"/participants/{first}  {record['qc_status']}, site {record['site']}")
        if record["qc_status"] != "included":
            failures.append(f"participant {first} should be included")
    except urllib.error.HTTPError as err:
        print(f"FAIL: {err.url} answered {err.code}: {err.read().decode('utf-8', 'replace')}")
        return 1
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print(f"OK: the API runs on the {args.data} dataset")
    return 0


if __name__ == "__main__":
    sys.exit(main())
