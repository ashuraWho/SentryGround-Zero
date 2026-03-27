// Edge inference: optional TensorFlow Lite autoencoder MSE, else calibrated heuristic.
//
// THRESHOLD ALIGNMENT NOTE (Bug fix):
//   The heuristic backend uses a completely different scoring scale than the
//   TFLite backend (bright-pixel count / frame_size vs. true reconstruction MSE).
//   Because of this, the mse_threshold loaded from obc_model_meta.json — which is
//   calibrated on actual Keras reconstruction errors — is ONLY meaningful for the
//   TFLite path.  The heuristic backend has its own independent threshold that is
//   set from a separate JSON key ("heuristic_threshold") or falls back to a
//   hard-coded default (see HEURISTIC_DEFAULT_THRESHOLD).
//
//   This separation avoids the silent bug where a threshold of e.g. 0.003 (typical
//   for a well-trained autoencoder) would flag *every* frame as anomalous under the
//   heuristic score, whose values are on a completely different numerical scale.

#ifndef INFERENCE_ENGINE_H
#define INFERENCE_ENGINE_H

#include "memory_pool.h"
#include <memory>
#include <string>

// Opaque holder for TFLite interpreter when built with SENTRY_HAVE_TFLITE.
struct TfliteState;

class InferenceEngine {
public:
    // Default heuristic threshold: a frame with ~0.5% saturated pixels is flagged.
    // This is independent of the autoencoder MSE threshold in obc_model_meta.json.
    static constexpr float kHeuristicDefaultThreshold = 0.05f;

    explicit InferenceEngine(MemoryPool& pool);
    ~InferenceEngine();

    // image_data: row-major H×W float32, size must be kSensorElements (28×28).
    // Returns true if the frame is classified as anomalous.
    bool run_inference(const float* image_data, size_t size);

    // Last computed score: reconstruction MSE (TFLite path) or bright-pixel ratio
    // (heuristic path). The numerical scales differ; compare only to the threshold
    // reported by the corresponding backend.
    float last_mse() const { return last_mse_; }

    // Human-readable backend identifier: "tflite_fp32" or "heuristic_linear".
    const std::string& backend_name() const { return backend_name_; }

    // Active threshold for the current backend (matches the scale of last_mse()).
    float active_threshold() const { return active_threshold_; }

private:
    MemoryPool& memory_pool;

    // Threshold for the TFLite path — loaded from obc_model_meta.json.
    // Calibrated on reconstruction MSE produced by the trained Keras autoencoder.
    float tflite_threshold_ = 0.05f;

    // Threshold for the heuristic path — loaded from obc_model_meta.json key
    // "heuristic_threshold", or falls back to kHeuristicDefaultThreshold.
    // MUST NOT be set from "mse_threshold"; the scales are incompatible.
    float heuristic_threshold_ = kHeuristicDefaultThreshold;

    // Points to whichever threshold is currently active (backend-specific).
    float active_threshold_ = kHeuristicDefaultThreshold;

    float last_mse_ = 0.f;
    std::string backend_name_ = "heuristic_linear";

    bool use_tflite_ = false;
    std::unique_ptr<TfliteState> tflite_;

    bool run_tflite(const float* image_data, size_t size);
    bool run_heuristic(const float* image_data, size_t size);
};

#endif
