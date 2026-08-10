"""Code fragment for zbrush.commands.freeze.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# The payload function.
def payload() -> None:
    '''Subdivides the active tool three times, unwraps it, and then creates a displacement map.
    '''
    for _ in range(3):
        zbc.press("Tool:Geometry:Divide")

    auto_seams: str = "Tool:UV Map:Create (Unwrap):Auto Seams"
    print(f"{zbc.get_status(auto_seams) = }")
    if not zbc.get_status(auto_seams):
        zbc.toggle(auto_seams)

    zbc.press("Tool:UV Map:Create (Unwrap):Unwrap")
    for _ in range(10):
        zbc.press("Tool:Geometry:Lower Res")

    zbc.press("Tool:Displacement Map:Create DispMap")

# Carry out our #payload function while halting UI updates while it is running.
zbc.freeze(payload)
