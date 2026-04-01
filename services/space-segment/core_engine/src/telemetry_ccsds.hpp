#pragma once

#include <iostream>
#include <nlohmann/json.hpp>
#include <string>
#include <cstdint>
#include <chrono>
#include <iomanip>

// Emits a CCSDS Space Packet enclosing the JSON telemetry payload.
inline void emit_ccsds_packet(std::ostream& os,
                              const std::string& cycle_id,
                              bool anomaly_flag,
                              const std::string& signature_hex,
                              float mse_score,
                              const std::string& inference_backend,
                              double orbital_alt_km = 0.0,
                              double orbital_vel_km_s = 0.0,
                              double orbital_period_min = 0.0,
                              const std::string& orbital_regime = "UNKNOWN") {
    nlohmann::json j;
    j["telemetry_schema"] = "sentry_sat.obc.v3.ccsds";
    j["cycle_id"] = cycle_id;
    j["anomaly"] = anomaly_flag;
    j["signature_hex"] = signature_hex;
    j["reconstruction_mse"] = mse_score;
    j["inference_backend"] = inference_backend;
    
    // Orbital state (v3 extension)
    j["orbital_state"] = {
        {"regime", orbital_regime},
        {"altitude_km", orbital_alt_km},
        {"velocity_km_s", orbital_vel_km_s},
        {"period_min", orbital_period_min}
    };
    
    // Timestamp UTC
    auto now = std::chrono::system_clock::now();
    auto time_t = std::chrono::system_clock::to_time_t(now);
    std::ostringstream ts;
    ts << std::put_time(std::gmtime(&time_t), "%Y-%m-%dT%H:%M:%SZ");
    j["timestamp_utc"] = ts.str();
    
    std::string payload = j.dump();
    
    // Sync Marker: 1A CF FC 1D
    uint8_t header[10];
    header[0] = 0x1A; header[1] = 0xCF; header[2] = 0xFC; header[3] = 0x1D;
    
    // Packet ID: Version 0, Type 0, SecHdr 1, APID 42 (0000 1000 0010 1010 = 0x082A)
    header[4] = 0x08; header[5] = 0x2A;
    // Seq Ctrl: Unsegmented (11), Count 0
    header[6] = 0xC0; header[7] = 0x00;
    
    // Length: payload.size() - 1
    // CCSDS Length is (actual length - 1)
    uint16_t ccsds_len = payload.size() - 1;
    header[8] = (ccsds_len >> 8) & 0xFF;
    header[9] = ccsds_len & 0xFF;
    
    // Write binary packet
    os.write(reinterpret_cast<const char*>(header), 10);
    os.write(payload.data(), payload.size());
    os.flush();
}
