"""Code fragment for zbrush.commands.create_displacement_map.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# Create a 1024x1024 displacement map for the active tool at sub-division level 3.
zbc.create_displacement_map(1024, 1024, True, 3, 2)
