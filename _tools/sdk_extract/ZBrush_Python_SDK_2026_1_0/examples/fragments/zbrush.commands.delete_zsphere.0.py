"""Code fragment for zbrush.commands.delete_zsphere.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# Define some symbols for better readability.
ID_X_POS: int = 1
ID_Y_POS: int = 2
ID_Z_POS: int = 3
ID_RADIUS: int = 4
ID_COLOR: int = 5

def delete_all_nodes() -> None:
    # Get the total number of ZSpheres from the root ZSphere.
    count: int = int(zbc.get_zsphere(property=0, index=0, sub_index=0))

    # Reset the root sphere to default values because it cannot be deleted.
    zbc.set_zsphere(ID_X_POS, 0, 0.0)
    zbc.set_zsphere(ID_Y_POS, 0, 0.0)
    zbc.set_zsphere(ID_Z_POS, 0, 0.0)
    zbc.set_zsphere(ID_RADIUS, 0, 1.0)
    zbc.set_zsphere(ID_COLOR, 0, 16777215.0)

    # Delete all remaining spheres. It is really important to do this in reverse order, 
    # as ZBrush will not let you delete ZSpheres whose parent you have already deleted. 
    # But they will still exist, i.e., you will only end up deleting a subset of the 
    # spheres. The reverse order approach assumes that children have higher indices than
    # their parents. Which usually holds true but there is no hard guarantee, as we can
    # structure ZSphere trees in the API however we want. The safer approach would 
    # be to delete the ZSpheres in LRN (post-order) depth first traversal, i.e., delete 
    # the tree "from the inside out".
    for i in reversed(range(1, count)):
        zbc.delete_zsphere(i)

zbc.edit_zsphere(delete_all_nodes)