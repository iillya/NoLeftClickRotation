"""Code fragment for zbrush.commands.set.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# Set the draw size to 42.
zbc.set("Draw:Draw Size", 42)

# Enable move and edit mode in the transform palette.
zbc.set("Transform:Move", 1)
zbc.set("Transform:Edit", 1)

# Set the light position as an example for an item with a secondary value.
zbc.set("Light:Light Placement", 0.5, 0.5)

# Note that buttons can also be pressed. I.e., this is equivalent to what we did above to set the transform 
# modes. The advantage of using #set is that we do not need to check the current state of the button first, 
# we can just set it to the desired state.
if not zbc.get("Transform:Move"):
    zbc.press("Transform:Move") # Enables move mode
if not zbc.get("Transform:Edit"):
    zbc.press("Transform:Edit") # Enables edit mode

# Somtimes it is also desirable to check the current value before calling #set to avoid unnecessary redraws or
# recomputations. A very defensive way to set a new value would be this, which also takes floating point 
# precision issues into account.

new_value: float = 3.14159 # The new value we want to set.
value_delta: float = 1e-5 # Acceptable difference threshold below which we do not update the value.
if zbc.exists("Foo::Bar") and (abs(zbc.get("Foo::Bar") - new_value) > value_delta):
    zbc.set("Foo::Bar", new_value)
