# Convert trained Keras autoencoder to INT8 TFLite plus a C byte array source file.
from __future__ import annotations

import argparse

import tensorflow as tf

# Build calibration tensors that match conv vs dense graph layouts.
from model_io import make_calibration_batch

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="autoencoder.h5", help="Trained Keras weights file")
    args = parser.parse_args()

    print("Loading model...")
    model = tf.keras.models.load_model(args.model)

    print("Generating representative dataset for INT8 quantization...")
    x_train = make_calibration_batch(model, n=100)

    def representative_dataset():
        for i in range(100):
            yield [x_train[i : i + 1]]

    print("Converting to TFLite (INT8)...")
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.representative_dataset = representative_dataset
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    converter.inference_input_type = tf.int8
    converter.inference_output_type = tf.int8

    tflite_quant_model = converter.convert()

    tflite_path = "anomaly_model.tflite"
    with open(tflite_path, "wb") as f:
        f.write(tflite_quant_model)
    print(f"Quantized TFLite model saved to {tflite_path}")

    print("Converting to C array...")
    with open("anomaly_model_data.cc", "w") as f:
        f.write("#include <cstdint>\n\n")
        f.write("alignas(16) const unsigned char g_anomaly_model_data[] = {\n")

        hex_array = [f"0x{b:02x}" for b in tflite_quant_model]

        for i in range(0, len(hex_array), 12):
            f.write("    " + ", ".join(hex_array[i : i + 12]) + ",\n")

        f.write("};\n")
        f.write(f"const int g_anomaly_model_data_len = {len(tflite_quant_model)};\n")

    print("Saved C array to anomaly_model_data.cc")
