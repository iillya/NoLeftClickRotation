"""Code fragment for zbrush.commands.get_max.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

value: str = zbc.get_max("Draw:Draw Size")
print(f"The maximum value for 'Draw:Draw Size' is: {value}.")