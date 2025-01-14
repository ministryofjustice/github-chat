"""Contains the logic for checking the moderation of user prompts."""
from openai import Client
from shiny import reactive


async def check_moderation(prompt:str, openai_client:Client) -> str:
    """Check if the prompt is flagged by OpenAI's moderation tool.

    Awaits the response from the OpenAI moderation tool before
    attempting to access the content.

    Parameters
    ----------
    prompt : str
        The user's prompt to check.
    reactive_client : reactive.Value
        The reactive value containing an openai.AsyncOpenAI instance.

    Returns
    -------
    str
        The category violations if flagged, else None.
    """
    response = openai_client.moderations.create(input=prompt)
    content = response.results[0].to_dict()
    if content["flagged"]:
        infringements = []
        for key, val in content["categories"].items():
            if val:
                infringements.append(key)
        return " & ".join(infringements)
    else:
        return prompt
