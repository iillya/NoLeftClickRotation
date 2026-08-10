"""Code fragment for zbrush.commands.set_keyframe_time.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# Get the total length of the document in seconds and the total amount of keyframes in the
# current track.
max_time: float = zbc.get("Movie:TimeLine:Duration")
count: int = zbc.get_keyframes_count()
if max_time < count:
    raise RuntimeError("Cannot redistribute keyframes with a stride of one second for "
                       "document shorter than the keyframe count.")

# Now rewrite all keyframes so that their index becomes their time value in seconds. E.g., when
# the track has five keyframes, we would move the keyframes to 0s, 1s, 2s, 3s, and 4s.
for i in range(count):
    t_doc: float = float(i) / max_time # Compute the normalized document time for #i seconds.
    zbc.set_keyframe_time(i, t_doc)

print(f"Redistributed {count} keyframes.")
