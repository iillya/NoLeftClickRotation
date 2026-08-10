"""Code fragment for zbrush.commands.select_subtool.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# Select the first sub-tool of the active tool. A tool will always have at least one 
# sub-tool.
zbc.select_subtool(0)

# Select the last sub-tool in the active tool.
cnt: int = zbc.get_subtool_count()
zbc.select_subtool(cnt - 1)
