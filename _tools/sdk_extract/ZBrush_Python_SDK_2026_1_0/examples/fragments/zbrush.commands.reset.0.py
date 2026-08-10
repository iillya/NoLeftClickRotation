"""Code fragment for zbrush.commands.reset.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# Resets the interface, document, tools, lights, materials, and stencils to a default state
# associated with ZBrush 2026.
zbc.reset(0, 2026)
