"""Code fragment for zbrush.commands.show.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# 1.

# This is the first way how to use this function, to show a palette. Here we show the 'Draw' palette.
# When it is not docked, it will open as a floating palette under the cursor. Because this might 
# interfere with the example belopw, this line is commented out.
# zbc.show("Draw")

# 2.

# This is the second way how to use this function, to show a script generated  interface item which 
# has been hidden before.

# Define a simple event handler.
def on_event(sender: str) -> None:
    print(f"Event: {sender}")

# Make sure there is no existing "ZScript:Foo" palette.
if zbc.exists("ZScript:Foo"):
    zbc.close("ZScript:Foo")

# Create a new palette with two buttons, maximize the palette, and after that hide the second button.
zbc.add_subpalette("ZScript:Foo")
zbc.add_button("ZScript:Foo:A", "A", on_event)
zbc.add_button("ZScript:Foo:B", "B", on_event)
zbc.maximize("ZScript:Foo")
zbc.hide("ZScript:Foo:B")

# Show the hidden button again.
zbc.show("ZScript:Foo:B", True)