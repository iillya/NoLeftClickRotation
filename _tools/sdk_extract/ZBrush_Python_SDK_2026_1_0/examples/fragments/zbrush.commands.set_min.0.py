"""Code fragment for zbrush.commands.set_min.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

def on_change(sender: str, value: float) -> None:
    print(f"Slider changed: {sender} to {value}")

# Make sure there is no existing "ZScript:Foo" palette.
if zbc.exists("ZScript:Foo"):
    zbc.close("ZScript:Foo")

# Create a new palette with a slider with the current value of 50, and a min of 0 and max of 100. 
# Then sets the new min value to 10.
zbc.add_subpalette("ZScript:Foo")
zbc.add_slider("ZScript:Foo:A", 50, 1, 0, 100, "", on_change, width=1.0)
zbc.set_min("ZScript:Foo:A", 10)
