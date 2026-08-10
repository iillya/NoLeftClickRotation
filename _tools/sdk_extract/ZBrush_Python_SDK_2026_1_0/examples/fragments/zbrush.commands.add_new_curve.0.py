"""Code fragment for zbrush.commands.add_new_curve.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# Adds a new curve in the current curves list.
cid: int = zbc.add_new_curve()
if not cid:
    raise RuntimeError("Failed to add a new curve.")

# Adds a new point to the newly created curve.
zbc.add_curve_point(cid, x=0, y=0, z=0)