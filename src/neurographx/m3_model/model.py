"""Baseline graph neural network (decision 0006).

N x GCNConv -> global mean pooling -> MLP head. One model per atlas
(decision 0004): `in_dim` is the number of regions of that atlas.
"""
import torch
import torch.nn.functional as F
from torch.nn import Dropout, Linear, ModuleList, ReLU, Sequential
from torch_geometric.nn import GCNConv, global_mean_pool


class GCN(torch.nn.Module):
    """N x GCNConv -> mean-pool readout -> MLP head."""

    def __init__(self, in_dim, hidden, num_classes, num_layers=3, dropout=0.5):
        super().__init__()
        dims = [in_dim] + [hidden] * num_layers
        self.convs = ModuleList(
            [GCNConv(dims[i], dims[i + 1]) for i in range(num_layers)]
        )
        self.head = Sequential(
            Linear(hidden, hidden), ReLU(), Dropout(dropout), Linear(hidden, num_classes)
        )
        self.dropout = dropout

    def forward(self, x, edge_index, batch):
        for conv in self.convs:
            x = F.relu(conv(x, edge_index))
            x = F.dropout(x, p=self.dropout, training=self.training)
        x = global_mean_pool(x, batch)  # graph-level readout
        return self.head(x)  # logits


def model_from_checkpoint(ckpt: dict) -> GCN:
    """Rebuild the exact architecture stored in a checkpoint and load its weights."""
    model = GCN(ckpt["in_dim"], ckpt["hidden"], ckpt["num_classes"],
                ckpt["layers"], ckpt["dropout"])
    model.load_state_dict(ckpt["state_dict"])
    return model
