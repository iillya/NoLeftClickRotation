"""Code fragment for zbrush.commands.get_next_filename.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

zbc.set_next_filename(r"D:\\temp\\test.zbr")
print(f"{zbc.get_next_filename() = }") # > D:\\temp\\test.zbr (printed as 'D:temptest.zbr')