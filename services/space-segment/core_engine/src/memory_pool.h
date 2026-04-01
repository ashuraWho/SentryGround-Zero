// Prevent duplicate definitions if header included more than once per TU.
#ifndef MEMORY_POOL_H
// Macro token used to skip reprocessing if already defined.
#define MEMORY_POOL_H

// size_t lives in cstddef for portable unsigned memory-related integer typing.
#include <cstddef>
// Fixed-width 8-bit integer type backs the raw backing store bytes.
#include <cstdint>
// std::uintptr_t needed for alignment arithmetic in allocate().
#include <cstdint>

// Model a deterministic, size-bounded SRAM arena without malloc/free churn.
// Runtime dynamic allocation is avoided except this one static slab.
//
// ALIGNMENT NOTE: allocate() aligns every returned pointer to `kDefaultAlign`
// bytes. On most Cortex-M / RISC-V targets unaligned float access is either
// undefined behaviour or a bus fault; aligning to 8 bytes (double-word) covers
// all scalar primitives used in this project (float, double, int32, int64).

class MemoryPool {
public:
    // Total byte capacity reserved at compile time (5 MiB illustrative).
    static constexpr size_t POOL_SIZE = 1024 * 1024 * 5; // 5 MB Space-Grade SRAM

    // Default alignment: 8 bytes covers float32, float64, and all integer types
    // typically used in sensor/telemetry buffers without wasting significant space.
    static constexpr size_t kDefaultAlign = 8;

    // Construct pool and zero-initialize logical cursor state.
    MemoryPool();
    // Defaulted destructor: no heap ownership, backing array has static storage duration.
    ~MemoryPool() = default;

    // Attempt bump allocation of `size` bytes from the front of the free tail.
    // The returned pointer is guaranteed to be aligned to `align` bytes.
    // Returns nullptr if the request cannot be satisfied (OOM or alignment padding
    // would overflow POOL_SIZE).
    void* allocate(size_t size, size_t align = kDefaultAlign);

    // Placeholder deallocation API (linear allocator cannot free mid-buffer blocks).
    // Retained for API symmetry; calling it has no effect.
    void deallocate(void* ptr);

    // Report high-water mark / current offset for diagnostics or assertions.
    size_t get_used_memory() const;
    // Reset write cursor to zero to reuse the entire pool for the next frame cycle.
    void reset(); // Reset the linear allocator per telemetry cycle

private:
    // Byte buffer representing on-chip SRAM backing store for all allocations.
    // alignas(kDefaultAlign) ensures the buffer itself starts at an aligned address
    // so that the alignment arithmetic inside allocate() is correct.
    alignas(kDefaultAlign) uint8_t buffer[POOL_SIZE];
    // Monotonic offset pointing one past the last allocated byte (bump pointer).
    size_t offset;
};

// End include guard to cooperate with other headers in the TU.
#endif
