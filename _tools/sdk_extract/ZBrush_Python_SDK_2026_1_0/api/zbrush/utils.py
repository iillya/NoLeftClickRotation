# Stub file for 'utils' module.
# This file was generated automatically.
from typing import Any


__doc__: str
__name__: str

def clear_output() -> None:
    """Clears the Python output log.

    .. note::

        This clears the output log but does not reset the scroll position of the log. So, when the log had been scrolled down substantially, you will have to scroll back up to see new output.

    :Example:

        .. literalinclude:: /../../examples/fragments/zbrush.utils.clear_output.0.py
            :language: python
            :lines: 7-

    """
    ...

def run_path(script_path: str, shared_environment: bool = True) -> bool:
    """Executes the Python script at the passed `script_path`.

    .. warning::

        - Running arbitrary code is very unsafe. Avoid executing code from untrusted sources.
        - Do not try to use `subprocess.run` with `sys.executable`, because just as `multiprocessing`, it will create a new Python interpreter process which means a new ZBrush instance in case of the ZBrush Python interpreter. This is not supported and will lead to crashes.

    Args:
    	script_path (`str`): File path to the script to execute.
    	shared_environment (`bool`, optional): Whether the script is executed in its own scope or the global scope.

    Returns:
        bool: `True` if the script was successfully executed, `False` otherwise.

    :Example:

        .. literalinclude:: /../../examples/fragments/zbrush.utils.run_path.0.py
            :language: python
            :lines: 7-

    """
    ...

def run_script(script: str, shared_environment: bool = True) -> bool:
    """Executes the passed Python `script` code.

    .. warning::

        Running arbitrary code is very unsafe. Avoid executing code from untrusted sources.

    Args:
    	script (`str`): Script to execute.
    	shared_environment (`bool`, optional): Whether the script is executed in its own scope or the global scope.

    Returns:
        bool: `True` if the code was successfully executed, `False` otherwise.

    :Example:

        .. literalinclude:: /../../examples/fragments/zbrush.utils.run_script.0.py
            :language: python
            :lines: 7-

    """
    ...
