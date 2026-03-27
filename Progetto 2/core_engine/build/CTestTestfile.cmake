# CMake generated Testfile for 
# Source directory: /Users/ashura/Desktop/Sentry-Sat/core_engine
# Build directory: /Users/ashura/Desktop/Sentry-Sat/core_engine/build
# 
# This file includes the relevant testing commands required for 
# testing this directory and lists subdirectories to be tested as well.
add_test(obc_json_parse_self "/Users/ashura/Desktop/Sentry-Sat/core_engine/build/obc_json_check")
set_tests_properties(obc_json_parse_self PROPERTIES  _BACKTRACE_TRIPLES "/Users/ashura/Desktop/Sentry-Sat/core_engine/CMakeLists.txt;74;add_test;/Users/ashura/Desktop/Sentry-Sat/core_engine/CMakeLists.txt;0;")
add_test(sentry_sat_sim_smoke "/Users/ashura/Desktop/Sentry-Sat/core_engine/build/sentry_sat_sim")
set_tests_properties(sentry_sat_sim_smoke PROPERTIES  TIMEOUT "30" WORKING_DIRECTORY "/Users/ashura/Desktop/Sentry-Sat/core_engine/build" _BACKTRACE_TRIPLES "/Users/ashura/Desktop/Sentry-Sat/core_engine/CMakeLists.txt;76;add_test;/Users/ashura/Desktop/Sentry-Sat/core_engine/CMakeLists.txt;0;")
add_test(sentry_telemetry_json_lines "/opt/anaconda3/bin/python3.13" "/Users/ashura/Desktop/Sentry-Sat/core_engine/tests/check_telemetry_json.py" "/Users/ashura/Desktop/Sentry-Sat/core_engine/build/sentry_sat_sim")
set_tests_properties(sentry_telemetry_json_lines PROPERTIES  TIMEOUT "30" WORKING_DIRECTORY "/Users/ashura/Desktop/Sentry-Sat/core_engine/build" _BACKTRACE_TRIPLES "/Users/ashura/Desktop/Sentry-Sat/core_engine/CMakeLists.txt;84;add_test;/Users/ashura/Desktop/Sentry-Sat/core_engine/CMakeLists.txt;0;")
