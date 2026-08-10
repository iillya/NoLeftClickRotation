"""Code fragment for zbrush.utils.run_path.
"""
__author__ = "Ferdinand Hoppe"
__date__ = "16/10/2025"
__copyright__ = "Maxon Computer"

from zbrush import utils as zbu

script_path: str = "d:/myScript.py" # A script we want to run.

# # Runs the script located at #path.
zbu.run_path(script_path)

# Alternative approaches which can be better depending on the context, can be to use builtin Python
# tools such as `runpy`, `exec`, or `importlib` as we have here full control over what is going on.

# Execute the script content ourself, here is the advantage that we have more control over the
# globals and locals.
content: str = open(script_path, encoding="utf-8").read()
exec(content, {"__name__": "__main__", "__file__": script_path, "MY_VARIABLE": 42})
