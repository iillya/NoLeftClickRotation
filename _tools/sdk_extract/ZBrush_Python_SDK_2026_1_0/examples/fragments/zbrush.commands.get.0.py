"""Code fragment for zbrush.commands.get.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# A slider, #a will hold the current value of the slider.
a: float = zbc.get("Draw:Width")

# A toggle button, #b will hold the current value of the button where 0.0 means 
# off and 1.0 means on.
b: float = zbc.get("Tool:UV Map:Create (Unwrap):Auto Seams")

# Getting the value of a button and a subpalette. Neither of these has a value which 
# could be retrieved, but these calls will not raise an error, and instead just return 
# 0.0.
c: float = zbc.get("Tool:Displacement Map:Create DispMap")
d: float = zbc.get("Tool:Displacement Map")
