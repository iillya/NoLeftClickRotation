"""Code fragment for zbrush.commands.un_press.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# Press the "Local Transformations" button in the "Transform" palette.
zbc.press("Transform:Local Transformations")

# Unpress the "Local Transformations" button in the "Transform" palette again. For programmatically 
# unpressing buttons, the same restrictions apply as for user interactions. I.e., buttons that 
# cannot be unpressed by users by clicking them again - like for example the transform mode buttons 
# "Move", "Scale", and "Rotate" - cannot be unpressed by calling #un_press either. In these cases,
# where buttons are not a switch but also have a mutual exclusion with other buttons, one must press
# another button of the same group to unpress the first button.
zbc.un_press("Transform:Local Transformations")
