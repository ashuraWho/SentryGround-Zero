#include "inference_engine.h"

#include "sensor_frame.hpp"

#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <nlohmann/json.hpp>

#ifdef SENTRY_HAVE_TFLITE
#include <tensorflow/lite/interpreter_builder.h>
#include <tensorflow/lite/kernels/register.h>
#include <tensorflow/lite/model.h>

struct TfliteState {
    std::unique_ptr<tflite::FlatBufferModel> model;
    std::unique_ptr<tflite::Interpreter> interpreter;
};
#else
struct TfliteState {};
#endif

namespace {

namespace fs = std::filesystem;

fs::path resolve_meta_path() {
    if (const char* env = std::getenv("SENTRY_OBC_META")) {
        return fs::path(env);
    }
    // Default: from core_engine/build → ../../ai_training/obc_model_meta.json
    return fs::path("..") / ".." / "ai_training" / "obc_model_meta.json";
}

fs::path resolve_tflite_file(const nlohmann::json& meta, const fs::path& meta_path) {
    std::string rel = meta.value("tflite_fp32_relative",
                                 std::string("anomaly_model_fp32.tflite"));
    if (rel.empty()) return {};

    fs::path base = meta_path.parent_path();
    if (base.empty()) base = fs::current_path();

    fs::path candidate = base / rel;
    if (fs::exists(candidate)) return candidate;

    if (const char* env = std::getenv("SENTRY_TFLITE_PATH")) {
        fs::path epath(env);
        if (fs::exists(epath)) return epath;
    }
    return candidate;
}

}  // namespace

InferenceEngine::InferenceEngine(MemoryPool& pool) : memory_pool(pool) {
    std::cout << "[OBC-AI] Initializing Edge AI Inference Engine..." << std::endl;

    const fs::path meta_path = resolve_meta_path();
    nlohmann::json meta;

    if (std::ifstream f(meta_path); f.good()) {
        f >> meta;

        // ── TFLite threshold ──────────────────────────────────────────────────
        // "mse_threshold" is calibrated on true Keras reconstruction MSE.
        // It is ONLY valid for the TFLite inference path.
        tflite_threshold_ = meta.value("mse_threshold", tflite_threshold_);

        // ── Heuristic threshold ───────────────────────────────────────────────
        // "heuristic_threshold" is an INDEPENDENT key for the bright-pixel score
        // whose range is [0, 10*bright_fraction].  If not present in the JSON the
        // hard-coded default (kHeuristicDefaultThreshold) is kept.
        // DO NOT fall back to "mse_threshold" here — the scales are incompatible
        // and doing so would silently flag all frames as anomalous (MSE values from
        // a well-trained autoencoder are typically < 0.01, but the heuristic score
        // for a normal frame is typically 0.0–0.3).
        heuristic_threshold_ = meta.value("heuristic_threshold", heuristic_threshold_);

        std::cout << "[OBC-AI] Loaded meta " << meta_path
                  << " | tflite_threshold=" << tflite_threshold_
                  << " | heuristic_threshold=" << heuristic_threshold_ << std::endl;
    } else {
        std::cout << "[OBC-AI] Meta not found (" << meta_path
                  << "); using defaults — tflite_threshold=" << tflite_threshold_
                  << " heuristic_threshold=" << heuristic_threshold_ << std::endl;
    }

    // Initially assume heuristic path is used; updated below if TFLite loads.
    active_threshold_ = heuristic_threshold_;

#ifdef SENTRY_HAVE_TFLITE
    const fs::path tflite_file = resolve_tflite_file(meta, meta_path);
    if (!tflite_file.empty() && fs::exists(tflite_file)) {
        tflite_ = std::make_unique<TfliteState>();
        tflite_->model = tflite::FlatBufferModel::BuildFromFile(tflite_file.string().c_str());
        if (tflite_->model) {
            tflite::ops::builtin::BuiltinOpResolver resolver;
            tflite::InterpreterBuilder builder(*tflite_->model, resolver);
            builder(&tflite_->interpreter);
            if (tflite_->interpreter &&
                tflite_->interpreter->AllocateTensors() == kTfLiteOk) {
                use_tflite_     = true;
                backend_name_   = "tflite_fp32";
                active_threshold_ = tflite_threshold_;  // switch to MSE scale
                std::cout << "[OBC-AI] TFLite FP32 model: " << tflite_file << std::endl;
            }
        }
    }
    if (!use_tflite_) {
        std::cout << "[OBC-AI] TFLite not available or model missing"
                     " — using heuristic backend.\n";
    }
#else
    std::cout << "[OBC-AI] Built without SENTRY_HAVE_TFLITE — heuristic backend only.\n";
#endif
}

