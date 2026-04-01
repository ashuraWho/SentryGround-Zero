// Simulated 28×28 single-channel acquisition geometry (matches train_model conv input).
#pragma once

#ifdef _OPENMP
#include <omp.h>
#endif

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

// Astrophysical background containing a Dark Matter NFW profile projection
inline void fill_nfw_halo_frame(float* hw_rowmajor, std::uint32_t seed) {
    std::uint32_t s = seed ? seed : 1u;
    const float center_x = kSensorW / 2.0f;
    const float center_y = kSensorH / 2.0f;
    const float I_0 = 0.3f; // Central column density intensity
    const float R_s = 5.0f; // Scale radius of the dark matter halo
    
    #pragma omp parallel for
    for (int y = 0; y < kSensorH; ++y) {
        for (int x = 0; x < kSensorW; ++x) {
            std::uint32_t s_local = s + y * kSensorW + x;
            float dx = x - center_x;
            float dy = y - center_y;
            float r = std::sqrt(dx*dx + dy*dy);
            
            // 2D pseudo-NFW projection approximation
            float signal = I_0 / ( (r/R_s) * std::pow(1.0f + r/R_s, 2.0f) + 0.1f );
            
            // Cosmic background Poisson-like noise
            float noise = (lcg_uniform_01(&s_local) - 0.1f) * 0.5f; 
            
            float pixel_val = signal + noise;
            if (pixel_val > 1.0f) pixel_val = 1.0f;
            if (pixel_val < 0.0f) pixel_val = 0.0f;
            
            hw_rowmajor[y * kSensorW + x] = pixel_val;
        }
    }
}

// Exoplanet Transit simulation: A U-shaped or V-shaped lightcurve dip
inline void fill_exoplanet_frame(float* hw_rowmajor, std::uint32_t seed) {
    std::uint32_t s = seed ? seed : 1u;
    const float baseline_flux = 0.9f;
    
    #pragma omp parallel for
    for (int y = 0; y < kSensorH; ++y) {
        for (int x = 0; x < kSensorW; ++x) {
            std::uint32_t s_local = s + y + x;
            // Let x be the "Time" axis for the lightcurve.
            float t = static_cast<float>(x);
            float transit_center = kSensorW / 2.0f;
            float distance = std::abs(t - transit_center);
            
            float dip = 0.0f;
            if (distance < 4.0f) {
                // simple U-shaped occultation
                dip = 0.4f * std::cos(distance * 3.14159f / 8.0f); 
            }
            
            float noise = (lcg_uniform_01(&s_local) - 0.1f) * 0.1f;
            float flux = baseline_flux - dip + noise;
            
            // Replicate line across Y axis for simplicity in 2D array mapping
            if (flux > 1.0f) flux = 1.0f;
            if (flux < 0.0f) flux = 0.0f;
            
            hw_rowmajor[y * kSensorW + x] = flux;
        }
    }
}

// Earth Observation snapshot: Continents, Oceans and Clouds (Multispectral proxy)
inline void fill_earth_frame(float* hw_rowmajor, std::uint32_t seed) {
    std::uint32_t s = seed ? seed : 1u;
    
    #pragma omp parallel for
    for (int y = 0; y < kSensorH; ++y) {
        for (int x = 0; x < kSensorW; ++x) {
            std::uint32_t s_local = s + y * 97 + x;
            // Some generative pseudo-fractal noise for terrain
            float val = std::sin(x * 0.3f) * std::cos(y * 0.3f) * 0.5f + 0.5f;
            float cloud = lcg_uniform_01(&s_local);
            if (cloud > 0.15f) cloud = 0.0f; else cloud = 0.4f; // sparse clouds
            
            float pixel_val = val * 0.6f + cloud;
            if (pixel_val > 1.0f) pixel_val = 1.0f;
            if (pixel_val < 0.0f) pixel_val = 0.0f;
            
            hw_rowmajor[y * kSensorW + x] = pixel_val;
        }
    }
}

