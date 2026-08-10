"""Code fragment for zbrush.commands.Stroke.__init__.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# Instantiate a stroke from its string representation. String representations can be generated with
# the Python script recording feature of ZBrush.
stroke: zbc.Stroke = zbc.Stroke(
    "(ZObjStrokeV03n27%p2377BA8p191C7ACPnA63An234Fn-BF76s100672Cs100672Cs100672Cz-7E6B=H231V219H230"
    "V216H22FV214h22E55v210AAH22Ev20C40h22D40v203C0H22Dv1F980H22DV1EEH22DV1E2h22D40v1D5C0h22DC0v1C9"
    "80h22E40v1BD40h22EC0v1B040H22Fv1A280H22Fv19380h22EC0v18480h22DC0v17640h22C40v16980h22A80v15F40"
    "h228C0v15740h227C0v15240h22740v14F40h226C0v14D80h22680v14C80h22640v14B80H226v14A80H226v149C0)")

# Apply the stroke to the canvas.
zbc.canvas_stroke(stroke)