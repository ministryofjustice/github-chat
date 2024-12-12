import logging
from pathlib import Path
import re

import chromadb
import ollama
from pyprojroot import here
from shiny import App, ui

from scripts.constants import SUMMARY_PROMPT, WELCOME_MSG
from scripts.modelfile import create_model
from scripts.pipeline_config import (
    EMBEDDINGS_MODEL,
    LLM,
    VECTOR_STORE_PTH,
)
from scripts.string_utils import (
    format_results,
    format_meta_prompt,
    get_vintage_from_str,
    sanitise_string,
)

# Before ==================================================================
app_dir = Path(__file__).parent
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(here("logs/app.log"))],
    )

stream = list()
stream.append({"role": "assistant", "content": WELCOME_MSG})

nm_pat = re.compile(r"Name:\s*([^,]+)", re.IGNORECASE)
url_pat = re.compile(r"url:\s*([^,]+)", re.IGNORECASE)
desc_pat = re.compile(r"Description: (.*?)(?=\sREADME:)", re.IGNORECASE)
readme_pat = re.compile(r"README: (.*?)([^']+)", re.IGNORECASE)

resp = ollama.list()
found_models = [mod["model"] for mod in resp["models"]]
for mod in [EMBEDDINGS_MODEL, LLM]:
    if mod not in found_models:
        ollama.pull(mod)

# default prompt
create_model()

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
    ),
    ui.include_css(app_dir / "www/styles.css"),
    ui.h1("RAG with MoJ GitHub"),
    ui.markdown(
        """Code repositories in ministryofjustice and
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
                max=1.0,
                step=0.1,
                ),
            bg="#f0e3ff"
            ),  
        ui.navset_tab(
            ui.nav_panel(f"Chat with {LLM}", ui.chat_ui(id="chat", placeholder="Enter some keywords", ),),
            ui.nav_panel(
                "More details",
                ui.h2("Citations", {"style": "font-size:25px;"}),
                ui.markdown("* Embeddings storage with <a href=https://docs.trychroma.com/ target='_blank'>Chromadb</a>, an open-source vector store. Embeddings were created with the default normalised <a href='https://docs.trychroma.com/guides#changing-the-distance-function' target='_blank'>Root Mean Squared Error function</a>."),
                ui.markdown("* Local LLMs handled with <a href=https://ollama.com/ target='_blank'>ollama</a>."),
                ui.markdown("* Embeddings calculated with <a href=https://www.nomic.ai/blog/posts/nomic-embed-text-v1 target='_blank'>nomic-embed-text</a>, an open-source embeddings model with a comparable context window to leading edge proprietary embeddings models."),
                ui.markdown(f"* Retrieval model {LLM} from Meta's Open Source <a href=https://www.llama.com/ target='_blank'>Llama series</a>."),
                ui.hr(),
                ui.h2("Known Issues", {"style": "font-size:25px;"}),
                ui.markdown("* Queries are slow, even with the most performant Meta `llama3.2:1b` model. This is due to design decisions in an effort to mitigate hallucinations. To reduce wait time, reduce the value of n Results."),
                ui.markdown("* Repos in the `moj-analytical-platform` may mistakenly show repo descriptions and README content as 'None'. This is likely to be a flaw in the ingestion process regarding GitHub API credentials rather than LLM hallucinations."),
                ui.markdown("* Queries such as 'machine learning' tend to produce results with higher relevance than queries like 'Are there any repos about machine learning?'. At a cost to performance, I would like to explore using an LLM for entity extraction of search keywords in the user's query, by using the <a href='https://dottxt-ai.github.io/outlines/latest/welcome/' target='_blank'>Python `outlines` library</a>."),
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
        # Get the user's input
        usr_prompt = sanitise_string(chat.user_input())
        logging.info("User submitted prompt =============================")
        logging.info(f"Santised user input: {usr_prompt}")
        query_embeddings = ollama.embed(
            model=EMBEDDINGS_MODEL, input=f"search_query: {usr_prompt}")
        results = collection.query(
            query_embeddings=query_embeddings.embeddings, n_results=input.selected_n())
        # filter out any results that are above the distance threshold
        logging.info("Vector Store queried ==============================")
        logging.info(f"Search results: {results}")
        logging.info("Filtering results =================================")
        rem_inds = [i for i, dist in enumerate(results["distances"][0]) if dist > input.dist_thresh()]
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
            meta_dict = {
                "repo_nm": nm[0] if nm else None,
                "html_url": url[0] if url else None,
                "repo_desc": desc[0] if desc else None,
                "distance": dist, 
            }

            repo_content = {
                "role": "user",
                "content": SUMMARY_PROMPT.format(repo_deets=res)
                }
            stream.append(repo_content)
            model_resp = ollama.chat(
                model=LLM,
                messages=stream,
            )
            ai_summary = model_resp["message"]["content"]
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
        meta_resp = ollama.chat(
            model=LLM,
            messages=[{"role": "user", "content": summary_prompt}]
            )
        response = f"**Outcome:** {meta_resp['message']['content']}\n***\n**Results:**\n{repo_results}"
        await chat.append_message(response)

app = App(app_ui, server, static_assets=app_dir / "www")
# app = App(app_ui, server)
