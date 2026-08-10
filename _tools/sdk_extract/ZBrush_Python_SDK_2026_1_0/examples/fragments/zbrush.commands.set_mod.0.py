"""Code fragment for zbrush.commands.set_mod.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# We define our modifiers as increasing powers of two. We could of course also just write "1 | 4" 
# instead of "ID_X_AXIS | ID_Z_AXIS" below, but this way it is more obvious what we mean. We derive
# the values from the order in which they are shown in the UI.
ID_X_AXIS = 1 << 0  # i.e., 1
ID_Y_AXIS = 1 << 1  # i.e., 2
ID_Z_AXIS = 1 << 2  # i.e., 4

# We now want the X and Z axis modifiers to be active, so we combine them using a bitwise OR.
zbc.set_mod("Tool:Deformation:Unify", ID_X_AXIS | ID_Z_AXIS)
