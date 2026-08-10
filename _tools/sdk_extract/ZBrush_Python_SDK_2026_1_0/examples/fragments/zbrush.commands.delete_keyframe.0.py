"""Code fragment for zbrush.commands.delete_keyframe.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# This example assumes that there are no existing keyframes in the document.

# Add three keyframes at the normalized document times 0, .5, and 1.
zbc.add_keyframe(0)
zbc.add_keyframe(0.5)
zbc.add_keyframe(1.0)

# Deletes the second keyframe, i.e., 50% of the timeline.
zbc.delete_keyframe(1)
