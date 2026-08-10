"""Code fragment for zbrush.commands.set_transpose.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# The n_start/n_end arguments of this function do not express a line segment but rather an origin 
# and a normal. So, these two commands will do absolutely the same, although one could think the 
# second call creates a transpose line ten times longer than the former call.
zbc.set_transpose(x_start=0, y_start=0, z_start=0, x_end=1, y_end=0, z_end=0)
zbc.set_transpose(x_start=0, y_start=0, z_start=0, x_end=10, y_end=0, z_end=0)

# Instead we must treat #start as the origin and #end as a direction normal. We create a line with 
# the origin (0, 0, 0), the direction (1, 1, 0), and a length of five units.
zbc.set_transpose(0, 0, 0, 1, 1, 0, length=5)
