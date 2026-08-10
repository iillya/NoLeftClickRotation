"""Code fragment for zbrush.commands.set_hotkey.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# Define a simple event handler.
def on_event(sender: str) -> None:
    print(f"Event: {sender}")

# Make sure there is no existing "ZScript:Foo" palette.
if zbc.exists("ZScript:Foo"):
    zbc.close("ZScript:Foo")

# Create a new palette with a button and after that set a hotkey for the button.
zbc.add_subpalette("ZScript:Foo")
zbc.add_button("ZScript:Foo:A", "A", on_event)
zbc.set_hotkey("ZScript:Foo:A", "ALT+a")
