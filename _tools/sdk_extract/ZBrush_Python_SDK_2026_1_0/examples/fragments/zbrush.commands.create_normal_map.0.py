"""Code fragment for zbrush.commands.create_normal_map.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# Creates a normal map for the active tool with a size of 1024x1024.
zbc.create_normal_map(1024, 1024, True, 3, 2)
