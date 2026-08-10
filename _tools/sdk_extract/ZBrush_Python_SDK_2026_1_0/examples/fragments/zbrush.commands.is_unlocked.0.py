"""Code fragment for zbrush.commands.is_unlocked.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

is_unlocked: bool = zbc.is_unlocked("Transform:Move")
print(f"'Transform:Move' is unlocked: {is_unlocked}")
