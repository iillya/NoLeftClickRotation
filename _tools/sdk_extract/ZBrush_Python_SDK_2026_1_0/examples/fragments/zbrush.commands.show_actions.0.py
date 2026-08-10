"""Code fragment for zbrush.commands.show_actions.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# Disable action drawing in the UI. This can be useful to minimize flickering and speed up scripts 
# which perform many UI actions.
zbc.show_actions(0)

# Press a bunch of buttons in a loop.
for i in range(10):
    zbc.press("Transform:Move")
    zbc.press("Transform:Rotate")

# Enable showing scripted interface interactions again.
zbc.show_actions(1)
