"""Code fragment for zbrush.commands.get_subtool_count.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

print(f"The '{zbc.get_active_tool_path()}' tool has {zbc.get_subtool_count()} sub-tools.")
