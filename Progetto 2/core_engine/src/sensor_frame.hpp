// Simulated 28×28 single-channel acquisition geometry (matches train_model conv input).
#pragma once

#include <cmath>
#include <cstddef>
#include <cstdint>

// Height/width of the downlinked sensor patch (same as config.default.json synthetic img_size).
constexpr int kSensorH = 28;
constexpr int kSensorW = 28;
// Scalar count after flattening row-major (HW layout).
constexpr std::size_t kSensorElements = static_cast<std::size_t>(kSensorH) * static_cast<std::size_t>(kSensorW);

// Tiny deterministic LCG for reproducible on-board noise (no libc rand dependency in tests).
inline std::uint32_t lcg_next(std::uint32_t* state) {
    *state = (*state * 1103515245u + 12345u);
    return *state;
}

// Uniform float in [0, high] from LCG bites (good enough for a bench simulator).
inline float lcg_uniform_01(std::uint32_t* state) {
    const std::uint32_t x = lcg_next(state);
    return (static_cast<float>(x & 0x00FFFFFFu) / static_cast<float>(0x01000000)) * 0.2f;
}

// Nominal acquisition: spatially uncorrelated “dark field” noise ~[0, 0.2] like synthetic_frames.py.
inline void fill_nominal_sensor_frame(float* hw_rowmajor, std::uint32_t seed) {
    std::uint32_t s = seed ? seed : 1u;
    for (int i = 0; i < kSensorH * kSensorW; ++i) {
        hw_rowmajor[i] = lcg_uniform_01(&s);
    }
}

// Anomalous acquisition: same noise floor plus one saturated scan line (laser / row defect).
inline void fill_anomaly_streak_frame(float* hw_rowmajor, std::uint32_t seed, int bright_row = 14) {
    fill_nominal_sensor_frame(hw_rowmajor, seed);
    if (bright_row < 0) {
        bright_row = 0;
    }
    if (bright_row >= kSensorH) {
        bright_row = kSensorH - 1;
    }
    for (int c = 0; c < kSensorW; ++c) {
        hw_rowmajor[static_cast<std::size_t>(bright_row) * static_cast<std::size_t>(kSensorW) + static_cast<std::size_t>(c)] = 1.0f;
    }
}
