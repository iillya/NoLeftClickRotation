"""Code fragment for zbrush.commands.set_zsphere.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

def set_nodes() -> None:
    '''Sets the x-coordinates of all ZSpheres to one quarter of their index.
    '''
    # Get the total number of ZSpheres from the root and then start iterating.
    count: int = int(zbc.get_zsphere(property=0, index=0, sub_index=0))
    for i in range(count):
        zbc.set_zsphere(property=1, index=i, value=0.25 * i)

zbc.edit_zsphere(set_nodes)
