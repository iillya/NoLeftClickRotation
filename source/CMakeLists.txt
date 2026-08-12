cmake_minimum_required(VERSION 3.20)
project(NoLeftClickRotation2022 LANGUAGES CXX)

add_library(NoLeftClickRotation2022 SHARED NoLeftClickRotationZscript.cpp)
target_compile_features(NoLeftClickRotation2022 PRIVATE cxx_std_17)
target_compile_definitions(NoLeftClickRotation2022 PRIVATE
    UNICODE _UNICODE WIN32_LEAN_AND_MEAN NOMINMAX)
target_link_libraries(NoLeftClickRotation2022 PRIVATE comctl32 user32 winmm)
set_target_properties(NoLeftClickRotation2022 PROPERTIES
    OUTPUT_NAME "NoLeftClickRotation2022"
    PREFIX "")

