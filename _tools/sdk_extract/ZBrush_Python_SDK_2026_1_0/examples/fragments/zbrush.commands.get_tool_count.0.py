"""Code fragment for zbrush.commands.get_tool_count.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# Iterate over all tool indices and print their paths; i.e., usually name as seen in the UI, unless
# the tool has been loaded from a file.
for i in range(zbc.get_tool_count()):
    print(f"{i}: {zbc.get_tool_path(i)}")
