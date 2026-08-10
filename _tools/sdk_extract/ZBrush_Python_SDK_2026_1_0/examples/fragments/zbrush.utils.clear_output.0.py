"""Code fragment for zbrush.utils.clear_output.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc 
from zbrush import utils as zbu

# Show the 'Tutorial View', i.e., the part of the UI which holds the console, then turn on the 
# 'Python Output' mode, and finally clear the output. There is currently no way (which at least
# I see) with which we could check if the 'Tutorial View' is already open. Running `click` on
# an already opened 'Tutorial View' will close it again.
zbc.click("Tutorial View")
zbc.set("ZScript:Script Window Mode:Python Output", True)
zbu.clear_output()
zbc.update(redraw_ui=True)
