"""Code fragment for zbrush.commands.has_next_filename.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

if zbc.has_next_filename():
   filename = zbc.get_next_filename()
