"""Code fragment for zbrush.commands.rgb.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

dark_blue: int = zbc.rgb(20, 40, 80) # A dark blue color.
zbc.show_note("Hello World!", bg_color=dark_blue) # Use the color to display a note.
