"""Code fragment for zbrush.commands.unlock.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# Lock the 'Transform:Move' button, making it unresponsive to user interactions.
zbc.lock("Transform:Move")

# Unlocks the 'Transform:Move' button, making it again responsive to user interactions.
zbc.unlock("Transform:Move")
