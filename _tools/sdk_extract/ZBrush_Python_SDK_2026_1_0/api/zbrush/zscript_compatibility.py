# Stub file for 'zscript_compatibility' module.
# This file was generated automatically.
from typing import Any


__doc__: str
__name__: str

def rand(value: float) -> float:
    """Returns a random float between 0 and the specified value.

    .. note::

        Exposes the legacy ZScript function for faithfully porting legacy ZScripts. Use Python's native `random.uniform` in new scripts.

    Args:
        value (float): The upper bound for the random float.    

    Returns:
        float: A random float between 0 and the specified value.

    :Example:

        .. literalinclude:: /../../examples/fragments/zbrush.zscript_compatibility.rand.0.py
            :language: python
            :lines: 7-

    """
    ...

def rand_int(value: float) -> int:
    """Returns a random integer between 0 and the specified value.

    .. note::

        Exposes the legacy ZScript function for faithfully porting legacy ZScripts. Use Python's native `random.randint` in new scripts.


    Args:
        value (float): The upper bound for the random integer.

    Returns:
        int: A random integer between 0 and the specified value.

    :Example:

        .. literalinclude:: /../../examples/fragments/zbrush.zscript_compatibility.rand_int.0.py
            :language: python
            :lines: 7-

    """
    ...
