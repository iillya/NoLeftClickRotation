"""Code fragment for zbrush.commands.set_tool_path.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# Set the name of the active tool to "Bar"
tid: int = zbc.get_active_tool_index()
zbc.set_tool_path(tid, "Bar")

# Set the path of the active tool to "d:\\temp\\foo.ztl". The tool will be displayed as "foo".
zbc.set_tool_path(tid, r"d:\\temp\\foo.ztl")
print(zbc.press("Tool:Save"))

# After setting a tool name we should update the UI.
zbc.update(redraw_ui=True)
