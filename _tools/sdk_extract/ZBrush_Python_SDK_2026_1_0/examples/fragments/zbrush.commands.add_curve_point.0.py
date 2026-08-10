"""Code fragment for zbrush.commands.add_curve_point.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import commands as zbc

# This example assumes that there is an editable tool active in the canvas.

# Select the standard curve brush and reset all curves by starting a new curves list.
zbc.press("Brush:CurveStandard")
zbc.new_curves()

# Now start creating three curves one by one, filling them with points each. Each curve is meant to
# travel along one of the principal axes (X, Y, Z).
for i in range(3):
    cid: int = zbc.add_new_curve()
    # Create five points for each curve along their respective axes. These points live in
    # the coordinate system of the tool, not in canvas space, so 5 units length for each curve
    # is quite large.
    for j in range(5):
        point: list[float]
        if i == 0: # X-axis
            point = [j, 0.0, 0.0]
        elif i == 1: # Y-axis
            point = [0.0, j, 0.0]
        elif i == 2: # Z-axis
            point = [0.0, 0.0, j]

        # Add the point using Python's unpacking operator *. This is the same as calling
        # zbc.add_curve_point(cid, x=point[0], y=point[1], z=point[2])
        zbc.add_curve_point(cid, *point)

# Finally, commit the curves to the canvas.
zbc.curves_to_ui()