InferenceEngine::~InferenceEngine() = default;

bool InferenceEngine::run_tflite(const float* image_data, size_t size) {
#ifdef SENTRY_HAVE_TFLITE
    if (!tflite_ || !tflite_->interpreter) {
        return run_heuristic(image_data, size);
    }
    float* in = tflite_->interpreter->typed_input_tensor<float>(0);
    if (!in) {
        std::cerr << "[OBC-AI] TFLite input tensor is null or wrong type.\n";
        return run_heuristic(image_data, size);
    }
    const size_t in_bytes = tflite_->interpreter->input_tensor(0)->bytes;
    if (in_bytes < size * sizeof(float)) {
        std::cerr << "[OBC-AI] TFLite input smaller than frame ("
                  << in_bytes << " bytes).\n";
        return run_heuristic(image_data, size);
    }
    std::memcpy(in, image_data, size * sizeof(float));
    if (tflite_->interpreter->Invoke() != kTfLiteOk) {
        last_mse_ = 1e9f;
        return true;
    }
    float* out = tflite_->interpreter->typed_output_tensor<float>(0);
    if (!out) return run_heuristic(image_data, size);

    double acc = 0.0;
    for (size_t i = 0; i < size; ++i) {
        const double d = static_cast<double>(image_data[i])
                       - static_cast<double>(out[i]);
        acc += d * d;
    }
    last_mse_ = static_cast<float>(acc / static_cast<double>(size));
    if (last_mse_ > tflite_threshold_) {
        std::cout << "[OBC-AI] ALERT: reconstruction MSE " << last_mse_
                  << " > " << tflite_threshold_ << std::endl;
        return true;
    }
    return false;
#else
    return run_heuristic(image_data, size);
#endif
}

bool InferenceEngine::run_heuristic(const float* image_data, size_t size) {
    // Score = (count of pixels > 0.9) * 10 / frame_size
    // Range: [0, 10].  A normal dark-field frame has essentially zero saturated
    // pixels; a row-streak anomaly saturates 28/784 ≈ 3.6% → score ≈ 0.36.
    // The default heuristic_threshold of 0.05 therefore flags frames with >0.5%
    // saturated pixels, which is a reasonable conservative sentinel.
    std::cout << "[OBC-AI] Running heuristic inference..." << std::endl;
    float acc = 0.0f;
    for (size_t i = 0; i < size; ++i) {
        if (image_data[i] > 0.9f) {
            acc += 10.0f;
        }
    }
    last_mse_ = acc / static_cast<float>(size);
    std::cout << "[OBC-AI] Frame score (heuristic): " << last_mse_
              << " (threshold: " << heuristic_threshold_ << ")" << std::endl;
    if (last_mse_ > heuristic_threshold_) {
        std::cout << "[OBC-AI] ALERT: Anomaly suspected (heuristic)." << std::endl;
        return true;
    }
    return false;
}

bool InferenceEngine::run_inference(const float* image_data, size_t size) {
    if (size != kSensorElements) {
        std::cerr << "[OBC-AI] Expected " << kSensorElements
                  << " floats, got " << size << std::endl;
        last_mse_ = 0.f;
        return false;
    }
#ifdef SENTRY_HAVE_TFLITE
    if (use_tflite_ && tflite_) {
        return run_tflite(image_data, size);
    }
#endif
    return run_heuristic(image_data, size);
}
