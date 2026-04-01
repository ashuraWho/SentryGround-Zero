// Include the class interface for methods defined in this translation unit.
#include "puf_simulator.h"
// Operator logs to stdout to mimic secure-world boot traces.
#include <iostream>

extern "C" {
    void hardware_puf_entropy(char* buffer, int length);
}

// Simulate manufacturing-time provisioning of a device-unique string.
PUFSimulator::PUFSimulator() {
    // Emit a TrustZone-flavored banner for narrative consistency in demos.
    std::cout << "[TrustZone] Activating Physical Unclonable Function (PUF) via Native C Module..." << std::endl;
    // Call the pure C module explicitly to generate hardware-level entropy
    char buffer[64];
    hardware_puf_entropy(buffer, sizeof(buffer));
    internal_key = std::string(buffer);
    // Confirm provisioning step for integration testing log scraping.
    std::cout << "[TrustZone] Device Root Key provisioned via Native C PUF." << std::endl;
}

// Return the simulated key bits to crypto modules needing an identity string.
std::string PUFSimulator::get_device_key() const {
    // Const method: copy elision may apply when returning by value from SSO buffer.
    return internal_key;
}
