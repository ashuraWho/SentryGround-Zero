// OBC simulator: 28×28 sensor tiles (aligned with Python training), JSON telemetry, signed downlink.
#include <cctype>
#include <iostream>
#include <string>
#include <cmath>
#include <array>

#include "memory_pool.h"
#include "inference_engine.h"
#include "puf_simulator.h"
#include "crypto_signer.h"
#include "sensor_frame.hpp"
#include "sensor_observation.hpp"
#include "telemetry_ccsds.hpp"

namespace {

const double GM_EARTH = 3.986004418e14;
const double R_EARTH = 6.378137e6;

struct OrbitalState {
    double altitude_km;
    double velocity_km_s;
    double period_min;
    std::string regime;
};

std::string normalize_profile(const char* env_profile) {
    std::string p = env_profile ? std::string(env_profile) : "dark_matter";
    for (char& c : p) {
        c = static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    }
    return p;
}

OrbitalState compute_orbital_state(double semimajor_km, double eccentricity) {
    OrbitalState state;
    state.altitude_km = semimajor_km - R_EARTH / 1000.0;
    
    // Vis-viva: v = sqrt(GM * (2/r - 1/a))
    double r_km = state.altitude_km + R_EARTH / 1000.0;
    double v_m_s = std::sqrt(GM_EARTH * (2.0 / (r_km * 1000.0) - 1.0 / (semimajor_km * 1000.0)));
    state.velocity_km_s = v_m_s / 1000.0;
    
    // Period: T = 2*pi*sqrt(a³/GM)
    double T_s = 2.0 * M_PI * std::sqrt(std::pow(semimajor_km * 1000.0, 3.0) / GM_EARTH);
    state.period_min = T_s / 60.0;
    
    if (state.altitude_km < 2000.0) state.regime = "LEO";
    else if (state.altitude_km < 35786.0) state.regime = "MEO";
    else if (state.altitude_km < 40000.0) state.regime = "GEO";
    else state.regime = "HEO";
    
    return state;
}

// Mission profile to approximate orbital elements
std::array<double, 2> profile_to_orbital_elements(const std::string& profile) {
    // Returns {semimajor_axis_km, eccentricity}
    if (profile == "earth_observation" || profile == "earth" || profile == "earth_climate") {
        return {7078.0, 0.0001};  // ~700km SSO
    } else if (profile == "stellar" || profile == "deep_space") {
        return {6913.0, 0.0003};  // HST-like ~540km
    } else if (profile == "black_hole" || profile == "exoplanet") {
        return {42164.0, 0.0001};  // GEO-like
    } else if (profile == "gravitational_wave") {
        return {7000.0, 0.001};  // LEO science
    } else if (profile == "asteroid") {
        return {6800.0, 0.001};  // LEO
    } else if (profile == "survey") {
        return {7078.0, 0.0001};  // SSO
    } else {
        return {7078.0, 0.0001};  // Default LEO
    }
}

// Dispatch synthetic 28×28 acquisition to the correct science template + instrument mode.
void fill_mission_frame(const std::string& profile, const std::string& obs_mode, float* frame,
                        std::uint32_t seed) {
    if (profile == "exoplanet") {
        fill_exoplanet_frame(frame, seed);
    } else if (profile == "earth" || profile == "earth_observation") {
        fill_earth_frame(frame, seed);
    } else if (profile == "earth_climate") {
        fill_earth_climate_frame(frame, seed);
    } else if (profile == "deep_space") {
        fill_deep_space_frame(frame, seed);
    } else if (profile == "stellar") {
        fill_stellar_frame(frame, seed);
    } else if (profile == "black_hole") {
        fill_black_hole_frame(frame, seed);
    } else if (profile == "gravitational_wave") {
        fill_gravitational_wave_frame(frame, seed);
    } else if (profile == "asteroid") {
        fill_asteroid_frame(frame, seed);
    } else if (profile == "survey") {
        fill_survey_frame(frame, seed);
    } else {
        fill_nfw_halo_frame(frame, seed);
    }
    apply_observation_modulation(profile, obs_mode, frame, seed);
}

}  // namespace

