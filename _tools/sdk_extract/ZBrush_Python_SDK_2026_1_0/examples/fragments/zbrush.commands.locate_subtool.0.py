"""Code fragment for zbrush.commands.locate_subtool.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

sid: int = zbc.get_subtool_id()
sindex: int = zbc.get_active_subtool_index()
print(f"Active sub-tool ID: {sid}")
print(f"Active sub-tool index: {sindex}")
print(f"{zbc.locate_subtool(sid) = }")
