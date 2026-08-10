"""Code fragment for zbrush.commands.is_locked.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

is_locked: bool = zbc.is_locked("Transform:Move")
print(f"'Transform:Move' is locked: {is_locked}")
