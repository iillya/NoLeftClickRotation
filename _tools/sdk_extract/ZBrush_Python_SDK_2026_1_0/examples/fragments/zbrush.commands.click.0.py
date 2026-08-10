"""Code fragment for zbrush.commands.click.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# Emulates a click on the intentisty slider of the Light palette at position (50, 10).
zbc.click("Light:Intensity", 50, 10)