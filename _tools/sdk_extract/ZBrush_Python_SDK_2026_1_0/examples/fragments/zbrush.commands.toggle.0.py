"""Code fragment for zbrush.commands.toggle.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# Define a simple event handler.
def on_event(sender: str, value: bool) -> None:
    print(f"Event: {sender}, Value: {value}")

# Make sure there is no existing "ZScript:Foo" palette.
if zbc.exists("ZScript:Foo"):
    zbc.close("ZScript:Foo")

# Create a new palette with a switch and after it has been created, toggle it.
zbc.add_subpalette("ZScript:Foo")
zbc.add_switch("ZScript:Foo:A", True, "A", on_event)
zbc.toggle("ZScript:Foo:A")
