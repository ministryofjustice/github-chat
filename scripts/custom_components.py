"""Custom user interface components."""
from faicons import icon_svg
from shiny import ui

from scripts.pipeline_config import EMBEDDINGS_MODEL


def more_info_tab(emb_mod:str=EMBEDDINGS_MODEL):
    """Return the HTML elements associated with the 'More details' tab."""

    return ui.nav_panel(
        "More details",
        ui.h2("Citations", {"style": "font-size:25px;"}),
        ui.markdown(
            f"""* Embeddings calculated with
            <a href=https://www.nomic.ai/blog/posts/nomic-embed-text-v1 target=_blank>{emb_mod}</a>,
            an open-source embeddings model with a comparable
            context window to leading edge proprietary embeddings
            models."""
        ),
        ui.markdown(
            """* Embeddings storage with
            <a href=https://docs.trychroma.com/ target=_blank>Chromadb</a>,
            an open-source vector store. Embeddings were created
            with the default normalised
            <a href='https://docs.trychroma.com/guides#changing-the-distance-function' target=_blank>Root Mean Squared Error function</a>."""
        ),
        ui.markdown(
            """* Retrieval with OpenAI's
            <a href=https://openai.com/index/hello-gpt-4o/ target=_blank>GPT-4o series</a>."""
        ),
        ui.hr(),
        ui.h2("Known Issues", {"style": "font-size:25px;"}),
        ui.markdown(
            """* Queries are slow. This is due to design decisions
            in an effort to mitigate hallucinations. To reduce wait
            time, reduce the value of n Results. Response times
            could be improved by pre-generating AI repo summaries.
            """
        ),
        ui.markdown(
            """* Repos in the `moj-analytical-platform` may
            mistakenly show repo metadata as 'None'. This is likely
            to be a flaw in the ingestion process regarding GitHub
            API credentials rather than LLM hallucinations.
            Alternative approaches to authorisation or use of
            <a href=https://docs.github.com/en/graphql target=_blank>GitHub GraphQL API</a>
            could resolve this issue."""
        ),
        ui.markdown(
            """* Queries such as 'machine learning' tend to produce
            results with higher relevance than queries like 'Are
            there any repos about machine learning?'. At a cost to
            performance, entity extraction of search keywords in
            the user's query could be explored using the
            <a href='https://dottxt-ai.github.io/outlines/latest/welcome/' target=_blank>Python `outlines` library</a>.
        """),
        ui.markdown(
            """* This application contains public repo metadata
            only. We are currently examining demand for an internal
            application that would include all MoJ repo metadata.
            """
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
        ui.markdown("Provide feedback in the following ways: "),
        ui.markdown(
            """* If you find an issue or have a feature request,
            please
            <a href=https://github.com/ministryofjustice/github-chat/issues target=_blank>open a GitHub Issue</a>
            """
        ),
        ui.markdown(
            """* If you'd like to ask a question about the
            application, head over to our
            <a href=https://github.com/ministryofjustice/github-chat/discussions target=_blank>GitHub Discussions page</a>.
            """
        ),
        ui.markdown(
            """* A list of
            <a href='https://github.com/ministryofjustice/github-chat/issues?q=is%3Aissue%20state%3Aopen%20label%3A%22selected%20for%20development%22' target=_blank>list of issues selected for development</a>
            is available on GitHub."""
        ),
        ui.markdown(
            """* An overview of the changes to this application can
            be viewed in the
            <a href=https://github.com/ministryofjustice/github-chat/blob/main/CHANGELOG.md target=_blank>changelog document</a>.
            """
        ),
    )


NUMERIC_INPUTS = [
    {"id": "selected_n", "label": "n results", "value": 5, "min": 1, "max": None, "step": 1},
    {"id": "dist_thresh", "label": "Distance threshold", "value": 1.0, "min": 0.0, "max": 2.0, "step": 0.1},
    {"id": "temp", "label": "Model temperature", "value": 0.7, "min": 0.0, "max": 1.0, "step": 0.1},
    {"id": "pres_pen", "label": "Presence penalty", "value": 0.0, "min": -2.0, "max": 2.0, "step": 0.1},
    {"id": "max_tokens", "label": "Max tokens", "value": None, "min": 50, "max": 16_384, "step": 50},
]
numeric_inputs = [ui.input_numeric(**_in) for _in in NUMERIC_INPUTS]