// Deep-field survey: dim interstellar background + sparse unresolved sources
inline void fill_deep_space_frame(float* hw_rowmajor, std::uint32_t seed) {
    std::uint32_t s = seed ? seed : 1u;
    #pragma omp parallel for
    for (int y = 0; y < kSensorH; ++y) {
        for (int x = 0; x < kSensorW; ++x) {
            std::uint32_t s_local = s + static_cast<std::uint32_t>(y * kSensorW + x);
            float v = lcg_uniform_01(&s_local) * 0.08f;
            if ((lcg_next(&s_local) % 19u) == 0u)
                v += 0.45f + lcg_uniform_01(&s_local) * 0.45f;
            if (v > 1.0f) v = 1.0f;
            hw_rowmajor[y * kSensorW + x] = v;
        }
    }
}

// Unresolved / lightly resolved stellar disk (smooth core + diffraction-like ring hint)
inline void fill_stellar_frame(float* hw_rowmajor, std::uint32_t seed) {
    std::uint32_t s = seed ? seed : 1u;
    const float cx = kSensorW / 2.0f;
    const float cy = kSensorH / 2.0f;
    #pragma omp parallel for
    for (int y = 0; y < kSensorH; ++y) {
        for (int x = 0; x < kSensorW; ++x) {
            std::uint32_t s_local = s + static_cast<std::uint32_t>(y * kSensorW + x);
            float dx = static_cast<float>(x) - cx;
            float dy = static_cast<float>(y) - cy;
            float r2 = dx * dx + dy * dy;
            float core = std::exp(-r2 / 22.0f);
            float ring = 0.12f * std::exp(-std::pow(std::sqrt(r2) - 9.0f, 2) / 3.0f);
            float noise = (lcg_uniform_01(&s_local) - 0.1f) * 0.1f;
            float v = core * 0.92f + ring + noise;
            if (v > 1.0f) v = 1.0f;
            if (v < 0.0f) v = 0.0f;
            hw_rowmajor[y * kSensorW + x] = v;
        }
    }
}

// Educative black-hole shadow + photon-ring proxy (axisymmetric, smooth)
inline void fill_black_hole_frame(float* hw_rowmajor, std::uint32_t seed) {
    std::uint32_t s = seed ? seed : 1u;
    const float cx = kSensorW / 2.0f;
    const float cy = kSensorH / 2.0f;
    #pragma omp parallel for
    for (int y = 0; y < kSensorH; ++y) {
        for (int x = 0; x < kSensorW; ++x) {
            std::uint32_t s_local = s + static_cast<std::uint32_t>(y * kSensorW + x);
            float dx = static_cast<float>(x) - cx;
            float dy = static_cast<float>(y) - cy;
            float r = std::sqrt(dx * dx + dy * dy);
            float ring = 0.78f * std::exp(-std::pow(r - 8.0f, 2) / 5.0f);
            float shadow = (r < 4.0f) ? 0.03f : 0.0f;
            float noise = (lcg_uniform_01(&s_local) - 0.1f) * 0.06f;
            float v = ring + shadow + noise;
            if (v > 1.0f) v = 1.0f;
            if (v < 0.0f) v = 0.0f;
            hw_rowmajor[y * kSensorW + x] = v;
        }
    }
}

// Chirp-like strain proxy mapped onto the patch (smooth phase evolution along x)
inline void fill_gravitational_wave_frame(float* hw_rowmajor, std::uint32_t seed) {
    std::uint32_t s = seed ? seed : 1u;
    #pragma omp parallel for
    for (int y = 0; y < kSensorH; ++y) {
        for (int x = 0; x < kSensorW; ++x) {
            std::uint32_t s_local = s + static_cast<std::uint32_t>(y + x);
            float tx = static_cast<float>(x) / static_cast<float>(kSensorW);
            float phase = 6.2831853f * tx * tx * 10.0f;
            float amp = 0.22f * std::sin(phase);
            float noise = (lcg_uniform_01(&s_local) - 0.1f) * 0.07f;
            float v = 0.48f + amp + noise;
            if (v > 1.0f) v = 1.0f;
            if (v < 0.0f) v = 0.0f;
            hw_rowmajor[y * kSensorW + x] = v;
        }
    }
}

