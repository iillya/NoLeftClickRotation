"""Code fragment for zbrush.commands.get_width.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

light_place: str = "Light:Light Placement"
light_amb: str = "Light:Ambient"
print(f"Width of '{light_place}' is {zbc.get_width(light_place)} pixels.")
print(f"Width of '{light_amb}' is {zbc.get_width(light_amb)} pixels.")
