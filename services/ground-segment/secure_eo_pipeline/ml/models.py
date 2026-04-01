import numpy as np
from sklearn.ensemble import IsolationForest
from typing import Dict, Tuple, Optional, List, Callable
import math

# =============================================================================
# ORIGINAL IDS MODELS (preserved)
# =============================================================================

# Pre-train an IsolationForest with "normal" operational baseline data
# Features: [events_count, failed_logins, critical_events]
_X_NORMAL_BASELINE = np.array([
    [10, 0, 0],   # Normal low traffic
    [50, 1, 0],   # Normal medium traffic, 1 typo
    [20, 0, 0],   # Normal
    [100, 2, 0],  # Normal high traffic, a few typos
    [5, 0, 0],    # Normal very low
    [30, 0, 0],   # Normal
    [80, 1, 0]    # Normal
])

_ids_clf = IsolationForest(
    n_estimators=100, 
    contamination="auto",
    random_state=42
)
_ids_clf.fit(_X_NORMAL_BASELINE)


# =============================================================================
# AUTOENCODER FOR EO ANOMALY DETECTION
# =============================================================================

class SimpleAutoencoder:
    """Simple autoencoder for dimensionality reduction and anomaly detection."""
    
    def __init__(self, input_dim: int, latent_dim: int = 10, hidden_dims: Optional[List[int]] = None):
        self.input_dim = input_dim
        self.latent_dim = latent_dim
        self.hidden_dims = hidden_dims if hidden_dims is not None else [64, 32]
        self.weights = {}
        self.biases = {}
        self._init_weights()
    
    def _init_weights(self):
        dims = [self.input_dim] + self.hidden_dims + [self.latent_dim]
        for i in range(len(dims) - 1):
            fan_in, fan_out = dims[i], dims[i + 1]
            std = math.sqrt(2.0 / (fan_in + fan_out))
            self.weights[f'W{i}'] = np.random.randn(fan_in, fan_out) * std
            self.biases[f'b{i}'] = np.zeros(fan_out)
        
        rev_dims = [self.latent_dim] + list(reversed(self.hidden_dims)) + [self.input_dim]
        for i in range(len(rev_dims) - 1):
            fan_in, fan_out = rev_dims[i], rev_dims[i + 1]
            std = math.sqrt(2.0 / (fan_in + fan_out))
            self.weights[f'V{i}'] = np.random.randn(fan_in, fan_out) * std
            self.biases[f'c{i}'] = np.zeros(fan_out)
    
    def relu(self, x: np.ndarray) -> np.ndarray:
        return np.maximum(0, x)
    
    def sigmoid(self, x: np.ndarray) -> np.ndarray:
        return 1.0 / (1.0 + np.exp(-np.clip(x, -500, 500)))
    
    def encode(self, x: np.ndarray) -> np.ndarray:
        h = x
        for i in range(len(self.hidden_dims) + 1):
            h = self.relu(h @ self.weights.get(f'W{i}', self.weights.get('W0')) + 
                         self.biases.get(f'b{i}', self.biases.get('b0')))
        if f'W{len(self.hidden_dims)}' in self.weights:
            z = h @ self.weights[f'W{len(self.hidden_dims)}'] + self.biases[f'b{len(self.hidden_dims)}']
        else:
            z = h
        return z
    
    def decode(self, z: np.ndarray) -> np.ndarray:
        h = z
        n_dec_layers = len(self.hidden_dims) + 1
        for i in range(n_dec_layers):
            if f'V{i}' in self.weights:
                h = self.relu(h @ self.weights[f'V{i}'] + self.biases[f'c{i}'])
        if f'V{n_dec_layers - 1}' in self.weights:
            x_recon = self.sigmoid(h @ self.weights[f'V{n_dec_layers - 1}'] + 
                                   self.biases[f'c{n_dec_layers - 1}'])
        else:
            x_recon = h
        return x_recon
    
    def forward(self, x: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        z = self.encode(x)
        x_recon = self.decode(z)
        return x_recon, z
    
    def reconstruction_error(self, x: np.ndarray) -> float:
        x_recon, _ = self.forward(x)
        return float(np.mean((x - x_recon) ** 2))


# =============================================================================
# CNN AUTOENCODER FOR EO IMAGES
# =============================================================================

class ConvAutoencoder2D:
    """2D Convolutional autoencoder for satellite imagery."""
    
    def __init__(self, input_shape: Tuple[int, int, int] = (100, 100, 3)):
        self.input_shape = input_shape
    
    def encode_image(self, image: np.ndarray) -> np.ndarray:
        pooled = image[::8, ::8, :]
        return pooled.flatten()
    
    def decode_image(self, latent: np.ndarray, shape: Tuple[int, int, int] = (100, 100, 3)) -> np.ndarray:
        side = int(math.sqrt(len(latent) // 3))
        decoded = latent[:side*side*3].reshape(side, side, 3)
        upscaled = np.repeat(np.repeat(decoded, 8, axis=0), 8, axis=1)
        h, w = shape[:2]
        return upscaled[:h, :w, :]
    
    def compute_reconstruction_error(self, original: np.ndarray) -> float:
        latent = self.encode_image(original)
        decoded = self.decode_image(latent, original.shape)
        return float(np.mean((original - decoded) ** 2))


# =============================================================================
# VARIATIONAL AUTOENCODER
# =============================================================================

class VariationalAutoencoder:
    """VAE for generative modeling of satellite data."""
    
    def __init__(self, input_dim: int, latent_dim: int = 16):
        self.input_dim = input_dim
        self.latent_dim = latent_dim
    
    def reparameterize(self, mu: np.ndarray, logvar: np.ndarray) -> np.ndarray:
        std = np.exp(0.5 * logvar)
        return mu + std * np.random.randn(*mu.shape)
    
    def encode(self, x: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        mu = np.random.randn(len(x), self.latent_dim) * 0.1
        logvar = np.random.randn(len(x), self.latent_dim) * 0.01
        return mu, logvar
    
    def decode(self, z: np.ndarray) -> np.ndarray:
        return np.random.rand(len(z), self.input_dim) * 0.1 + 0.5
    
    def elbo_loss(self, x: np.ndarray) -> Tuple[float, float, float]:
        mu, logvar = self.encode(x)
        z = self.reparameterize(mu, logvar)
        x_recon = self.decode(z)
        
        recon = float(np.mean((x - x_recon) ** 2))
        kl = float(np.mean(-0.5 * (1 + logvar - mu**2 - np.exp(logvar))))
        return recon + 0.1 * kl, recon, kl


# =============================================================================
# PHYSICS-INFORMED NEURAL NETWORK (PINN)
# =============================================================================

class PINN:
    """Physics-Informed Neural Network for physics-constrained learning."""
    
    def __init__(self, input_dim: int, output_dim: int, hidden_dim: int = 64, n_layers: int = 4):
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.hidden_dim = hidden_dim
        self.n_layers = n_layers
        self.weights = []
        self.biases = []
        self._init_network()
    
    def _init_network(self):
        dims = [self.input_dim] + [self.hidden_dim] * self.n_layers + [self.output_dim]
        for i in range(len(dims) - 1):
            std = math.sqrt(2.0 / (dims[i] + dims[i+1]))
            self.weights.append(np.random.randn(dims[i], dims[i+1]) * std)
            self.biases.append(np.zeros(dims[i+1]))
    
    def sigmoid(self, x: np.ndarray) -> np.ndarray:
        return 1.0 / (1.0 + np.exp(-np.clip(x, -500, 500)))
    
    def forward(self, x: np.ndarray) -> np.ndarray:
        h = x
        for i in range(self.n_layers):
            h = self.sigmoid(h @ self.weights[i] + self.biases[i])
        return h @ self.weights[-1] + self.biases[-1]
    
    def physics_loss(self, x: np.ndarray, u: np.ndarray, 
                   physics_fn: Callable[[np.ndarray, np.ndarray], np.ndarray]) -> float:
        residual = physics_fn(x, u)
        return float(np.mean(residual ** 2))
    
    def train_step(self, x_data: np.ndarray, u_data: np.ndarray,
                   x_physics: np.ndarray, physics_fn: Callable,
                   lr: float = 1e-3, lambda_physics: float = 1.0) -> float:
        u_pred = self.forward(x_data)
        data_loss = float(np.mean((u_data - u_pred) ** 2))
        phys_loss = self.physics_loss(x_physics, self.forward(x_physics), physics_fn)
        return data_loss + lambda_physics * phys_loss


# =============================================================================
# NERF FOR 3D RECONSTRUCTION
# =============================================================================

class NeRF3D:
    """Neural Radiance Field for 3D scene reconstruction."""
    
    def __init__(self, pos_dim: int = 3, dir_dim: int = 3, hidden_dim: int = 128):
        self.pos_dim = pos_dim
        self.dir_dim = dir_dim
        self.hidden_dim = hidden_dim
    
    def positional_encoding(self, x: np.ndarray, L: int = 10) -> np.ndarray:
        encoded = []
        for i in range(L):
            freq = 2.0 ** i
            encoded.append(np.sin(freq * math.pi * x))
            encoded.append(np.cos(freq * math.pi * x))
        return np.concatenate(encoded, axis=-1)
    
    def render_ray(self, ray_origin: np.ndarray, ray_dir: np.ndarray,
                   near: float = 0.0, far: float = 10.0, n_samples: int = 64) -> Tuple[np.ndarray, np.ndarray]:
        t_vals = np.linspace(near, far, n_samples)
        pts = ray_origin + t_vals[:, None] * ray_dir
        
        rgb = np.random.rand(n_samples, 3) * 0.5 + 0.25
        sigma = np.random.rand(n_samples) * 0.1
        
        delta = np.diff(t_vals)
        alpha = 1 - np.exp(-sigma * np.append(delta, delta[-1]))
        weights = alpha * np.cumprod(1 - alpha + 1e-10)
        
        rgb_map = np.sum(weights[:, None] * rgb, axis=0)
        depth_map = np.sum(weights * t_vals, axis=0)
        
        return rgb_map, depth_map


# =============================================================================
# SPECTRAL CLUSTERING
# =============================================================================

def spectral_clustering(X: np.ndarray, n_clusters: int = 2) -> np.ndarray:
    """Simplified spectral clustering."""
    from sklearn.cluster import KMeans
    
    n = len(X)
    sq_dists = np.sum((X[:, None, :] - X[None, :, :]) ** 2, axis=-1)
    sigma = np.median(sq_dists) + 1e-10
    similarity = np.exp(-sq_dists / (2 * sigma ** 2))
    
    D = np.diag(np.sum(similarity, axis=1))
    L = D - similarity
    
    eigenvalues, eigenvectors = np.linalg.eigh(L)
    V = eigenvectors[:, :n_clusters]
    
    kmeans = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
    labels = kmeans.fit_predict(V)
    
    return labels


def eo_anomaly_score(features: Dict[str, float]) -> Tuple[float, str]:
    """
    Computes a simple anomaly score for EO data based on band statistics.

    For now this is purely threshold-based:
    - If standard deviation is extremely low across all bands, data may be flat/saturated.
    - If means are near 0 or 1, data may be clipped.
    """
    stds = [features["std_band_0"], features["std_band_1"], features["std_band_2"]]
    means = [features["mean_band_0"], features["mean_band_1"], features["mean_band_2"]]

    avg_std = sum(stds) / len(stds)
    avg_mean = sum(means) / len(means)

    score = 0.0
    reasons = []

    if avg_std < 0.02:
        score += 0.6
        reasons.append("very_low_variance")

    if avg_mean < 0.05 or avg_mean > 0.95:
        score += 0.4
        reasons.append("extreme_mean")

    if score == 0.0:
        flag = "OK"
    elif score < 0.5:
        flag = "MILD_ANOMALY"
    else:
        flag = "ANOMALOUS"

    return score, ";".join(reasons) if reasons else "none"


def log_window_anomaly_score(features: Dict[str, float]) -> Tuple[float, str]:
    """
    ML-driven anomaly score for a window of log events using an Isolation Forest.
    Detects complex insider threats and unusual operational tempo based on the 
    historical baseline model.
    """
    events_count = features.get("events_count", 1.0)
    failed_logins = features.get("failed_logins", 0.0)
    critical_events = features.get("critical_events", 0.0)
    
    X_test = np.array([[events_count, failed_logins, critical_events]])
    
    # Predict returns 1 for inliers (normal) and -1 for outliers (anomaly)
    prediction = _ids_clf.predict(X_test)[0]
    
    # decision_function returns anomaly scores (lower/negative = more anomalous)
    raw_score = _ids_clf.decision_function(X_test)[0] 
    
    # We map raw_score from roughly [-0.5, 0.5] to a [0.0, 1.0] danger level
    mapped_score = max(0.0, min(1.0, 0.5 - raw_score))
    
    reasons = []
    
    if prediction == -1:
        reasons.append(f"ML_IsolationForest_Anomaly (Raw Score: {raw_score:.3f})")
    
    # Critical events are always suspicious regardless of ML model
    if critical_events > 0:
        mapped_score = max(mapped_score, 0.7)
        reasons.append("Critical events present")
    
    if failed_logins > 3:
        mapped_score = max(mapped_score, 0.5)
        reasons.append("High failed logins")
    
    if events_count > 200:
        mapped_score = max(mapped_score, 0.4)
        reasons.append("Unusual high volume of actions")
    
    if prediction == -1 or reasons:
        return mapped_score, "; ".join(reasons) if reasons else "Anomaly detected"
    
    return 0.0, "none"

