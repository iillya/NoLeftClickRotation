"""Code fragment for zbrush.commands.lock.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# Locks the 'Transform:Move' button, making it unresponsive to user interactions.
zbc.lock("Transform:Move")
