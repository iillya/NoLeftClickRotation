"""Code fragment for zbrush.commands.get_active_subtool_index.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

index: int = zbc.get_active_subtool_index()
print(f"Active sub-tool index: {index}")
