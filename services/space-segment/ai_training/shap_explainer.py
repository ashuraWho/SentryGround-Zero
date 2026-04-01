# Run SHAP DeepExplainer on the trained autoencoder and save anomaly attributions.
from __future__ import annotations

import argparse

import numpy as np
import shap
import tensorflow as tf

from model_io import make_calibration_batch, make_shap_probes

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="autoencoder.h5", help="Trained Keras weights file")
    args = parser.parse_args()

    print("Loading model...")
    model = tf.keras.models.load_model(args.model)

    x_test_norm, x_test_anom = make_shap_probes(model)

    print("Setting up SHAP DeepExplainer...")
    background = make_calibration_batch(model, n=100)

    explainer = shap.DeepExplainer(model, background)

    print("Calculating SHAP values for normal sample...")
    shap_idx_norm = explainer.shap_values(x_test_norm)

    print("Calculating SHAP values for anomalous sample...")
    shap_idx_anom = explainer.shap_values(x_test_anom)

    np.save("shap_anomaly.npy", shap_idx_anom)
    np.save("shap_normal.npy", shap_idx_norm)
    print("Saved shap_anomaly.npy and shap_normal.npy")
