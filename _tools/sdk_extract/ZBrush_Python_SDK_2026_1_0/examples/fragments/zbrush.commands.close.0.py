"""Code fragment for zbrush.commands.close.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# Close ZScript:Python Scripting palette.
zbc.close("ZScript:Python Scripting")

# Close ZScript:Python Scripting palette by passing the button 'Load' as the item path.
zbc.close("ZScript:Python Scripting:Load", False, True)