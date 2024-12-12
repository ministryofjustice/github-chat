from ollama import create

from scripts.constants import SYS_PROMPT
from scripts.pipeline_config import LLM, TEMP


def create_model(llm:str=LLM, temp:str=TEMP, prompt:str=SYS_PROMPT):
    # carriage returns break ollama.create
    prompt = prompt.replace("\n", " ")
    modelfile = f"""
    FROM {llm}
    PARAMETER temperature {temp}
    SYSTEM {prompt}

    """    
    create(LLM, modelfile=modelfile)
