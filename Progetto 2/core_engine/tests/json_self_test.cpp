#include <nlohmann/json.hpp>
#include <string>

int main() {
    const auto j = nlohmann::json::parse(R"({"telemetry_schema":"sentry_sat.obc.v1"})");
    return j.at("telemetry_schema").get<std::string>() == "sentry_sat.obc.v1" ? 0 : 1;
}
