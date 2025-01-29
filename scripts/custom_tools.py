"""Store schemas for defining structured model outputs here."""
from typing import List

from openai import pydantic_function_tool
from pydantic import BaseModel

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

    Choose a filename that makes sense based upon the user's queries.

    Attributes
    ----------
    filename : str
        The name of the TSV file to which data will be exported. Must end
        in a ".tsv" suffix.
    """

    filename: str

toolbox = [
    pydantic_function_tool(ExtractKeywordEntities),
    pydantic_function_tool(ExportDataToTSV)
    ]
