"""Store schemas for defining structured model outputs here."""
from typing import List

from openai import pydantic_function_tool
from pydantic import BaseModel

class ShouldExtractKeywords(BaseModel):
    """A tool that initiates keyword entity extraction.

    Attributes
    ----------
    use_tool : bool
        Should the ExtractKeywordEntities tool be used.

    """

    use_tool: bool


class ExtractKeywordEntities(BaseModel):
    """
    A model for extracting keyword entities.

    Pass a list of keyword strings extracted from the user's prompt.

    Attributes
    ----------
    keywords : List[str]
        A list of keywords to be extracted.
    """

    keywords: List[str]


class ExportDataToTSV(BaseModel):
    """Export cached data to a TSV file.

    Attributes
    ----------
    export : bool
        When True, file export will begin.
    """

    export: bool

toolbox = [
    pydantic_function_tool(ShouldExtractKeywords),
    pydantic_function_tool(ExportDataToTSV),
]
