"""Code fragment for zbrush.commands.get_last_used_filename.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# The example assume that we have saved this script as file and then loaded it with the
# load button in the Python section.
print(f"{zbc.get_last_used_filename() = }")
# > D:\\stuff\\examples\\test.py (printed as 'D:stuffexamplestest.py')