// Small-body reflectance map: irregular albedo + limb darkening proxy
inline void fill_asteroid_frame(float* hw_rowmajor, std::uint32_t seed) {
    std::uint32_t s = seed ? seed : 1u;
    const float cx = kSensorW / 2.0f;
    const float cy = kSensorH / 2.0f;
    #pragma omp parallel for
    for (int y = 0; y < kSensorH; ++y) {
        for (int x = 0; x < kSensorW; ++x) {
            std::uint32_t s_local = s + static_cast<std::uint32_t>(y * 131 + x * 17);
            float dx = (static_cast<float>(x) - cx) / 6.5f;
            float dy = (static_cast<float>(y) - cy) / 4.5f;
            float r = std::sqrt(dx * dx + dy * dy);
            float rugged = 0.35f * std::sin(dx * 4.2f) * std::cos(dy * 3.1f);
            float body = (r < 1.15f) ? (0.52f + rugged) : (0.1f + lcg_uniform_01(&s_local) * 0.18f);
            body += (lcg_uniform_01(&s_local) - 0.1f) * 0.07f;
            if (body > 1.0f) body = 1.0f;
            if (body < 0.0f) body = 0.0f;
            hw_rowmajor[y * kSensorW + x] = body;
        }
    }
}

// Terrestrial climate proxy: banded jets / fronts on top of surface albedo
inline void fill_earth_climate_frame(float* hw_rowmajor, std::uint32_t seed) {
    std::uint32_t s = seed ? seed : 1u;
    #pragma omp parallel for
    for (int y = 0; y < kSensorH; ++y) {
        for (int x = 0; x < kSensorW; ++x) {
            std::uint32_t s_local = s + static_cast<std::uint32_t>(y * 97 + x);
            float jet = 0.18f * std::sin(static_cast<float>(y + x) * 0.38f);
            float base = std::sin(x * 0.32f) * std::cos(y * 0.28f) * 0.5f + 0.5f;
            float cloud = (lcg_uniform_01(&s_local) > 0.80f) ? 0.32f : 0.0f;
            float v = base * 0.52f + jet + cloud;
            if (v > 1.0f) v = 1.0f;
            if (v < 0.0f) v = 0.0f;
            hw_rowmajor[y * kSensorW + x] = v;
        }
    }
}

// Multi-mission survey: blend of representative smooth fields (educational composite)
inline void fill_survey_frame(float* hw_rowmajor, std::uint32_t seed) {
    float a[kSensorElements];
    float b[kSensorElements];
    float c[kSensorElements];
    float d[kSensorElements];
    fill_nfw_halo_frame(a, seed);
    fill_exoplanet_frame(b, seed ^ 0xA5A5A5A5u);
    fill_earth_frame(c, seed ^ 0x5A5A5A5Au);
    fill_stellar_frame(d, seed ^ 0xC3C3C3C3u);
    for (std::size_t i = 0; i < kSensorElements; ++i) {
        float v = 0.25f * (a[i] + b[i] + c[i] + d[i]);
        if (v > 1.0f) v = 1.0f;
        if (v < 0.0f) v = 0.0f;
        hw_rowmajor[i] = v;
    }
}

// Anomalous acquisition: Deep Space Cosmic Ray Hit (high energy saturation track)
inline void apply_cosmic_ray_hit(float* hw_rowmajor) {
    // Inject a diagonal cascade of high-energy pixels simulating a cosmic ray strike
    for (int i = 4; i < 22; ++i) {
        if (i < kSensorW && (i+3) < kSensorH) {
            hw_rowmajor[(i+3) * kSensorW + i] = 1.0f;
            if (i+1 < kSensorW) hw_rowmajor[(i+3) * kSensorW + i + 1] = 0.8f;
        }
    }
}
