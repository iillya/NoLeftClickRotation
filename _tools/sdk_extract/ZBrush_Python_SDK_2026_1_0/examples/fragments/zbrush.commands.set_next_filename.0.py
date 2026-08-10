"""Code fragment for zbrush.commands.set_next_filename.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# Set the full path "d:\\temp\\foo.zbr" for the next load or save operation.
zbc.set_next_filename(r"d:\\temp\\foo.zbr")
# Only set the next file name.
zbc.set_next_filename("foo.zbr")
