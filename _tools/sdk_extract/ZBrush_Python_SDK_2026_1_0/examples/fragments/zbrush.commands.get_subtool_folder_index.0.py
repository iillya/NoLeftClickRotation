"""Code fragment for zbrush.commands.get_subtool_folder_index.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

print(f"The active sub-tool is in a folder with the index {zbc.get_subtool_folder_index()}, named "
      f"'{zbc.get_subtool_folder_name()}'.")