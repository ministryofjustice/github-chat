"""Store schemas for defining structured model outputs here."""
from typing import List

from openai import pydantic_function_tool
from pydantic import BaseModel

class ExtractKeywordEntities(BaseModel):
    keywords: List[str]

toolbox = [pydantic_function_tool(ExtractKeywordEntities)]
