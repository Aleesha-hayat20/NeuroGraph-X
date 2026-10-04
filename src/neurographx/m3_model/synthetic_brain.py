"""Brain-shaped synthetic graphs for NeuroGraph-X pipeline testing.
NOT real data. Used to test shapes, thresholding and the training loop
before ABIDE matrices arrive. matrix_to_graph() is reused on real data."""
import numpy as np
import torch
from torch_geometric.data import Data


def assign_networks(n_rois, n_networks, seed=0):
    """Fixed ROI-to-network assignment, every network non-empty."""
    rng = np.random.default_rng(seed)
    return rng.permutation(np.arange(n_rois) % n_networks)


def simulate_timeseries(rng, network_of_roi, n_timepoints, label, effect,
                        base_coupling=0.8, noise_sd=1.0):
    """Label 1 has weaker coupling between networks 0 and 1 (planted signal)."""
    n_networks = int(network_of_roi.max()) + 1
    latent = rng.standard_normal((n_timepoints, n_networks))
    coupling = base_coupling * (1.0 - effect * label) + rng.normal(0.0, 0.1)
    shared = rng.standard_normal(n_timepoints)
    latent[:, 0] += coupling * shared
    latent[:, 1] += coupling * shared
    noise = noise_sd * rng.standard_normal((n_timepoints, len(network_of_roi)))
    return latent[:, network_of_roi] + noise


def correlation_to_fisher_z(ts):
    """Pearson correlation between ROI columns, Fisher z, diagonal set to 0."""
    r = np.corrcoef(ts, rowvar=False)
    r = np.clip(r, -0.999999, 0.999999)
    z = np.arctanh(r)
    np.fill_diagonal(z, 0.0)
    return z.astype(np.float32)


def matrix_to_graph(z, label, density=0.10, subject_id=None, site=None,
                    atlas="synthetic"):
    """Unthresholded N x N Fisher-z matrix -> PyG graph.
    Node features: correlation rows. Edges: top `density` fraction of |z|
    (proportional threshold), undirected, weight = |z|."""
    z = np.asarray(z, dtype=np.float32)
    n = z.shape[0]
    if z.ndim != 2 or z.shape != (n, n):
        raise ValueError(f"expected square matrix, got {z.shape}")
    if not np.isfinite(z).all():
        raise ValueError(f"{subject_id}: matrix contains NaN or inf")
    if not np.allclose(z, z.T, atol=1e-5):
        raise ValueError(f"{subject_id}: matrix is not symmetric")
    iu, ju = np.triu_indices(n, k=1)
    strength = np.abs(z[iu, ju])
    k = max(1, round(density * strength.size))
    keep = np.argpartition(strength, -k)[-k:]
    src = np.concatenate([iu[keep], ju[keep]])
    dst = np.concatenate([ju[keep], iu[keep]])
    return Data(
        x=torch.from_numpy(z.copy()),
        edge_index=torch.tensor(np.stack([src, dst]), dtype=torch.long),
        edge_weight=torch.tensor(np.concatenate([strength[keep], strength[keep]]),
                                 dtype=torch.float32),
        y=torch.tensor([int(label)], dtype=torch.long),
        num_nodes=n, subject_id=subject_id, site=site, atlas=atlas,
    )


def make_dataset(n_subjects=200, n_rois=200, n_timepoints=150, n_networks=7,
                 effect=0.5, density=0.10, n_sites=4, seed=0):
    """Balanced synthetic cohort. effect=0 means no signal (null control)."""
    rng = np.random.default_rng(seed)
    network_of_roi = assign_networks(n_rois, n_networks, seed)
    labels = np.array([i % 2 for i in range(n_subjects)])
    rng.shuffle(labels)
    sites = rng.integers(0, n_sites, size=n_subjects)
    graphs = []
    for i in range(n_subjects):
        site_noise = 1.0 + 0.3 * sites[i] / max(1, n_sites - 1)
        ts = simulate_timeseries(rng, network_of_roi, n_timepoints,
                                 int(labels[i]), effect, noise_sd=site_noise)
        graphs.append(matrix_to_graph(
            correlation_to_fisher_z(ts), int(labels[i]), density,
            subject_id=f"SYN_{i:04d}", site=f"SITE{sites[i]}",
            atlas=f"synthetic{n_rois}"))
    return graphs
