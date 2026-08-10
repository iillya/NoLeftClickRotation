"""Code fragment for zbrush.commands.load_stroke.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# To make this example tangible, we are going to save a stroke string to disk and then load it. With
# the new Python API this is all a bit nonsensical as we could also easily load the file content into
# Stroke.__init__ ourself. So, we do not really need #load_stroke.
data: str = str(
    "(ZObjStrokeV03n27%p2377BA8p191C7ACPnA63An234Fn-BF76s100672Cs100672Cs100672Cz-7E6B=H231V219H230"
    "V216H22FV214h22E55v210AAH22Ev20C40h22D40v203C0H22Dv1F980H22DV1EEH22DV1E2h22D40v1D5C0h22DC0v1C9"
    "80h22E40v1BD40h22EC0v1B040H22Fv1A280H22Fv19380h22EC0v18480h22DC0v17640h22C40v16980h22A80v15F40"
    "h228C0v15740h227C0v15240h22740v14F40h226C0v14D80h22680v14C80h22640v14B80H226v14A80H226v149C0)")

# Save the stroke data.
file_path: str = r"line.txt"
with open(file_path, "w") as file:
    file.write(data)

# Now we can load the stroke data from the file and apply it.
loaded_stroke: zbc.Stroke = zbc.load_stroke(file_path)
zbc.canvas_stroke(loaded_stroke)