"""Code fragment for zbrush.commands.get_last_typed_filename.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# This example assumes that we have saved this script as at `D:\\stuff\\examples\\test.py` and then 
# loaded it with the 'Load' button in the Python palette of ZBrush.
print(f"{zbc.get_last_typed_filename() = }")
# > D:\\stuff\\examples\\test.py (printed as 'D:stuffexamplestest.py')
