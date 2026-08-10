"""Code fragment for zbrush.commands.get_title.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

title: str = zbc.get_title("Transform:Move") # Will return 'Move'
print(f"The title of 'Transform:Move' is: '{title}'.")