"""Run this first. Prints everything SETUP.md needs as evidence (L1)."""
import platform
import sys

import torch

print("Python          :", sys.version.split()[0])
print("Platform        :", platform.platform())
print("PyTorch         :", torch.__version__)
print("CUDA available  :", torch.cuda.is_available())
if torch.cuda.is_available():
    print("GPU             :", torch.cuda.get_device_name(0))
    print("CUDA version    :", torch.version.cuda)

try:
    import torch_geometric
    from torch_geometric.nn import GCNConv, global_mean_pool  # noqa: F401
    print("PyG             :", torch_geometric.__version__)
    print("PyG import      : OK")
except Exception as e:  # noqa: BLE001
    print("PyG import      : FAILED ->", e)

try:
    import numpy
    import pandas
    import sklearn
    print("scikit-learn    :", sklearn.__version__)
    print("numpy / pandas  :", numpy.__version__, "/", pandas.__version__)
except Exception as e:  # noqa: BLE001
    print("Other libs      : FAILED ->", e)
