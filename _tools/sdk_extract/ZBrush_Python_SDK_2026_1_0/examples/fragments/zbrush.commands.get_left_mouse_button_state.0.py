"""Code fragment for zbrush.commands.get_left_mouse_button_state.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc
import time

# Poll the left mouse button state for three seconds and print its state every 0.25 
# seconds. The output of the script will only be shown after the script has finished,
# because the script is blocking.

t_start: float = time.time()
t_delta: float = 3.0
while (time.time() - t_start) < t_delta:
    state: bool = zbc.get_left_mouse_button_state()
    print(f"Current left mouse button pressed state: {state}.")
    time.sleep(0.25)
