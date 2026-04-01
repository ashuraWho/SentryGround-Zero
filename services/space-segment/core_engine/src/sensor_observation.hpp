// Per-satellite observation / instrument modes (28×28 single-channel patch).
// Applied after the base mission template from sensor_frame.hpp.
#pragma once

#include <cmath>
#include <cstdint>
#include <string>

#include "sensor_frame.hpp"

inline std::string normalize_observation_mode(const char* env_mode) {
    if (!env_mode || !env_mode[0]) {
        return "default";
    }
    std::string m(env_mode);
    for (char& c : m) {
        c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    }
    // collapse spaces to underscore
    for (char& c : m) {
        if (c == ' ' || c == '-') {
            c = '_';
        }
    }
    return m;
}

inline void clamp01(float& v) {
    if (v < 0.0f) {
        v = 0.0f;
    }
    if (v > 1.0f) {
        v = 1.0f;
    }
}

// In-place modulation: profile = normalized mission profile; mode = normalized observation code.
inline void apply_observation_modulation(const std::string& profile, const std::string& mode,
                                         float* hw, std::uint32_t seed) {
    if (mode.empty() || mode == "default") {
        return;
    }

    auto idx = [](int y, int x) { return y * kSensorW + x; };

    if (profile == "earth" || profile == "earth_observation" || profile == "earth_climate") {
        if (mode == "climate") {
            for (int y = 0; y < kSensorH; ++y) {
                for (int x = 0; x < kSensorW; ++x) {
                    float& v = hw[idx(y, x)];
                    v += 0.12f * std::sin(static_cast<float>(y + x) * 0.35f);
                    clamp01(v);
                }
            }
        } else if (mode == "vegetation") {
            for (int y = 0; y < kSensorH; ++y) {
                for (int x = 0; x < kSensorW; ++x) {
                    float& v = hw[idx(y, x)];
                    v += 0.18f * std::sin(x * 0.45f) * std::sin(y * 0.52f);
                    clamp01(v);
                }
            }
        } else if (mode == "desert") {
            for (int y = 0; y < kSensorH; ++y) {
                for (int x = 0; x < kSensorW; ++x) {
                    float& v = hw[idx(y, x)];
                    v = 0.82f * v + 0.08f * std::sin(y * 0.7f);
                    clamp01(v);
                }
            }
        } else if (mode == "ocean" || mode == "sea") {
            for (int y = 0; y < kSensorH; ++y) {
                for (int x = 0; x < kSensorW; ++x) {
                    float& v = hw[idx(y, x)];
                    v = 0.35f * v + 0.45f * std::sin(x * 0.22f) * std::sin(y * 0.18f);
                    clamp01(v);
                }
            }
        } else if (mode == "urban" || mode == "cities") {
            for (int y = 0; y < kSensorH; ++y) {
                for (int x = 0; x < kSensorW; ++x) {
                    float& v = hw[idx(y, x)];
                    if ((x % 5 == 0) || (y % 5 == 0)) {
                        v += 0.22f;
                    }
                    clamp01(v);
                }
            }
        }
    }

    if (profile == "earth_climate") {
        if (mode == "jet_stream" || mode == "jet") {
            for (int y = 0; y < kSensorH; ++y) {
                for (int x = 0; x < kSensorW; ++x) {
                    float& v = hw[idx(y, x)];
                    v += 0.14f * std::sin((x + 2 * y) * 0.31f);
                    clamp01(v);
                }
            }
        } else if (mode == "hadley_cell" || mode == "hadley") {
            for (int y = 0; y < kSensorH; ++y) {
                for (int x = 0; x < kSensorW; ++x) {
                    float& v = hw[idx(y, x)];
                    v += 0.1f * std::sin(y * 0.25f);
                    clamp01(v);
                }
            }
        } else if (mode == "storm_system" || mode == "storm") {
            for (int y = 0; y < kSensorH; ++y) {
                for (int x = 0; x < kSensorW; ++x) {
                    float dx = float(x - 16), dy = float(y - 12);
                    float& v = hw[idx(y, x)];
                    v += 0.25f * std::exp(-(dx * dx + dy * dy) / 15.0f);
                    clamp01(v);
                }
            }
        } else if (mode == "sea_ice" || mode == "ice") {
            for (int y = 0; y < kSensorH; ++y) {
                for (int x = 0; x < kSensorW; ++x) {
                    float& v = hw[idx(y, x)];
                    if (y < 8 || y > 20) {
                        v = std::min(1.0f, v + 0.35f);
                    }
                }
            }
        }
    }

    if (profile == "stellar") {
        if (mode == "photosphere") {
            for (int y = 0; y < kSensorH; ++y) {
                for (int x = 0; x < kSensorW; ++x) {
                    float& v = hw[idx(y, x)];
                    v = std::pow(v, 0.85f);
                    clamp01(v);
                }
            }
        } else if (mode == "sunspots" || mode == "starspots") {
            const int cx1 = 9, cy1 = 11, cx2 = 19, cy2 = 16;
            for (int y = 0; y < kSensorH; ++y) {
                for (int x = 0; x < kSensorW; ++x) {
                    float& v = hw[idx(y, x)];
                    float d1 = std::sqrt(float((x - cx1) * (x - cx1) + (y - cy1) * (y - cy1)));
                    float d2 = std::sqrt(float((x - cx2) * (x - cx2) + (y - cy2) * (y - cy2)));
                    if (d1 < 3.2f) {
                        v *= 0.35f;
                    }
                    if (d2 < 2.8f) {
                        v *= 0.4f;
                    }
                    clamp01(v);
                }
            }
        } else if (mode == "luminosity") {
            for (std::size_t i = 0; i < kSensorElements; ++i) {
                hw[i] = std::min(1.0f, hw[i] * 1.25f);
            }
        } else if (mode == "temperature" || mode == "temperature_map") {
            for (int y = 0; y < kSensorH; ++y) {
                for (int x = 0; x < kSensorW; ++x) {
                    float& v = hw[idx(y, x)];
                    float cx = std::abs(x - kSensorW / 2) + std::abs(y - kSensorH / 2);
                    v = v * (0.55f + 0.45f * (1.0f - cx / 28.0f));
                    clamp01(v);
                }
            }
        }
    } else if (profile == "deep_space") {
        if (mode == "galaxy_cluster") {
            for (int y = 0; y < kSensorH; ++y) {
                for (int x = 0; x < kSensorW; ++x) {
                    float& v = hw[idx(y, x)];
                    float dx = float(x - 14), dy = float(y - 14);
                    v += 0.35f * std::exp(-(dx * dx + dy * dy) / 40.0f);
                    clamp01(v);
                }
            }
        } else if (mode == "cmb_proxy" || mode == "cmb") {
            for (int y = 0; y < kSensorH; ++y) {
                for (int x = 0; x < kSensorW; ++x) {
                    float& v = hw[idx(y, x)];
                    v += 0.06f * std::sin(x * 0.9f + y * 0.7f);
                    clamp01(v);
                }
            }
        } else if (mode == "deep_field") {
            for (std::size_t i = 0; i < kSensorElements; ++i) {
                hw[i] = std::min(1.0f, hw[i] * 1.15f);
            }
        }
    } else if (profile == "dark_matter") {
        if (mode == "subhalo") {
            for (int y = 0; y < kSensorH; ++y) {
                for (int x = 0; x < kSensorW; ++x) {
                    float& v = hw[idx(y, x)];
                    float dx = float(x - 20), dy = float(y - 8);
                    v += 0.25f * std::exp(-(dx * dx + dy * dy) / 18.0f);
                    clamp01(v);
                }
            }
        } else if (mode == "merger_stream" || mode == "merger") {
            for (int y = 0; y < kSensorH; ++y) {
                for (int x = 0; x < kSensorW; ++x) {
                    float& v = hw[idx(y, x)];
                    v += 0.2f * std::exp(-std::pow(float(x - y) / 6.0f, 2));
                    clamp01(v);
                }
            }
        } else if (mode == "nfw_core" || mode == "core") {
            for (int y = 0; y < kSensorH; ++y) {
                for (int x = 0; x < kSensorW; ++x) {
                    float& v = hw[idx(y, x)];
                    float dx = float(x - 14), dy = float(y - 14);
                    v += 0.15f * std::exp(-(dx * dx + dy * dy) / 25.0f);
                    clamp01(v);
                }
            }
        }
    } else if (profile == "exoplanet") {
        if (mode == "transit") {
            for (int y = 0; y < kSensorH; ++y) {
                for (int x = 0; x < kSensorW; ++x) {
                    float& v = hw[idx(y, x)];
                    if (std::abs(x - 14) < 5) {
                        v *= 0.55f;
                    }
                    clamp01(v);
                }
            }
        } else if (mode == "phase_curve" || mode == "phase") {
            for (int y = 0; y < kSensorH; ++y) {
                for (int x = 0; x < kSensorW; ++x) {
                    float& v = hw[idx(y, x)];
                    v *= 0.75f + 0.25f * std::sin(float(x) * 0.4f);
                    clamp01(v);
                }
            }
        } else if (mode == "secondary_eclipse" || mode == "eclipse") {
            for (int y = 0; y < kSensorH; ++y) {
                for (int x = 0; x < kSensorW; ++x) {
                    float& v = hw[idx(y, x)];
                    if (std::abs(x - 8) < 3 || std::abs(x - 20) < 3) {
                        v *= 0.62f;
                    }
                    clamp01(v);
                }
            }
        } else if (mode == "reflection" || mode == "glint") {
            for (int y = 0; y < kSensorH; ++y) {
                for (int x = 0; x < kSensorW; ++x) {
                    float& v = hw[idx(y, x)];
                    if ((x + y) % 7 == 0) {
                        v = std::min(1.0f, v + 0.35f);
                    }
                }
            }
        }
    } else if (profile == "black_hole") {
        if (mode == "shadow") {
            for (int y = 0; y < kSensorH; ++y) {
                for (int x = 0; x < kSensorW; ++x) {
                    float& v = hw[idx(y, x)];
                    float r = std::sqrt(float((x - 14) * (x - 14) + (y - 14) * (y - 14)));
                    if (r < 5.0f) {
                        v *= 0.2f;
                    }
                    clamp01(v);
                }
            }
        } else if (mode == "accretion_disk" || mode == "disk") {
            for (int y = 0; y < kSensorH; ++y) {
                for (int x = 0; x < kSensorW; ++x) {
                    float& v = hw[idx(y, x)];
                    float r = std::sqrt(float((x - 14) * (x - 14) + (y - 14) * (y - 14)));
                    if (r > 6.0f && r < 11.0f) {
                        v = std::min(1.0f, v + 0.25f);
                    }
                    clamp01(v);
                }
            }
        } else if (mode == "jet_proxy" || mode == "jet") {
            for (int y = 0; y < kSensorH; ++y) {
                for (int x = 0; x < kSensorW; ++x) {
                    if (std::abs(x - 14) < 2) {
                        hw[idx(y, x)] = std::min(1.0f, hw[idx(y, x)] + 0.3f);
                    }
                }
            }
        } else if (mode == "ring_only" || mode == "ring") {
            for (int y = 0; y < kSensorH; ++y) {
                for (int x = 0; x < kSensorW; ++x) {
                    float& v = hw[idx(y, x)];
                    float r = std::sqrt(float((x - 14) * (x - 14) + (y - 14) * (y - 14)));
                    if (r < 7.0f) {
                        v *= 0.15f;
                    }
                    clamp01(v);
                }
            }
        }
    } else if (profile == "gravitational_wave") {
        if (mode == "ringdown") {
            for (int y = 0; y < kSensorH; ++y) {
                for (int x = 0; x < kSensorW; ++x) {
                    float& v = hw[idx(y, x)];
                    float t = static_cast<float>(x) / static_cast<float>(kSensorW);
                    v += 0.15f * std::sin(t * 25.0f) * std::exp(-t * 4.0f);
                    clamp01(v);
                }
            }
        } else if (mode == "stochastic_bg" || mode == "stochastic") {
            std::uint32_t s = seed ? seed : 1u;
            for (std::size_t i = 0; i < kSensorElements; ++i) {
                s = s * 1103515245u + 12345u;
                float n = static_cast<float>(s & 0xFFu) / 255.0f * 0.08f;
                hw[i] = std::min(1.0f, hw[i] + n);
            }
        }
    } else if (profile == "asteroid") {
        if (mode == "regolith") {
            std::uint32_t s = seed ? seed : 1u;
            for (std::size_t i = 0; i < kSensorElements; ++i) {
                s = s * 1664525u + 1013904223u;
                hw[i] = std::min(1.0f, hw[i] + static_cast<float>(s % 7u) * 0.02f);
            }
        } else if (mode == "craters") {
            const int cr[][2] = {{8, 9}, {18, 15}, {12, 20}};
            for (int k = 0; k < 3; ++k) {
                int cx = cr[k][0], cy = cr[k][1];
                for (int y = 0; y < kSensorH; ++y) {
                    for (int x = 0; x < kSensorW; ++x) {
                        float d = std::sqrt(float((x - cx) * (x - cx) + (y - cy) * (y - cy)));
                        if (d < 3.5f) {
                            hw[idx(y, x)] *= 0.45f;
                        }
                    }
                }
            }
        } else if (mode == "rotation" || mode == "rotation_curve") {
            for (int y = 0; y < kSensorH; ++y) {
                for (int x = 0; x < kSensorW; ++x) {
                    hw[idx(y, x)] *= 0.65f + 0.35f * (static_cast<float>(x) / static_cast<float>(kSensorW));
                }
            }
        } else if (mode == "binary_proxy" || mode == "binary") {
            for (int y = 0; y < kSensorH; ++y) {
                for (int x = 0; x < kSensorW; ++x) {
                    float d1 = std::sqrt(float((x - 10) * (x - 10) + (y - 14) * (y - 14)));
                    float d2 = std::sqrt(float((x - 18) * (x - 18) + (y - 14) * (y - 14)));
                    float& v = hw[idx(y, x)];
                    if (d1 < 4.0f || d2 < 3.5f) {
                        v = std::min(1.0f, v + 0.2f);
                    }
                }
            }
        }
    } else if (profile == "survey") {
        if (mode == "mosaic") {
            for (int y = 0; y < kSensorH; ++y) {
                for (int x = 0; x < kSensorW; ++x) {
                    float g = ((x < 14) ? 1.0f : 0.92f) * ((y < 14) ? 1.0f : 0.88f);
                    hw[idx(y, x)] *= g;
                }
            }
        } else if (mode == "strip_map" || mode == "strips") {
            for (int y = 0; y < kSensorH; ++y) {
                for (int x = 0; x < kSensorW; ++x) {
                    if (x % 6 < 2) {
                        hw[idx(y, x)] *= 1.12f;
                    }
                    clamp01(hw[idx(y, x)]);
                }
            }
        } else if (mode == "multi_band" || mode == "multiband") {
            for (int y = 0; y < kSensorH; ++y) {
                for (int x = 0; x < kSensorW; ++x) {
                    float& v = hw[idx(y, x)];
                    v += 0.05f * std::sin(x * 1.1f) * std::cos(y * 1.05f);
                    clamp01(v);
                }
            }
        }
    }
}
