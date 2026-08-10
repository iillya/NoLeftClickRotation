"""Code fragment for zbrush.zscript_compatibility.rand.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import zscript_compatibility as zbcomp

# Prints 10 random floats for the ranges [0.0, 1.0], [0.0, 100.0], and [0.0, 10000.0].
for i in range(10):
    print(f"{i}: {zbcomp.rand(1.0) = }")        # Will generate values in the interval [0.0, 1.0]
    print(f"{i}: {zbcomp.rand(100.0) = }")      # Will generate values in the interval [0.0, 100.0]
    print(f"{i}: {zbcomp.rand(10000.0) = }")    # Will generate values in the interval [0.0, 10000.0]