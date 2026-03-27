# CMake generated Testfile for 
# Source directory: /Users/ashura/Desktop/Project/Sentry-Sat/core_engine
# Build directory: /Users/ashura/Desktop/Project/Sentry-Sat/core_engine/build2
# 
# This file includes the relevant testing commands required for 
# testing this directory and lists subdirectories to be tested as well.
add_test(obc_json_parse_self "/Users/ashura/Desktop/Project/Sentry-Sat/core_engine/build2/obc_json_check")
set_tests_properties(obc_json_parse_self PROPERTIES  _BACKTRACE_TRIPLES "/Users/ashura/Desktop/Project/Sentry-Sat/core_engine/CMakeLists.txt;56;add_test;/Users/ashura/Desktop/Project/Sentry-Sat/core_engine/CMakeLists.txt;0;")
add_test(sentry_sat_sim_smoke "/Users/ashura/Desktop/Project/Sentry-Sat/core_engine/build2/sentry_sat_sim")
set_tests_properties(sentry_sat_sim_smoke PROPERTIES  TIMEOUT "30" WORKING_DIRECTORY "/Users/ashura/Desktop/Project/Sentry-Sat/core_engine/build2" _BACKTRACE_TRIPLES "/Users/ashura/Desktop/Project/Sentry-Sat/core_engine/CMakeLists.txt;58;add_test;/Users/ashura/Desktop/Project/Sentry-Sat/core_engine/CMakeLists.txt;0;")
add_test(sentry_telemetry_json_lines "/opt/anaconda3/bin/python3.13" "/Users/ashura/Desktop/Project/Sentry-Sat/core_engine/tests/check_telemetry_json.py" "/Users/ashura/Desktop/Project/Sentry-Sat/core_engine/build2/sentry_sat_sim")
set_tests_properties(sentry_telemetry_json_lines PROPERTIES  TIMEOUT "30" WORKING_DIRECTORY "/Users/ashura/Desktop/Project/Sentry-Sat/core_engine/build2" _BACKTRACE_TRIPLES "/Users/ashura/Desktop/Project/Sentry-Sat/core_engine/CMakeLists.txt;66;add_test;/Users/ashura/Desktop/Project/Sentry-Sat/core_engine/CMakeLists.txt;0;")
