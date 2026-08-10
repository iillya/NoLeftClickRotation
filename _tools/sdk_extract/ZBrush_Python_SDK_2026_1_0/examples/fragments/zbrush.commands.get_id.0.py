"""Code fragment for zbrush.commands.get_id.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

value: str = zbc.get_id("Transform:Move")
print(f"ID for 'Transform:Move' is '{value}'.")
