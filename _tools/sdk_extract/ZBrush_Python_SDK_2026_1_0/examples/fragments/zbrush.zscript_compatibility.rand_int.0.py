"""Code fragment for zbrush.zscript_compatibility.rand_int.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import zscript_compatibility as zbcomp

# Prints 10 random integers for the ranges [0, 1], [0, 100], and [0, 10000].
for i in range(10):
    print(f"{i}: {zbcomp.rand_int(1.0) = }")        # Will generate values in the interval [0, 1]
    print(f"{i}: {zbcomp.rand_int(100.0) = }")      # Will generate values in the interval [0, 100]
    print(f"{i}: {zbcomp.rand_int(10000.0) = }")    # Will generate values in the interval [0, 10000]