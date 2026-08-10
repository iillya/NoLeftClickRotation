"""Code fragment for zbrush.commands.system_info.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# Prints a system infomation string, e.g. (a tuncated string):
#   "Intel(R) Core(TM) i7-10700K CPU @ 3.80GHz MaxThreads=16 ActiveTh@"
print(zbc.system_info())
