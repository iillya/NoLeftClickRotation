"""Code fragment for zbrush.commands.edit_zsphere.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

def do_edit() -> None:
    # Deletes the third ZSphere in the currently active ZSpheres tool.
    zbc.delete_zsphere(2)

# The #delete_zsphere call in #do_edit is only valid within the context of #edit_zsphere.
zbc.edit_zsphere(do_edit)
