"""Code fragment for zbrush.commands.get_min.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

value: str = zbc.get_min("Draw:Draw Size")
print(f"The minimum value for 'Draw:Draw Size' is: {value}.")   