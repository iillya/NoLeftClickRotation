"""Code fragment for zbrush.commands.select_tool.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# Select the last tool in the list of tools.
cnt: int = zbc.get_tool_count()
zbc.select_tool(cnt - 1)

# Calling #select_tool does exactly the same as this #set call, we simply set here the interface
# element which selects the active tool.
zbc.set("Tool:Item Info", cnt - 1)

# In general, selecting tools is often done via #press as we often want to select a tool by name 
# and not by index. We can also select a tool by name via the dedicated tool API but it is more 
# code and also (slightly) slower.

# Complicated (but more formal) approach to selecting a tool by name.
for i in range(zbc.get_tool_count()):
    name: str = zbc.get_tool_path(i)
    if name == "Sphere3D":
        zbc.select_tool(i)
        break
else:
    print("Tool not found!")

# The easier way. Each tool has a unique item path in the form "Tool:{NAME}".
item_path: str = f"Tool:Sphere3D"
if zbc.exists(item_path):
    zbc.press(item_path)
else:
    print("Tool not found!")
