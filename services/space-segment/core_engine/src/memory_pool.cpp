// Include declaration of MemoryPool methods implemented in this TU.
#include "memory_pool.h"
// Use stderr for fatal allocator messages that should not be silently dropped.
#include <iostream>
// bit_cast / uintptr_t for alignment arithmetic.
#include <cstdint>

// Initialize offset to head of buffer indicating no bytes consumed yet.
MemoryPool::MemoryPool() : offset(0) {
    // Intentionally minimal: static storage needs no dynamic initialization.
}

// Bump-allocate `size` bytes with pointer aligned to `align` bytes.
//
// Alignment algorithm:
//   1. Compute the raw address of the next candidate byte: &buffer[offset].
//   2. Calculate the padding needed to advance that address to the next multiple
//      of `align` using the standard ((-addr) & (align-1)) trick, which is
//      valid only when align is a power of two (asserted below).
//   3. Advance offset by padding + size; check total fits in POOL_SIZE.
//
// This matches the behaviour of std::align() but avoids pulling in <memory>
// and keeps the logic visible for embedded audits.
void* MemoryPool::allocate(size_t size, size_t align) {
    // Alignment must be a non-zero power of two; enforce at runtime for safety.
    if (align == 0 || (align & (align - 1)) != 0) {
        std::cerr << "[OBC-FATAL] allocate() called with non-power-of-two alignment: "
                  << align << std::endl;
        return nullptr;
    }

    // Compute raw address of next free byte.
    const uintptr_t raw_addr = reinterpret_cast<uintptr_t>(&buffer[offset]);

    // Number of padding bytes needed to reach the next aligned address.
    // ((-raw_addr) & (align-1)) is the canonical branchless formula.
    const size_t padding = static_cast<size_t>((-raw_addr) & (align - 1u));

    // Total bytes consumed: padding to align + actual requested size.
    const size_t total = padding + size;

    // Check for overflow of bump pointer past static capacity.
    if (offset + total > POOL_SIZE) {
        std::cerr << "[OBC-FATAL] Out of On-Board Memory! "
                  << "Requested " << size << " bytes (+" << padding << " align pad), "
                  << "used " << offset << "/" << POOL_SIZE << " bytes." << std::endl;
        return nullptr;
    }

    // Advance past padding to the aligned start of this allocation.
    void* ptr = &buffer[offset + padding];
    offset += total;
    return ptr;
}

// No-op release: linear strategy cannot recycle interior regions.
void MemoryPool::deallocate(void* /*ptr*/) {
    // Documented limitation: pointer ignored until free-list or slab tiers exist.
    // Suppressed unused-parameter warning by naming the arg with a comment.
}

// Rewind cursor to recycle the entire arena cheaply between mission cycles.
void MemoryPool::reset() {
    // Setting offset to zero makes next allocate start from buffer base again.
    offset = 0;
}

// Simple introspection helper for tests or telemetry about allocator pressure.
size_t MemoryPool::get_used_memory() const {
    // Expose current high-water offset as "used" byte count approximation.
    // Note: includes alignment padding consumed internally, so the number may
    // be slightly larger than the sum of individual requested sizes.
    return offset;
}