int main() {
    const std::string profile = normalize_profile(std::getenv("MISSION_PROFILE"));
    const std::string obs_mode = normalize_observation_mode(std::getenv("OBSERVATION_MODE"));

    std::cout << "==========================================" << std::endl;
    std::cout << "Sentry-Sat OBC: Distributed Constellation Swarm v4.0" << std::endl;
    std::cout << "Active Mission Profile: [" << profile << "]" << std::endl;
    std::cout << "Observation / Instrument Mode: [" << obs_mode << "]" << std::endl;
    std::cout << "==========================================" << std::endl;

    MemoryPool pool;
    PUFSimulator puf;
    CryptoSigner signer(puf);
    InferenceEngine ai_engine(pool);

    std::cout << "==========================================" << std::endl;
    std::cout << "STARTING MISSION LOOP" << std::endl;
    std::cout << "==========================================" << std::endl;

    // Compute orbital state based on mission profile
    auto orb_elements = profile_to_orbital_elements(profile);
    OrbitalState orb = compute_orbital_state(orb_elements[0], orb_elements[1]);
    std::cout << "[Orbital] Regime: " << orb.regime 
              << " | Altitude: " << orb.altitude_km << " km"
              << " | Velocity: " << orb.velocity_km_s << " km/s"
              << " | Period: " << orb.period_min << " min" << std::endl;

    // Cycle 1 — nominal frame based on Mission Profile.
    std::cout << "\n--- [Cycle 1] Nominal Acquisition: " << profile << " ---" << std::endl;
    pool.reset();
    // Pass alignof(float) explicitly so the allocator pads correctly on any target.
    float* frame1 = static_cast<float*>(
        pool.allocate(kSensorElements * sizeof(float), alignof(float)));
    if (!frame1) {
        std::cerr << "[FATAL] Could not allocate frame1 from MemoryPool." << std::endl;
        return 1;
    }
    
    fill_mission_frame(profile, obs_mode, frame1, 0xC0FFEEu);

    bool anomaly1 = ai_engine.run_inference(frame1, kSensorElements);
    std::string sig1 = signer.sign_payload(anomaly1, "T+001");
    std::cout << "[Telemetry] Anomaly: " << anomaly1
              << " Score: " << ai_engine.last_mse()
              << " (threshold: " << ai_engine.active_threshold() << ")"
              << " MAC: " << sig1 << std::endl;
    
    emit_ccsds_packet(std::cout, "T+001", anomaly1, sig1,
                      ai_engine.last_mse(), ai_engine.backend_name(),
                      orb.altitude_km, orb.velocity_km_s, orb.period_min, orb.regime);

    // Cycle 2 — deep space cosmic ray hit over the nominal profile
    std::cout << "\n--- [Cycle 2] Anomaly: Cosmic Ray Hit Detection ---" << std::endl;
    pool.reset();
    float* frame2 = static_cast<float*>(
        pool.allocate(kSensorElements * sizeof(float), alignof(float)));
    if (!frame2) {
        std::cerr << "[FATAL] Could not allocate frame2 from MemoryPool." << std::endl;
        return 1;
    }
    
    fill_mission_frame(profile, obs_mode, frame2, 0xBEEFu);
    apply_cosmic_ray_hit(frame2);

    bool anomaly2 = ai_engine.run_inference(frame2, kSensorElements);
    std::string sig2 = signer.sign_payload(anomaly2, "T+002");
    std::cout << "[Telemetry] Anomaly: " << anomaly2
              << " Score: " << ai_engine.last_mse()
              << " (threshold: " << ai_engine.active_threshold() << ")"
              << " MAC: " << sig2 << std::endl;
    
    emit_ccsds_packet(std::cout, "T+002", anomaly2, sig2,
                      ai_engine.last_mse(), ai_engine.backend_name(),
                      orb.altitude_km, orb.velocity_km_s, orb.period_min, orb.regime);

    std::cout << "\n==========================================" << std::endl;
    std::cout << "SYSTEM SHUTDOWN" << std::endl;
    std::cout << "==========================================" << std::endl;
    return 0;
}
