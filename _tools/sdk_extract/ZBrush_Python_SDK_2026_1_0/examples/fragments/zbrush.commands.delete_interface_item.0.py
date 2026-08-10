"""Code fragment for zbrush.commands.delete_interface_item.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# Deletes the item "Button" in the "Zscript:Foo" sub-palette if it exists.
if zbc.exists("Zscript:Foo:Button"):
    zbc.delete_interface_item("Zscript:Foo:Button")
