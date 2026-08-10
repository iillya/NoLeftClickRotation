"""Code fragment for zbrush.commands.get_subtool_id.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

print(f"The unique ID for the active sub-tool in the active tool is {zbc.get_subtool_id()}.")