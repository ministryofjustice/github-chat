import datetime
import logging
from pathlib import Path
import re

import chromadb
import dotenv
from faicons import icon_svg
from nomic import embed, login
import openai
from pyprojroot import here
from shiny import App, ui

from scripts.constants import SUMMARY_PROMPT, SYS_PROMPT, WELCOME_MSG
from scripts.pipeline_config import (
    EMBEDDINGS_MODEL,
    META_LLM,
    REPO_LLM,
    VECTOR_STORE_PTH,
)
from scripts.string_utils import (
    format_results,
    format_meta_prompt,
    get_vintage_from_str,
    sanitise_string,
)

# Before ==================================================================
secrets = dotenv.dotenv_values(here(".env"))
app_dir = Path(__file__).parent
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(here("logs/app.log"))],
    )

system_prompt = {"role": "system", "content": SYS_PROMPT}
stream = [system_prompt]
stream.append({"role": "assistant", "content": WELCOME_MSG})

nm_pat = re.compile(r"Name:\s*([^,]+)", re.IGNORECASE)
url_pat = re.compile(r"url:\s*([^,]+)", re.IGNORECASE)
desc_pat = re.compile(r"Description: (.*?)(?=\sREADME:)", re.IGNORECASE)
readme_pat = re.compile(r"README: (.*?)([^']+)", re.IGNORECASE)

login(token=secrets["NOMIC_KEY"])
openai_client = openai.AsyncOpenAI(api_key=secrets["OPENAI_KEY"])
chroma_client = chromadb.PersistentClient(path=str(VECTOR_STORE_PTH))
latest_collection_nm = max(chroma_client.list_collections()).name
collection = chroma_client.get_collection(name=latest_collection_nm)
vintage = get_vintage_from_str(latest_collection_nm)

# Startup ends ============================================================

