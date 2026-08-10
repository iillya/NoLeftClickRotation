"""Code fragment for zbrush.commands.get_flags.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

flags: int = zbc.get_flags("Light:Light Placement")
