"""Code fragment for zbrush.commands.exists.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# Disables the item 'Button' in the 'ZScript:Foo' sub-palette only when it exists.
if zbc.exists("ZScript:Foo:Button"):
    zbc.disable("ZScript:Foo:Button")
