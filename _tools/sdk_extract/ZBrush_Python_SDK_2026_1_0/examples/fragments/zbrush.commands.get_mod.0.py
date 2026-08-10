"""Code fragment for zbrush.commands.get_mod.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

value: str = zbc.get_mod("Tool:Deformation:Unify")
print(f"The current modifier value for 'Tool:Deformation:Unify' is: {value}.")
if value & 1:
    print("The X modifier is active.")
if value & 2:
    print("The Y modifier is active.")
if value & 4:
    print("The Z modifier is active.")
