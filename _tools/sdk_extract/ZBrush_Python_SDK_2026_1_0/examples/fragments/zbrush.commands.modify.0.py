"""Code fragment for zbrush.commands.modify.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

def switch_sizes(item: str) -> None:
    '''Switches the widths of two buttons in the ZScript:Foo palette.
    '''
    a_width: int = int(zbc.get_width("ZScript:Foo:A"))
    b_width: int = int(zbc.get_width("ZScript:Foo:B"))
    zbc.modify("ZScript:Foo:A", width=b_width)
    zbc.modify("ZScript:Foo:B", width=a_width)
    zbc.update(repeat_count=1, redraw_ui=True)

# Make sure we start with a clean state by deleting the palette if it already exists.
if zbc.exists("ZScript:Foo"):
    zbc.close("ZScript:Foo") 

# Add two buttons with the width of 80px and 40px and the switch_sizes callback.
zbc.add_subpalette("ZScript:Foo")
if not zbc.exists("ZScript:Foo:A"):
    zbc.add_button("ZScript:Foo:A", "", switch_sizes, width=80.0)
if not zbc.exists("ZScript:Foo:B"):
    zbc.add_button("ZScript:Foo:B", "", switch_sizes, width=40.0)
