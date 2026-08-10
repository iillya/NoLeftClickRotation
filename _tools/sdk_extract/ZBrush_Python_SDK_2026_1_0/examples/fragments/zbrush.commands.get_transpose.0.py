"""Code fragment for zbrush.commands.get_transpose.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# Print the values of the active tranpose line.
line: list[float] = zbc.get_transpose()
print("Origin:", line[0:3])
print("Direction:", line[3:6])
print("Length:", line[6])
print("Red Axis:", line[7:10])
print("Green Axis:", line[10:13])
print("Blue Axis:", line[13:16])