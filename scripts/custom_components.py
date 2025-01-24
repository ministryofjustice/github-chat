"""Custom user interface components."""
from faicons import icon_svg
from shiny import ui

from scripts.icons import question_circle
from scripts.pipeline_config import EMBEDDINGS_MODEL


def more_info_tab(emb_mod:str=EMBEDDINGS_MODEL):
    """Return the HTML elements associated with the 'More details' tab."""

    return ui.nav_panel(
        "More details",
        ui.h2("Model Parameters", {"style": "font-size:25px;"}),
        ui.markdown(
            """
            Since <a href=https://github.com/ministryofjustice/github-chat/blob/main/CHANGELOG.md#010---2024-12-20  target=_blank>version 0.1.0</a>,
            the app generates AI repository summaries in advance. This
            change improves response times. However, model parameters will
            no longer affect the repo AI summaries. For more on model
            parameters, please consult
            <a href=https://platform.openai.com/docs/api-reference/chat target=_blank>the OpenAI API documentation</a>.
            """
        ),
        ui.hr(),
        ui.h2("Citations", {"style": "font-size:25px;"}),
        ui.markdown(
            f"""
            * Embeddings calculated with
            <a href=https://www.nomic.ai/blog/posts/nomic-embed-text-v1 target=_blank>{emb_mod}</a>,
            an open-source embeddings model with a comparable
            context window to leading edge proprietary embeddings
            models.  
            * Embeddings storage with
            <a href=https://docs.trychroma.com/ target=_blank>Chromadb</a>,
            an open-source vector store. Embeddings were created
            with the default normalised
            <a href='https://docs.trychroma.com/guides#changing-the-distance-function' target=_blank>Root Mean Squared Error function</a>."
            * Retrieval with OpenAI's
            <a href=https://openai.com/index/hello-gpt-4o/ target=_blank>GPT-4o series</a>."""
        ),
    )


def feedback_tab():
    """Return the HTML elements associated with the 'Feedback' tab."""
    return ui.nav_panel(
        "Feedback",
        ui.div(
            ui.a(
                icon_svg("github", width="25px", fill="currentColor"),
                href="https://github.com/ministryofjustice/github-chat",
                target="_blank",
                aria_label="GitHub Repository"
            ),
            style="float:right;",
        ),
        ui.h2("We'd like to hear from you.", {"style": "font-size:25px;"}),
        ui.markdown(
            """
            * If you find an issue or have a feature request, please
            <a href=https://github.com/ministryofjustice/github-chat/issues target=_blank>open a GitHub Issue</a>
            * If you'd like to ask a question about the application, head
            over to our
            <a href=https://github.com/ministryofjustice/github-chat/discussions target=_blank>GitHub Discussions page</a>.
            * A list of
            <a href='https://github.com/ministryofjustice/github-chat/issues?q=is%3Aissue%20state%3Aopen%20label%3A%22selected%20for%20development%22' target=_blank>issues selected for development</a>
            is available on GitHub.
            * An overview of the changes to this application can be viewed
            in the
            <a href=https://github.com/ministryofjustice/github-chat/blob/main/CHANGELOG.md target=_blank>changelog document</a>.
            """
        ),
        ui.hr(),
        ui.h2("Known Issues", {"style": "font-size:25px;"}),
        ui.markdown(
            """
            * Repos in the `moj-analytical-platform` may mistakenly show
            repo metadata as 'None'. This is likely to be a flaw in the
            ingestion process regarding GitHub API credentials rather than
            LLM hallucinations. Alternative approaches to authorisation or
            use of
            <a href=https://docs.github.com/en/graphql target=_blank>GitHub GraphQL API</a>
            could resolve this issue.
            * The model no longer streams responses, since
            <a href=https://github.com/ministryofjustice/github-chat/blob/main/CHANGELOG.md#020---2025-01-15  target=_blank>version 0.2.0</a>,
            the LLM is able to extract key terms from the user's prompts in
            order to query the vector store. Implementing this feature with
            streamed responses has proven to be difficult.  
            * This application contains public repo metadata only. We are
            currently examining demand for an internal application that
            would include all MoJ repo metadata.
            """
        ),
    )


NUMERIC_PARAMS = [
    {"id": "selected_n", "label": "n results", "value": 5, "min": 1, "max": None, "step": 1},
    {"id": "dist_thresh", "label": "Distance threshold", "value": 2.0, "min": 0.0, "max": 2.0, "step": 0.1},
    {"id": "temp", "label": "Model temperature", "value": 0.7, "min": 0.0, "max": 1.5, "step": 0.1},
    {"id": "pres_pen", "label": "Presence penalty", "value": 0.0, "min": -2.0, "max": 2.0, "step": 0.1},
    {"id": "freq_pen", "label": "Frequency penalty", "value": 0.0, "min": -2.0, "max": 2.0, "step": 0.1},
    {"id": "max_tokens", "label": "Max tokens", "value": None, "min": 50, "max": 16_384, "step": 50},
]
numeric_inputs = [ui.input_numeric(**_in) for _in in NUMERIC_PARAMS]
_STYLE = "position: relative; top: 40px; left: 185px; z-index: 1;"
NUMERIC_INPUT_POPOVER_PARAMS = [
    {"style": _STYLE, "placement": "top", "id": "selected_n_popover",},
    {"style": _STYLE, "placement": "top", "id": "dist_thresh_popover",},
    {"style": _STYLE, "placement": "top", "id": "temp_popover",},
    {"style": _STYLE, "placement": "top", "id": "pres_pen_popover",},
    {"style": _STYLE, "placement": "top", "id": "freq_pen_popover",},
    {"style": _STYLE, "placement": "top", "id": "max_tokens_popover",},
]

CONTENT_STRINGS = [
    "Controls the number of results returned from the vector store.",
    """Any result returned from the vector store with a distance value that
    exceeds this threshold is removed.""",
    """Larger values increase randomness in the model responses. Very high
    values may increase the likelihood of tokens in languages other than
    English.""",
    """Increases diversity in generated tokens by penalising a token if it
    has appeared before.""",
    "Increases diversity in generated tokens by penalising common tokens.",
    """Optional. The maximum number of tokens that can be generated. Be
    aware that very small values can truncate model responses.""",
]

def _format_popover(
    popover_params: dict, _content: str, icon=question_circle
    ):
    return ui.popover(
        ui.span(
            icon,
            style=popover_params.get("style")
        ),
        _content,
        placement=popover_params.get("placement"),
        id=popover_params.get("id"),
    )

numeric_popovers = [
    _format_popover(popover_params=_in, _content=CONTENT_STRINGS[i])
    for i, _in in enumerate(NUMERIC_INPUT_POPOVER_PARAMS)
    ]

inputs_with_popovers = list(zip(numeric_popovers, numeric_inputs))