app_ui = ui.page_fillable(

    ui.head_content(
        ui.tags.link(
            rel="icon", type="image/svg", href="favicon.svg"
        ),
        ui.include_css(app_dir / "www/styles.css"),
    ),
    ui.tags.head(ui.HTML("<html lang='en'>")),
    ui.panel_title("MoJ GitHub Chat - Chat With MoJ GitHub Repositories"),
    ui.div(
        ui.img(
            src="moJxlogo.png",
            width="100rem",
            style="padding-left:0.2rem;padding-top:0.6rem;float:left;",
            alt="MoJx Logo",
            ),

        ui.h1(
            "Welcome to MoJ GitHub Chat",
            style="padding-top:0.2rem;text-align:center;"
        ),
        id="header"
    ),

    ui.panel_well(
        ui.h2("This is a prototype", {"style": "font-size:22px;"}),        
        """All information presented is for testing and feedback purposes
        only. Large Language Models can make mistakes. Check important
        information."""
    ),
    ui.markdown(
        """**Public code** repositories in ministryofjustice and
        moj-analytical-services GitHub organisations are included."""),
    ui.p(f"Data last updated: {vintage}"),
    ui.card(  
    ui.layout_sidebar(  
        ui.sidebar(
            ui.input_numeric(
                id="selected_n",
                label="n Results",
                value=5,
                min=1,
                step=1,
            ),
            ui.input_numeric(
                id="dist_thresh",
                label="Distance Threshold",
                value=1.0,
                min=0.0,
                max=2.0,
                step=0.1,
                ),
            bg="#f0e3ff"
            ),  
        ui.navset_tab(
            ui.nav_panel(
                f"Chat with {META_LLM}",
                ui.chat_ui(id="chat", placeholder="Enter some keywords"),
            ),
            ui.nav_panel(
                "More details",
                ui.h2("Citations", {"style": "font-size:25px;"}),
                ui.markdown(
                    f"""* Embeddings calculated with
                    <a href=https://www.nomic.ai/blog/posts/nomic-embed-text-v1 target=_blank>{EMBEDDINGS_MODEL}</a>,
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
            ),
            ui.nav_panel(
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
            ),
        ),
    )), 
    fillable_mobile=True,
)


def server(input, output, session):
    chat = ui.Chat(
        id="chat",
        messages=["Hi! Perform semantic search with MoJ GitHub repos."],
        tokenizer=None)


    @chat.on_user_submit
    async def respond():
        """A callback to run when the user submits a message."""
        current_time = datetime.datetime.now()
        # Get the user's input
        usr_prompt = sanitise_string(chat.user_input())
        logging.info("User submitted prompt =============================")
        logging.info(f"Santised user input: {usr_prompt}")

        # embed with nomic
        query_embeddings = embed.text(
            texts=[usr_prompt],
            model=EMBEDDINGS_MODEL,
            task_type="search_query",
        )
        results = collection.query(
            query_embeddings=query_embeddings.get("embeddings"),
            n_results=input.selected_n()
            )

        # filter out any results that are above the distance threshold
        logging.info("Vector Store queried ==============================")
        logging.info(f"Search results: {results}")
        logging.info("Filtering results =================================")
        rem_inds = [
            i for i, dist in enumerate(results["distances"][0])
            if dist > input.dist_thresh()
        ]
        # delete results over selected threshold
        for i in rem_inds[::-1]:
            # careful with removing as adjusts index
            del results["documents"][0][i]
        
        # handle cases where distance threshold is too low
        if len(results["documents"][0]) == 0:
            ui.notification_show(
                "No results were shown, increase distance threshold"
                )

        # for each result, extract properties and inject into template
        ui_resps = []  
        for ind, res in enumerate(results["documents"][0]):
            nm = nm_pat.findall(res)
            url = url_pat.findall(res)
            desc = desc_pat.findall(res)
            readme = readme_pat.findall(res)
            dist = results["distances"][0][ind]

            logging.info(f"All available metadatas:\n{results['metadatas'][0][ind]}")
            upd_at = results["metadatas"][0][ind].get("updated_at")
            dt_object = datetime.datetime.fromtimestamp(upd_at)

            days_ago = (current_time - dt_object).days
            formatted_date = dt_object.strftime("%A, %d %B, %Y at %H:%M")
            date_out = f"{formatted_date} ({days_ago} days ago)."

            meta_dict = {
                "org_nm": results["metadatas"][0][ind].get("org_nm"),
                "repo_nm": nm[0] if nm else None,
                "html_url": url[0] if url else None,
                "repo_desc": desc[0] if desc else None,
                "is_private": results["metadatas"][0][ind].get("is_private"),
                "is_archived": results["metadatas"][0][ind].get("is_archived"),
                "programming_language": results["metadatas"][0][ind].get("programming_language"),
                "updated_at": date_out,
                "distance": dist, 
            }

            logging.info(f"Metadatas:\n{meta_dict}")

            repo_content = {
                "role": "user",
                "content": SUMMARY_PROMPT.format(repo_deets=res)
                }
            stream.append(repo_content)
            model_resp = await openai_client.chat.completions.create(
                model=REPO_LLM, messages=stream
                )
            ai_summary = model_resp.choices[0].message.content
            logging.info(f"Repo {url} ai summary:\n{ai_summary}")
            # rm summary to avoid growing context for next iter
            stream.pop()

            ui_resp = format_results(
                db_result=meta_dict,
                model_summary=ai_summary,
                )
            ui_resps.append(ui_resp)

        repo_results = "***".join(ui_resps)
        summary_prompt = format_meta_prompt(
            usr_prompt=usr_prompt, res=repo_results
            )        
        meta_resp = await openai_client.chat.completions.create(
                model=META_LLM,
                messages=[
                    system_prompt,
                    {"role": "user", "content": summary_prompt},
                    ]
            )
        summ_resp = meta_resp.choices[0].message.content
        response = (
            f"**Outcome:** {summ_resp}\n***" +
            f"\n**Results:**\n{repo_results}"
        )
        await chat.append_message(response)

app = App(app_ui, server, static_assets=app_dir / "www")
