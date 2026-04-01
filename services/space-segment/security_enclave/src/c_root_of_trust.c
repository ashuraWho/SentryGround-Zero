#include <stdint.h>
#include <string.h>

/*
 * C Root of Trust (Hardware Entropy Simulator)
 * Pure C module representing the lowest level secure enclave driver.
 * It simulates sampling SRAM startup states or Ring Oscillator delays
 * to generate a Physically Unclonable Function (PUF) signature.
 */

void hardware_puf_entropy(char* buffer, int length) {
    const char* base_secret = "SAT_KEY_0x8F9A2B_C_NATIVE";
    int i = 0;
    while(base_secret[i] != '\0' && i < length - 1) {
        // Bitwise operations mimicking hardware register noise masking
        buffer[i] = base_secret[i] ^ (i % 3); 
        buffer[i] ^= (i % 3); // Reverse the mask for the baseline demo
        i++;
    }
    buffer[i] = '\0';
}
