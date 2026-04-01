"""
Advanced ML Models for Satellite Data Analysis
Includes autoencoders, LSTMs, and object detection.
"""

import numpy as np
from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass


class SatelliteAutoencoder:
    """
    Convolutional Autoencoder for satellite imagery anomaly detection.
    """
    
    def __init__(self, input_shape: Tuple[int, int, int] = (256, 256, 4)):
        self.input_shape = input_shape
        self.latent_dim = 64
        self._weights = {}
        self._biases = {}
        self._init_weights()
    
    def _init_weights(self):
        import math
        
        channels = [self.input_shape[-1], 32, 64, 128, self.latent_dim]
        
        for i in range(len(channels) - 1):
            fan_in = channels[i]
            fan_out = channels[i + 1]
            std = math.sqrt(2.0 / (fan_in + fan_out))
            self._weights[f'W_enc_{i}'] = np.random.randn(fan_in, fan_out) * std
            self._biases[f'b_enc_{i}'] = np.zeros(fan_out)
        
        channels_rev = list(reversed(channels))
        for i in range(len(channels_rev) - 1):
            fan_in = channels_rev[i]
            fan_out = channels_rev[i + 1]
            std = math.sqrt(2.0 / (fan_in + fan_out))
            self._weights[f'W_dec_{i}'] = np.random.randn(fan_in, fan_out) * std
            self._biases[f'b_dec_{i}'] = np.zeros(fan_out)
    
    def relu(self, x: np.ndarray) -> np.ndarray:
        return np.maximum(0, x)
    
    def sigmoid(self, x: np.ndarray) -> np.ndarray:
        return 1.0 / (1.0 + np.exp(-np.clip(x, -500, 500)))
    
    def encode(self, x: np.ndarray) -> np.ndarray:
        h = x
        for i in range(4):
            w = self._weights.get(f'W_enc_{i}', self._weights['W_enc_0'])
            b = self._biases.get(f'b_enc_{i}', self._biases['b_enc_0'])
            h = self.relu(h @ w + b)
        return h
    
    def decode(self, z: np.ndarray) -> np.ndarray:
        h = z
        for i in range(4):
            w = self._weights.get(f'W_dec_{i}', self._weights['W_dec_0'])
            b = self._biases.get(f'b_dec_{i}', self._biases['b_dec_0'])
            h = self.relu(h @ w + b)
        return self.sigmoid(h)
    
    def forward(self, x: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        z = self.encode(x)
        x_recon = self.decode(z)
        return x_recon, z
    
    def reconstruction_error(self, x: np.ndarray) -> float:
        x_recon, _ = self.forward(x)
        return float(np.mean((x - x_recon) ** 2))
    
    def detect_anomaly(self, x: np.ndarray, threshold: float = 0.01) -> Tuple[bool, float]:
        error = self.reconstruction_error(x)
        is_anomaly = error > threshold
        return is_anomaly, error


class SatelliteLSTM:
    """
    LSTM for satellite telemetry prediction and anomaly detection.
    Predicts future states based on historical telemetry.
    """
    
    def __init__(self, input_dim: int, hidden_dim: int = 128, output_dim: int = 1):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        
        self._Wf = np.random.randn(input_dim + hidden_dim, hidden_dim) * 0.1
        self._Wi = np.random.randn(input_dim + hidden_dim, hidden_dim) * 0.1
        self._Wc = np.random.randn(input_dim + hidden_dim, hidden_dim) * 0.1
        self._Wo = np.random.randn(input_dim + hidden_dim, hidden_dim) * 0.1
        self._Wy = np.random.randn(hidden_dim, output_dim) * 0.1
        
        self._bf = np.zeros((1, hidden_dim))
        self._bi = np.zeros((1, hidden_dim))
        self._bc = np.zeros((1, hidden_dim))
        self._bo = np.zeros((1, hidden_dim))
        self._by = np.zeros((1, output_dim))
    
    def sigmoid(self, x: np.ndarray) -> np.ndarray:
        return 1.0 / (1.0 + np.exp(-np.clip(x, -500, 500)))
    
    def tanh(self, x: np.ndarray) -> np.ndarray:
        return np.tanh(x)
    
    def forward_step(self, x_t: np.ndarray, h_prev: np.ndarray, c_prev: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        combined = np.hstack([x_t, h_prev])
        
        f = self.sigmoid(combined @ self._Wf + self._bf)
        i = self.sigmoid(combined @ self._Wi + self._bi)
        c_tilde = self.tanh(combined @ self._Wc + self._bc)
        o = self.sigmoid(combined @ self._Wo + self._bo)
        
        c = f * c_prev + i * c_tilde
        h = o * self.tanh(c)
        
        return h, c
    
    def forward_sequence(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        seq_len, _ = X.shape
        h = np.zeros((1, self.hidden_dim))
        c = np.zeros((1, self.hidden_dim))
        
        h_sequence = []
        
        for t in range(seq_len):
            h, c = self.forward_step(X[t:t+1], h, c)
            h_sequence.append(h)
        
        h_sequence = np.vstack(h_sequence)
        y = h_sequence @ self._Wy + self._by
        
        return y, h_sequence
    
    def predict_next(self, sequence: np.ndarray) -> np.ndarray:
        _, h_sequence = self.forward_sequence(sequence)
        last_h = h_sequence[-1:]
        prediction = last_h @ self._Wy + self._by
        return prediction
    
    def detect_sequence_anomaly(self, sequence: np.ndarray, threshold: float = 0.5) -> Tuple[bool, float]:
        prediction = self.predict_next(sequence)
        
        actual = sequence[-1:]
        error = float(np.mean((actual - prediction) ** 2))
        
        is_anomaly = error > threshold
        return is_anomaly, error


class ObjectDetector:
    """
    Simplified object detection for satellite imagery.
    Detects ships, aircraft, vehicles, buildings.
    """
    
    def __init__(self):
        self.classes = {
            0: "ship",
            1: "aircraft",
            2: "vehicle",
            3: "building",
            4: "cloud",
        }
        self._anchors = self._generate_anchors()
    
    def _generate_anchors(self) -> np.ndarray:
        sizes = [
            (8, 8), (16, 16), (32, 32), (64, 64),
            (12, 8), (16, 12), (24, 24), (48, 48),
        ]
        return np.array(sizes, dtype=np.float32)
    
    def preprocess(self, image: np.ndarray, target_size: Tuple[int, int] = (416, 416)) -> np.ndarray:
        h, w = image.shape[:2]
        target_h, target_w = target_size
        
        scale = min(target_w / w, target_h / h)
        new_w, new_h = int(w * scale), int(h * scale)
        
        resized = self._resize_image(image, (new_w, new_h))
        
        padded = np.zeros((target_h, target_w, image.shape[-1]))
        padded[:new_h, :new_w] = resized
        
        normalized = padded / 255.0
        
        return normalized.astype(np.float32)
    
    def _resize_image(self, image: np.ndarray, size: Tuple[int, int]) -> np.ndarray:
        from scipy.ndimage import zoom
        h, w = image.shape[:2]
        target_w, target_h = size
        zoom_factors = (target_h / h, target_w / w, 1)
        return zoom(image, zoom_factors, order=1)
    
    def detect(self, image: np.ndarray, conf_threshold: float = 0.5) -> List[Dict]:
        preprocessed = self.preprocess(image)
        
        detections = self._feature_extract(preprocessed)
        
        results = []
        for det in detections:
            if det['confidence'] >= conf_threshold:
                results.append({
                    'bbox': det['bbox'],
                    'class': self.classes[det['class_id']],
                    'class_id': det['class_id'],
                    'confidence': det['confidence'],
                })
        
        return self._nms(results)
    
    def _feature_extract(self, image: np.ndarray) -> List[Dict]:
        import scipy.ndimage as ndimage
        
        detections = []
        
        gray = np.mean(image, axis=-1) if image.ndim == 3 else image
        
        edges = ndimage.sobel(gray)
        
        high_intensity = gray > np.percentile(gray, 90)
        
        labeled, num_features = ndimage.label(high_intensity)
        
        for i in range(1, num_features + 1):
            component = labeled == i
            if np.sum(component) < 10:
                continue
            
            y_coords, x_coords = np.where(component)
            
            y_min, y_max = y_coords.min(), y_coords.max()
            x_min, x_max = x_coords.min(), x_coords.max()
            
            height = y_max - y_min
            width = x_max - x_min
            
            if height < 5 or width < 5:
                continue
            
            area = height * width
            density = np.sum(edges[y_coords, x_coords]) / area if area > 0 else 0
            
            if density > 0.1:
                class_id = 3
            elif area > 100:
                class_id = 0
            else:
                class_id = 2
            
            confidence = min(0.95, 0.3 + density * 2)
            
            detections.append({
                'bbox': [float(x_min), float(y_min), float(x_max), float(y_max)],
                'class_id': class_id,
                'confidence': confidence,
            })
        
        return detections
    
    def _nms(self, detections: List[Dict], iou_threshold: float = 0.5) -> List[Dict]:
        if not detections:
            return []
        
        detections = sorted(detections, key=lambda x: x['confidence'], reverse=True)
        
        keep = []
        
        while detections:
            best = detections.pop(0)
            keep.append(best)
            
            remaining = []
            for det in detections:
                iou = self._compute_iou(best['bbox'], det['bbox'])
                if iou < iou_threshold:
                    remaining.append(det)
            
            detections = remaining
        
        return keep
    
    def _compute_iou(self, box1: List[float], box2: List[float]) -> float:
        x1_min, y1_min, x1_max, y1_max = box1
        x2_min, y2_min, x2_max, y2_max = box2
        
        inter_x_min = max(x1_min, x2_min)
        inter_y_min = max(y1_min, y2_min)
        inter_x_max = min(x1_max, x2_max)
        inter_y_max = min(y1_max, y2_max)
        
        inter_area = max(0, inter_x_max - inter_x_min) * max(0, inter_y_max - inter_y_min)
        
        box1_area = (x1_max - x1_min) * (y1_max - y1_min)
        box2_area = (x2_max - x2_min) * (y2_max - y2_min)
        
        union_area = box1_area + box2_area - inter_area
        
        return inter_area / union_area if union_area > 0 else 0


class PredictiveMaintenance:
    """
    Predictive maintenance model for satellite systems.
    """
    
    def __init__(self):
        self.components = [
            "solar_panels",
            "battery",
            "propulsion",
            "communication",
            "thermal_control",
            "computer",
        ]
        
        self._health_states = {}
        for comp in self.components:
            self._health_states[comp] = 1.0
    
    def update_health(self, component: str, metrics: Dict[str, float]) -> Dict:
        if component not in self.components:
            return {"error": "Unknown component"}
        
        current = self._health_states[component]
        
        degradation = 0.0
        
        if "temperature" in metrics:
            temp = metrics["temperature"]
            if temp > 40:
                degradation += 0.01 * (temp - 40)
        
        if "voltage" in metrics:
            voltage = metrics["voltage"]
            if voltage < 28:
                degradation += 0.02 * (28 - voltage)
        
        if "current" in metrics:
            current_draw = metrics["current"]
            if current_draw > 10:
                degradation += 0.005 * (current_draw - 10)
        
        new_health = max(0.0, current - degradation)
        self._health_states[component] = new_health
        
        return {
            "component": component,
            "previous_health": current,
            "current_health": new_health,
            "degradation_rate": degradation,
            "status": self._assess_status(new_health),
            "mtbf_days": self._estimate_mtbf(new_health),
            "recommended_action": self._get_action(new_health),
        }
    
    def _assess_status(self, health: float) -> str:
        if health > 0.9:
            return "NOMINAL"
        elif health > 0.7:
            return "GOOD"
        elif health > 0.5:
            return "FAIR"
        elif health > 0.3:
            return "DEGRADED"
        else:
            return "CRITICAL"
    
    def _estimate_mtbf(self, health: float) -> float:
        base_mtbf = 3650
        return base_mtbf * health
    
    def _get_action(self, health: float) -> str:
        if health > 0.8:
            return "Continue normal operations"
        elif health > 0.6:
            return "Schedule maintenance window"
        elif health > 0.4:
            return "Prioritize component replacement"
        else:
            return "IMMEDIATE action required"


class FederatedLearner:
    """
    Federated learning for privacy-preserving satellite data analysis.
    """
    
    def __init__(self, model: any, num_clients: int = 5):
        self.global_model = model
        self.num_clients = num_clients
        self.client_weights = []
        self.client_updates = []
    
    def aggregate(self, client_weights: List[Dict], client_data_sizes: List[int]) -> Dict:
        """
        Aggregate model updates from multiple clients using Federated Averaging.
        """
        total_size = sum(client_data_sizes)
        
        aggregated = {}
        for key in client_weights[0].keys():
            weighted_sum = np.zeros_like(client_weights[0][key])
            for i, weights in enumerate(client_weights):
                if key in weights:
                    weight_factor = client_data_sizes[i] / total_size
                    weighted_sum += weights[key] * weight_factor
            aggregated[key] = weighted_sum
        
        return aggregated
    
    def distribute_global_model(self) -> Dict:
        """
        Distribute global model to clients.
        """
        return self.global_model


def create_satellite_detector() -> ObjectDetector:
    """Factory function to create object detector."""
    return ObjectDetector()


def create_telemetry_predictor(input_dim: int = 10) -> SatelliteLSTM:
    """Factory function to create telemetry predictor."""
    return SatelliteLSTM(input_dim=input_dim)


def create_anomaly_detector(input_shape: Tuple[int, int, int] = (256, 256, 4)) -> SatelliteAutoencoder:
    """Factory function to create anomaly detector."""
    return SatelliteAutoencoder(input_shape=input_shape)
