"""Code fragment for zbrush.commands.locate_subtool_by_name.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

sid: int = zbc.locate_subtool_by_name("PM3D_Gear3D1")
print(f"Active sub-tool ID: {sid}")
