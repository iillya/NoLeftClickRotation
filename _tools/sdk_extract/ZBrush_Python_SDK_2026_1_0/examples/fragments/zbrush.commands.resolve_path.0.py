"""Code fragment for zbrush.commands.resolve_path.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

import os
import sys

# Let's assume we have this directory structure:
#
#   D:
#   └── scripts
#       ├── my_script.py
#       └── my_data.txt
#
# And the module we are currently running is #my_script.py. Then we can infer the absolute
# path to 'my_data.txt' as follows:
abs_data_path: str = zbc.resolve_path("my_data.txt") # > "D:\\scripts\\my_data.txt"

# As many for these legacy Zscript functions, it is a bit questionable to use a function
# for something this simple when using Python. We can achieve the same just by using #os
# and #__file__
abs_data_path_os: str = os.path.join(os.path.dirname(__file__), "my_data.txt")

# It is also really important to understand that the working directory of this Python script
# is NOT the directory of the script itself as one might be used to from a CPython instance, 
# but the directory of the running Zbrush instance.
print(f"{os.getcwd() = }")   # Will print the installation location of ZBrush.

# This will NOT try to open a file "my_data.txt" next to the file of this module but a file
# of that name in the ZBrush installation directory (because relative paths are releative to
# the working directory).
with open("my_data.txt", "r") as f:
    data = f.read()
    print(f"{data = }")

# Changing the current working directory is not advisable, as you do not just do this for
# your script, but for all scripts the user will ever run. And some scripts might implicitly
# rely on the current working directory being the ZBrush installation directory. So, we
# should use absolute paths instead.
data_file: str = os.path.join(os.path.dirname(__file__), "my_data.txt")
with open(data_file, "r") as f:
    data = f.read()
    print(f"{data = }")
