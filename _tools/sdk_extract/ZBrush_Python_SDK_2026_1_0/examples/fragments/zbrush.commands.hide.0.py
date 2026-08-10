"""Code fragment for zbrush.commands.hide.
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

# Creates a new palette with two buttons and after that hides one of them.
zbc.add_subpalette("ZScript:Foo")
zbc.add_button("ZScript:Foo:A", "A", on_event)
zbc.add_button("ZScript:Foo:B", "B", on_event)
zbc.hide("ZScript:Foo:B")