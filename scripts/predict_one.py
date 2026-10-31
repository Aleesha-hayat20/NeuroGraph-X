"""One prediction on this machine's CPU, through the registered model (L7, memo 0009).

Checks that the inference path runs without a GPU and gives the same answer as the
training environment. It reads the model registry, the run log (for the graph
settings the model was trained with) and the stored connectomes, so on the real data
it needs the registered checkpoint in checkpoints/ and the connectomes in
data/processed/connectomes/ (scripts 01, 04, 07).

It only predicts: it reads no labels, trains nothing and writes nothing, so it is
safe to run on a frozen-set participant. It is not a frozen-set measurement.

Usage (from the repository root):
    python scripts/predict_one.py --participant 0050011 --atlas cc200 --expect control:0.7052
    NGX_DATA=fixtures python scripts/predict_one.py --participant 0090001   # no real data needed

--expect compares the result with a reference (prediction:confidence). The reference
for CC200 is the Kaggle GPU output of run 00252f2b on 12 October 2026
(docs/progress/week-02/week-02-inference.jpeg): participant 0050011, control, 0.7052.
"""
import argparse
import json
import platform
import sys

import torch

from neurographx import datasource
from neurographx.m3_model.data import load_connectomes, make_get_graph
from neurographx.m3_model.inference import checkpoint_path, predict
from neurographx.m3_model.run_logger import get_model, get_run

TOLERANCE = 1e-3  # CPU and GPU kernels differ in the last decimals, not more


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--participant", required=True, help="SUB_ID ('0050011'), or FILE_ID")
    p.add_argument("--atlas", default="cc200", help="short atlas name, as in the registry")
    p.add_argument("--expect", help="reference result as prediction:confidence")
    args = p.parse_args()

    registry = datasource.model_registry()
    entry = get_model(args.atlas, registry)
    run = get_run(entry["run_id"], datasource.run_log())
    if run is None:
        raise SystemExit(f"run {entry['run_id']} is registered but not in the run log")
    cfg = run["data_config"]
    print(f"data mode      : {datasource.mode()}")
    print(f"python / torch : {platform.python_version()} / {torch.__version__} (device cpu)")
    print(f"model          : run {entry['run_id']}, {checkpoint_path(entry, registry)}")

    cset = load_connectomes(datasource.connectome_dir(), cfg["atlas_key"])
    get_graph = make_get_graph(cset, cfg["density"], cfg["fill_nan"])
    result = predict(args.participant, args.atlas, get_graph, registry, device="cpu")
    print(json.dumps(result))

    if args.expect:
        want_pred, want_conf = args.expect.split(":")
        same = (result["prediction"] == want_pred
                and abs(result["confidence"] - float(want_conf)) <= TOLERANCE)
        print(f"matches reference {args.expect} (tolerance {TOLERANCE}): {same}")
        return 0 if same else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
