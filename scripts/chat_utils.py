"""Utilities for handling chat stream"""

from scripts.constants import APP_SYS_PROMPT, WELCOME_MSG

system_prompt = {"role": "system", "content": APP_SYS_PROMPT}
welcome = {"role": "assistant", "content": WELCOME_MSG}


def _init_stream(_stream:list, sys:str=system_prompt, wlcm:str=welcome):
    """Internal utility for initialising the chat stream.
    
    Can be used at app startup, when the user flushes the chat on action
    button, or when the user refreshes the window.
    """
    _stream
    _stream.clear()
    _stream.append(sys)
    _stream.append(wlcm)
