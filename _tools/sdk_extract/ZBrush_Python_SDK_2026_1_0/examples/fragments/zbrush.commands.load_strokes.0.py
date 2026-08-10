"""Code fragment for zbrush.commands.load_strokes.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

loaded_stroke: zbc.Stroke = zbc.load_stroke(r"c:\\data\\strokes\\my_stroke_collection.txt")
zbc.canvas_stroke(loaded_stroke)
