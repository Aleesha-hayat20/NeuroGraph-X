"""Training helpers shared by every training script (toy, synthetic, ABIDE)."""
import random

import numpy as np
import torch
import torch.nn.functional as F


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def class_weights(labels) -> torch.Tensor:
    """Memo 0011: weight for class c = n / (2 x n_c), from the training labels only.

    Mistakes on the smaller class then cost more, so a model cannot do well by mostly
    predicting the larger class. With equal classes both weights are 1.
    """
    y = torch.as_tensor([int(v) for v in labels], dtype=torch.long)
    counts = torch.bincount(y, minlength=2).double()
    if (counts == 0).any():
        raise ValueError(f"both classes are needed to weight them, got counts {counts.tolist()}")
    return (len(y) / (2.0 * counts)).float()


def train_epoch(model, loader, optimizer, device, class_weight=None):
    """One pass over the training loader. Returns the mean loss per graph.

    `class_weight` (two numbers, control then autism) weights the loss per class;
    None is the plain, unweighted loss of the baseline (memo 0006).
    """
    model.train()
    total = 0.0
    weight = None if class_weight is None else class_weight.to(device)
    for data in loader:
        data = data.to(device)
        optimizer.zero_grad()
        loss = F.cross_entropy(model(data.x, data.edge_index, data.batch), data.y,
                               weight=weight)
        loss.backward()
        optimizer.step()
        total += loss.item() * data.num_graphs
    return total / len(loader.dataset)


@torch.no_grad()
def evaluate(model, loader, device):
    """Returns (accuracy, logits) with logits in loader order."""
    model.eval()
    correct, all_logits = 0, []
    for data in loader:
        data = data.to(device)
        logits = model(data.x, data.edge_index, data.batch)
        correct += (logits.argmax(dim=1) == data.y).sum().item()
        all_logits.append(logits.cpu())
    return correct / len(loader.dataset), torch.cat(all_logits)
