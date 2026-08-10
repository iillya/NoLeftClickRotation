"""Code fragment for zbrush.commands.get_zsphere.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# Define some symbols for better readability.
ID_TOTAL_COUNT: int = 0
ID_X_POS: int = 1
ID_Y_POS: int = 2
ID_Z_POS: int = 3
ID_CHILD_COUNT: int = 10
ID_SUB_INDEX: int = 11

# Get the total number of ZSpheres from the root sphere.
count: int = int(zbc.get_zsphere(property=ID_TOTAL_COUNT, index=0, sub_index=0))
# Now iterate over all ZSpheres and print data for each of them.
for i in range(count):
    print(f"{i} - parent: {zbc.get_zsphere(ID_PARENT, i, 0)}\\n"
          f"      x: {zbc.get_zsphere(ID_X_POS, i, 0)}\\n"
          f"      y: {zbc.get_zsphere(ID_Y_POS, i, 0)}\\n"
          f"      z: {zbc.get_zsphere(ID_Z_POS, i, 0)}\\n"
          f"      child_count: {zbc.get_zsphere(ID_CHILD_COUNT, i, 0)}\\n"
          f"      sub-index: {zbc.get_zsphere(ID_SUB_INDEX, i, 0)}")
