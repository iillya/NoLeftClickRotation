"""Code fragment for zbrush.commands.add_slider.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

def on_slider_change(sender: str, value: float) -> None:
    print(f"{sender}'s value changed to: {value}")

# Add a 'Foo' subpalette to the 'ZScript' palette if it doesn't exist.
if not zbc.exists("ZScript:Foo"):
    zbc.add_subpalette("ZScript:Foo")

# Adds a slider named 'MySlider' to 'ZScript:Foo' with a range from 0 to 100, the initial value of 
# 12, a step size of 1, and the callback function `on_slider_change`.
zbc.add_slider("ZScript:Foo:MySlider", 12, 1, 0, 100, "", on_slider_change)
