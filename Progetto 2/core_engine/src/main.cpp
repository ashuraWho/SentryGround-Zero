// OBC simulator: 28×28 sensor tiles (aligned with Python training), JSON telemetry, signed downlink.
#include <iostream>
#include <string>

#include "memory_pool.h"
#include "inference_engine.h"
#include "puf_simulator.h"
#include "crypto_signer.h"
#include "sensor_frame.hpp"
#include "telemetry_json.hpp"

int main() {
    std::cout << "==========================================" << std::endl;
    std::cout << "Sentry-Sat OBC Simulator v1.0 Boot Sequence" << std::endl;
    std::cout << "==========================================" << std::endl;

    MemoryPool pool;
    PUFSimulator puf;
    CryptoSigner signer(puf);
    InferenceEngine ai_engine(pool);

    std::cout << "==========================================" << std::endl;
    std::cout << "STARTING MISSION LOOP" << std::endl;
    std::cout << "==========================================" << std::endl;

    // Cycle 1 — nominal 28×28 patch (~dark-field + read noise, no artifacts).
    std::cout << "\n--- [Cycle 1] Normal Sensor Frame (28×28) ---" << std::endl;
    pool.reset();
    // Pass alignof(float) explicitly so the allocator pads correctly on any target.
    float* frame1 = static_cast<float*>(
        pool.allocate(kSensorElements * sizeof(float), alignof(float)));
    if (!frame1) {
        std::cerr << "[FATAL] Could not allocate frame1 from MemoryPool." << std::endl;
        return 1;
    }
    fill_nominal_sensor_frame(frame1, 0xC0FFEEu);

    bool anomaly1 = ai_engine.run_inference(frame1, kSensorElements);
    std::string sig1 = signer.sign_payload(anomaly1, "T+001");
    std::cout << "[Telemetry] Anomaly: " << anomaly1
              << " Score: " << ai_engine.last_mse()
              << " (threshold: " << ai_engine.active_threshold() << ")"
              << " MAC: " << sig1 << std::endl;
    emit_cycle_json(std::cout, "T+001", anomaly1, sig1,
                    ai_engine.last_mse(), ai_engine.backend_name());

    // Cycle 2 — bright scan line (spoof / row defect) across the tile.
    std::cout << "\n--- [Cycle 2] Suspicious Sensor Frame (row stripe) ---" << std::endl;
    pool.reset();
    float* frame2 = static_cast<float*>(
        pool.allocate(kSensorElements * sizeof(float), alignof(float)));
    if (!frame2) {
        std::cerr << "[FATAL] Could not allocate frame2 from MemoryPool." << std::endl;
        return 1;
    }
    fill_anomaly_streak_frame(frame2, 0xBEEFu, 14);

    bool anomaly2 = ai_engine.run_inference(frame2, kSensorElements);
    std::string sig2 = signer.sign_payload(anomaly2, "T+002");
    std::cout << "[Telemetry] Anomaly: " << anomaly2
              << " Score: " << ai_engine.last_mse()
              << " (threshold: " << ai_engine.active_threshold() << ")"
              << " MAC: " << sig2 << std::endl;
    emit_cycle_json(std::cout, "T+002", anomaly2, sig2,
                    ai_engine.last_mse(), ai_engine.backend_name());

    std::cout << "\n==========================================" << std::endl;
    std::cout << "SYSTEM SHUTDOWN" << std::endl;
    std::cout << "==========================================" << std::endl;
    return 0;
}
