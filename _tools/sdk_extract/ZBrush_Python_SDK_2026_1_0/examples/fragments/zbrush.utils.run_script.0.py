"""Code fragment for zbrush.utils.run_script.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import utils as zbu

# The code to run.
code: str = '''
from zbrush import commands as zbc

print(f"Hello world from the {zbc.__name__} API!")
'''

# Runs the given code.
zbu.run_script(code)

# We can also use here #exec to run the code.
exec(code)