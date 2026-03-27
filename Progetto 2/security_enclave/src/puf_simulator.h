// Prevent duplicate definitions if header included more than once per TU.
#ifndef PUF_SIMULATOR_H
// Mark this header as included for the preprocessor.
#define PUF_SIMULATOR_H

// std::string is the carrier type for textual key material in this simulation.
#include <string>

// Software model of a silicon Physical Unclonable Function output channel.
class PUFSimulator {
public:
  // Constructor seeds or loads a faux root secret representing device identity.
  PUFSimulator();
  // Read-only accessor returning a hex-ish key handle for signing helpers.
  std::string get_device_key() const;

private:
  // Holds synthetic entropy pretending to originate from SRAM startup
  // variation.
  std::string internal_key;
};

// Terminate include guard cleanly.
#endif
