// Include the class interface for methods defined in this translation unit.
#include "puf_simulator.h"
// Operator logs to stdout to mimic secure-world boot traces.
#include <iostream>

// Simulate manufacturing-time provisioning of a device-unique string.
PUFSimulator::PUFSimulator() {
    // Emit a TrustZone-flavored banner for narrative consistency in demos.
    std::cout << "[TrustZone] Activating Physical Unclonable Function (PUF)..." << std::endl;
    // Commentary: real hardware would measure oscillator races / SRAM start patterns.
    // Assign a deterministic placeholder secret rather than reading registers.
    internal_key = "SAT_KEY_0x8F9A2B";
    // Confirm provisioning step for integration testing log scraping.
    std::cout << "[TrustZone] Device Root Key provisioned via PUF." << std::endl;
}

// Return the simulated key bits to crypto modules needing an identity string.
std::string PUFSimulator::get_device_key() const {
    // Const method: copy elision may apply when returning by value from SSO buffer.
    return internal_key;
}
