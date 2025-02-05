"""Utilities for handling chat stream"""

from scripts.constants import ORCHESTRATOR_SYS_PROMPT, WELCOME_MSG


def _init_stream(
    _stream:list, sys:str=ORCHESTRATOR_SYS_PROMPT, wlcm:str=WELCOME_MSG
    ) -> None:
    """Internal utility for initialising the chat stream.
    
    Can be used at app startup, when the user flushes the chat on action
    button, or when the user refreshes the window.
    """
    _stream
    _stream.clear()
    _stream.append({"role": "system", "content": sys})
    if wlcm:
        _stream.append({"role": "assistant", "content": wlcm})
