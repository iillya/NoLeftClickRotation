"""Code fragment for zbrush.commands.is_disabled.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

is_disabled: bool = zbc.is_disabled("Transform:Move")
print(f"'Transform:Move' is disabled: {is_disabled}")
