"""Code fragment for zbrush.commands.canvas_strokes.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

strokes: zbc.Strokes = zbc.load_strokes(r"c:\\data\\strokes\\complex_stroke.txt")
zbc.canvas_strokes(strokes)
