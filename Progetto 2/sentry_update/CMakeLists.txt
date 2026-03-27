cmake_minimum_required(VERSION 3.14)
project(SentrySat CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(OpenMP)
if(OpenMP_CXX_FOUND)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${OpenMP_CXX_FLAGS}")
endif()

# Vendored single-header JSON (third_party/nlohmann/json.hpp) — no FetchContent / git needed.
set(SENTRY_THIRD_PARTY "${CMAKE_SOURCE_DIR}/third_party")

include_directories(
    ${CMAKE_SOURCE_DIR}/src
    ${CMAKE_SOURCE_DIR}/../security_enclave/src
    ${SENTRY_THIRD_PARTY}
)

add_executable(sentry_sat_sim
    src/main.cpp
    src/memory_pool.cpp
    src/inference_engine.cpp
    ../security_enclave/src/puf_simulator.cpp
    ../security_enclave/src/crypto_signer.cpp
)

# ── TensorFlow Lite (optional) ────────────────────────────────────────────────
option(SENTRY_ENABLE_TFLITE "Link prebuilt TensorFlow Lite C++ API" OFF)
set(TFLITE_ROOT "" CACHE PATH "Install prefix with include/ and libtensorflow-lite (or .dylib)")

if(SENTRY_ENABLE_TFLITE)
    find_path(TFLITE_INCLUDE NAMES tensorflow/lite/model.h
              PATHS ${TFLITE_ROOT}/include REQUIRED)
    find_library(TFLITE_LIB NAMES tensorflow-lite
                 PATHS ${TFLITE_ROOT}/lib REQUIRED)
    find_package(Threads REQUIRED)
    target_include_directories(sentry_sat_sim PRIVATE ${TFLITE_INCLUDE})
    target_link_libraries(sentry_sat_sim PRIVATE ${TFLITE_LIB} Threads::Threads)
    target_compile_definitions(sentry_sat_sim PRIVATE SENTRY_HAVE_TFLITE=1)
    message(STATUS "TFLite enabled: ${TFLITE_LIB}")
else()
    message(STATUS "TFLite disabled (heuristic inference). "
                   "Build TFLite, then -DSENTRY_ENABLE_TFLITE=ON -DTFLITE_ROOT=...")
endif()

# ── OpenSSL (recommended) ─────────────────────────────────────────────────────
find_package(OpenSSL)
if(OpenSSL_FOUND)
    target_compile_definitions(sentry_sat_sim PRIVATE SENTRY_HAVE_OPENSSL=1)
    target_link_libraries(sentry_sat_sim PRIVATE OpenSSL::Crypto)
    message(STATUS "OpenSSL found: HMAC-SHA256 MAC enabled.")
else()
    message(STATUS "OpenSSL not found: telemetry MAC uses dummy_hash (dev only).")
endif()

# ── dummy MAC release-build override ─────────────────────────────────────────
# Set this to ON only in CI environments that legitimately lack OpenSSL.
# In all other cases the default (OFF) will cause the release build to fail with
# a clear error if OpenSSL is absent, preventing silent integrity regression.
option(SENTRY_ALLOW_DUMMY_MAC
       "Allow the dummy (non-cryptographic) MAC even in Release builds" OFF)
if(SENTRY_ALLOW_DUMMY_MAC)
    target_compile_definitions(sentry_sat_sim PRIVATE SENTRY_ALLOW_DUMMY_MAC=1)
    message(WARNING "SENTRY_ALLOW_DUMMY_MAC is ON — dummy MAC active, NOT for production.")
endif()

# ── Tests ─────────────────────────────────────────────────────────────────────
include(CTest)
enable_testing()

add_executable(obc_json_check ${CMAKE_SOURCE_DIR}/tests/json_self_test.cpp)
add_test(NAME obc_json_parse_self COMMAND obc_json_check)

add_test(NAME sentry_sat_sim_smoke COMMAND sentry_sat_sim)
set_tests_properties(sentry_sat_sim_smoke PROPERTIES
    WORKING_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}"
    TIMEOUT 30
)

find_package(Python3 COMPONENTS Interpreter)
if(Python3_Interpreter_FOUND)
    add_test(NAME sentry_telemetry_json_lines
        COMMAND ${Python3_EXECUTABLE}
                ${CMAKE_SOURCE_DIR}/tests/check_telemetry_json.py
                $<TARGET_FILE:sentry_sat_sim>
    )
    set_tests_properties(sentry_telemetry_json_lines PROPERTIES
        WORKING_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}"
        TIMEOUT 30
    )
endif()
