"""Code fragment for zbrush.commands.set_subtool_status.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# Select the last tool in the list of tools.
cnt: int = zbc.get_subtool_count()
zbc.select_tool(cnt - 1)

# Iterate over all sub-tools and make sure both the sub-tool and its folder visibility is enabled 
# and that all sub-tools are not marked as a volume start.
for i in range(zbc.get_subtool_count()):
    status: int = zbc.get_subtool_status(i)
    status |= 0x0001   # Ensure the eye icon is enabled.
    status |= 0x0002   # Ensure the folder icon is enabled.
    status &= ~0x0400  # Ensure the volume start is disabled.
    zbc.set_subtool_status(i, status)
