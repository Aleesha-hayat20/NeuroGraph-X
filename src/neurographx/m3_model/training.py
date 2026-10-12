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


def train_epoch(model, loader, optimizer, device):
    """One pass over the training loader. Returns the mean loss per graph."""
    model.train()
    total = 0.0
    for data in loader:
        data = data.to(device)
        optimizer.zero_grad()
        loss = F.cross_entropy(model(data.x, data.edge_index, data.batch), data.y)
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
