cmake_minimum_required(VERSION 3.20)
project(NoLeftClickRotation LANGUAGES CXX)

add_library(NoLeftClickRotation SHARED NoLeftClickRotationZscript.cpp)
target_compile_features(NoLeftClickRotation PRIVATE cxx_std_17)
target_compile_definitions(NoLeftClickRotation PRIVATE
    UNICODE _UNICODE WIN32_LEAN_AND_MEAN NOMINMAX)
target_link_libraries(NoLeftClickRotation PRIVATE comctl32 user32 shell32)
set_target_properties(NoLeftClickRotation PROPERTIES
    OUTPUT_NAME "NoLeftClickRotation"
    PREFIX "")

