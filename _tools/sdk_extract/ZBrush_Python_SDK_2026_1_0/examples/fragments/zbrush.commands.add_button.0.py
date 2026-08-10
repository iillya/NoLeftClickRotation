"""Code fragment for zbrush.commands.add_button.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# A callback functions for multiple buttons which checks the item path of the raised item.
def on_button_pressed(sender: str) -> None:
    if str(sender).endswith("Bar"):
        print("A button named 'Bar' was pressed.")
    else:
        print(f"Button pressed: {sender = }")

# Add a 'Foo' subpalette to the 'ZScript' palette if it doesn't exist.
if not zbc.exists("ZScript:Foo"):
    zbc.add_subpalette("ZScript:Foo")

# Adds a button labeled 'Bar' to the 'ZScript:Foo' subpalette with the tooltip "Hello World!" 
# which invokes the callback #on_button_pressed when clicked.
zbc.add_button("ZScript:Foo:Bar", "Hello World!", on_button_pressed)
