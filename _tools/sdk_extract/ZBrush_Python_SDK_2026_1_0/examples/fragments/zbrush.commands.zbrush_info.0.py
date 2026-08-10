"""Code fragment for zbrush.commands.zbrush_info.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# Prints all the data #zbrush_info() holds, e.g.:
#
#   0: zbc.zbrush_info(i) = 2026.0
#   1: zbc.zbrush_info(i) = 2.0
#   2: zbc.zbrush_info(i) = 3370.84716796875
#   3: zbc.zbrush_info(i) = 660.066162109375
#   4: zbc.zbrush_info(i) = 0.0
#   5: zbc.zbrush_info(i) = 35171.02734375
#   6: zbc.zbrush_info(i) = 0.0
#   7: zbc.zbrush_info(i) = 118528.0
#   8: zbc.zbrush_info(i) = 37016.1328125
#   9: zbc.zbrush_info(i) = 2025.0
#   10: zbc.zbrush_info(i) = 8.0
#   11: zbc.zbrush_info(i) = 20.0
#   12: zbc.zbrush_info(i) = 14.0
#   13: zbc.zbrush_info(i) = 26.0
#   14: zbc.zbrush_info(i) = 28.0
#   15: zbc.zbrush_info(i) = 3.0
#   16: zbc.zbrush_info(i) = 64.0
#
for i in range(17):
    print(f"{i}: {zbc.zbrush_info(i) = }")