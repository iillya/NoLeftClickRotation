"""Code fragment for zbrush.commands.is_enabled.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

is_enabled: bool = zbc.is_enabled("Transform:Move")
print(f"'Transform:Move' is enabled: {is_enabled}")
