"""Demonstrates how to show a progress indicator with a message when running a long task.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "13/08/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc
import time

def main() -> None:
    """
    """
    # A long-running task simulation, where we update the note bar text and progress periodically.
    for i in range(1000):
        p: float = i / 1000.0
        zbc.set_notebar_text(f"Script is calculating : {round(100 * p, 2)}%", p)
        time.sleep(0.0025)

    # Clear the bar once we are done, otherwise it will linger until something else overrides it.
    zbc.set_notebar_text("", 0)

if __name__ == "__main__":
    main()