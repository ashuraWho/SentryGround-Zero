// One-line JSON mission telemetry for ground pipelines (jq / ELK / tests).
#pragma once

#include <iostream>
#include <nlohmann/json.hpp>
#include <string>

inline void emit_cycle_json(std::ostream& os,
                            const std::string& cycle_id,
                            bool anomaly_flag,
                            const std::string& signature_hex,
                            float mse_score,
                            const std::string& inference_backend) {
    nlohmann::json j;
    j["telemetry_schema"] = "sentry_sat.obc.v1";
    j["cycle_id"] = cycle_id;
    j["anomaly"] = anomaly_flag;
    j["signature_hex"] = signature_hex;
    j["reconstruction_mse"] = mse_score;
    j["inference_backend"] = inference_backend;
    os << "[json] " << j.dump() << std::endl;
}
