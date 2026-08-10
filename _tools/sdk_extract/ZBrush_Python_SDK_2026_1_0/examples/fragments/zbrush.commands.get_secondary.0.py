"""Code fragment for zbrush.commands.get_secondary.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

x: float = zbc.get("Light:Light Placement")
y: float = zbc.get_secondary("Light:Light Placement")
print(f"Light position: ({x}, {y})")