"""Code fragment for zbrush.commands.create_mesh_from_curves.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# Creates a mesh from the current curves.
zbc.create_mesh_from_curves("/data/test.obj", 0, 10.0)
