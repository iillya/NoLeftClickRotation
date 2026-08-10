"""Code fragment for zbrush.commands.add_zsphere.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

def add_nodes() -> None:
    '''Adds three new ZSpheres to the currently active ZSpheres tool.
    '''
    # Get the index of the last currently existing ZSphere and then start parenting
    # three new ZSpheres to it.
    offset: int = int(zbc.get_zsphere(property=0, index=0, sub_index=0)) - 1
    for i in range(3):
        zbc.add_zsphere(x=0.0, y=i*.5, z=0.0, radius=0.25, parent_index=offset + i)

zbc.edit_zsphere(add_nodes)
