"""Code fragment for zbrush.commands.get_info.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

value: str = zbc.get_info("Transform:Move")
print(f"The bubble help text for 'Transform:Move' is: '{value}'.")
