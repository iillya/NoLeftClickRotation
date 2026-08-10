"""Code fragment for zbrush.commands.ask_string.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# Displays a text input dialog and returns the string typed by user.
result: str = zbc.ask_string("Your name here", "Please enter your name:")
print(f"The entered name is: {result}")
