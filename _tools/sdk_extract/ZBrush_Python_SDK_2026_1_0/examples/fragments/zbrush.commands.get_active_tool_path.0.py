"""Code fragment for zbrush.commands.get_active_tool_path.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

path: str = zbc.get_active_tool_path()
print(f"Active tool path: {path}")