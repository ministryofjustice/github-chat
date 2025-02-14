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
    A tool for extracting keyword entities from user prompts.

    Pass a list of keyword strings extracted from the user's prompt. These
    keywords will be used to query a vector store of documents with
    information about Ministry of Justice GitHub repositories.

    Attributes
    ----------
    keywords : List[str]
        A list of keywords to be extracted.
    """

    keywords: List[str]


class ExportDataToTSV(BaseModel):
    """Export cached repo results data to a TSV file.

    Attributes
    ----------
    export : bool
        When True, file export will begin.
    """

    export: bool


class ShouldExplainTools(BaseModel):
    """Indicate that the User requires an overview of available tools.

    Attributes
    ----------
    use_tool: bool
        Should the ExplainTools tool be used.

    style_guidance: str
        If the user has provided guidance on formatting the tool overview,
        include this here.
    """
    use_tool: bool
    style_guidance: str


class ExplainTools(BaseModel):
    """Provide the User with an overview of your tools.

    Ensure that any style guidance requested by the user is adhered to. 

    Attributes
    ----------
    toolbox_manual: str
        The formatted guide to all of the available tools.

    """
    toolbox_manual: str


class WipeChat(BaseModel):
    """Initialise the chat interface and discard any cached results.

    Attributes
    ----------
    use_tool: bool
        Should the WipeChat tool be used.

        
    """
    use_tool: bool


class ShouldDraftEmail(BaseModel):
    """User indicated that they intend to draft an Email. This tool start
    the DraftEmail logic.

    Attributes
    ----------
    use_tool: bool
        Should the DraftEmail tool be used.
    """
    use_tool: bool


class DraftEmail(BaseModel):
    """Draft an Email for the user based on the conversation context.

    If a User indicates they wish to Email the application maintainer, this
    tool will prepopulate an Email with an appropriate subject and content
    based on their reasons for reaching out.

    Attributes
    ----------
    subject: str
        The subject line of the draft Email.
    body: str
        The content of the draft Email. Include appropriate formatting. 
    """
    subject: str
    body: str


toolbox = [
    pydantic_function_tool(ShouldExtractKeywords),
    pydantic_function_tool(ShouldExplainTools),
    pydantic_function_tool(ShouldDraftEmail),
    pydantic_function_tool(ExportDataToTSV),
    pydantic_function_tool(WipeChat),
] # these tools are available to the orchestrator agent

toolbox_manual_members = [
    ExtractKeywordEntities,
    ExportDataToTSV,
    ExplainTools,
    WipeChat,
    DraftEmail,
] # these tools will be included in any tool explanations required
