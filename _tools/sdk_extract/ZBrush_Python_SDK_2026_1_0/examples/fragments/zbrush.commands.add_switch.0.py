"""Code fragment for zbrush.commands.add_switch.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

def on_value_changed(sender: str, value: float) -> None:
    print(f"{sender}'s value changed to: {value}")

# Make sure there is no existing "ZScript:Foo" palette and create a new one.
if zbc.exists("ZScript:Foo"):
    zbc.close("ZScript:Foo")

zbc.add_subpalette("ZScript:Foo")

# Create a switch ladled 'ClickMe' in the 'Foo' subpalette which invokes `on_value_changed` when toggled.
zbc.add_switch("ZScript:Foo:ClickMe", True, "", on_value_changed)
