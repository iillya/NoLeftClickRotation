"""Code fragment for zbrush.commands.add_subpalette.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# A callback function that fits different callback function signatures (by using *args and **kwargs).
# We use this because buttons, sliders, and switches have different callback signatures.
def on_change(*args, **kwargs) -> None:
    print("on_change", args, kwargs)

# Adds a new palette named "Palette" to the ZBrush interface which will auto doc to the right.
zbc.add_palette("Palette", docking_bar=1)

# Adds a subpalette named "Subpalette" to the "Palette" palette which has no title bar and is
# always open.
zbc.add_subpalette("Palette:Subpalette", title_mode=2)

# Adds two buttons to the "Subpalette" subpalette.
zbc.add_button(f"Palette:Subpalette:Button A", "", on_change)
zbc.add_button(f"Palette:Subpalette:Button B", "", on_change)

# Adds a subpalette named "Subpalette (Togglable)" to the "Palette" palette which has a title bar
# and a minimize button, and is togglable.
zbc.add_subpalette("Palette:Subpalette (Togglable)")

# Adds a slider and a switch to the "Subpalette (Togglable)" subpalette.
zbc.add_slider(f"Palette:Subpalette (Togglable):Slider", 2, 1, 0, 10, "some help", on_change)
zbc.add_switch(f"Palette:Subpalette (Togglable):Switch", True, "some help", on_change)
