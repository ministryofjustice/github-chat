import datetime
import logging
from pathlib import Path
import re

import chromadb
import dotenv
from nomic import embed, login
import openai
from pyprojroot import here
from shiny import App, ui

from scripts.constants import SUMMARY_PROMPT, SYS_PROMPT, WELCOME_MSG
from scripts.moderations import check_moderation
from scripts.custom_components import (
    feedback_tab, more_info_tab, numeric_inputs
)
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
    ui.panel_title("MoJ GitHub Chat"),
    ui.div(
        ui.img(
            src="moJxlogo.png",
            width="100rem",
            style="padding-left:0.2rem;padding-top:0.6rem;float:left;",
            alt="MoJx Logo",
            ),

        ui.h1(
            "Chat With our GitHub Repositories",
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
            # unpack all numeric inputs from custom_components
            *numeric_inputs,
            bg="#f0e3ff"
            ),  
        ui.navset_tab(
            ui.nav_panel(
                f"Chat with {META_LLM}",
                ui.chat_ui(id="chat", placeholder="Enter some keywords"),
            ),
            # custom ui components:
            more_info_tab(),
            feedback_tab(),
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
        logging.info("Moderating prompt =================================")
        flagged_prompt = await check_moderation(
            prompt=usr_prompt, openai_client=openai_client
            )
        logging.info(f"Moderation outcome: {flagged_prompt}")
        if flagged_prompt != usr_prompt:
            await chat.append_message({
                "role": "assistant",
                "content": ("Your message may violate OpenAI's usage "
                f"policy, categories: {flagged_prompt}. Please rephrase "
                "your input and try again."),
            })
            logging.info("Discarding moderated prompt ===================")
            logging.info(f"Discarded prompt: {usr_prompt}")
            del usr_prompt
        else:
            # prompt has passed moderation, embed with nomic Atlas
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
            logging.info("Vector Store queried ==========================")
            logging.info(f"Search results: {results}")
            logging.info("Filtering results =============================")
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

                logging.info(
                    f"Available metas:\n{results['metadatas'][0][ind]}"
                )
                upd_at = results["metadatas"][0][ind].get("updated_at")
                dt_object = datetime.datetime.fromtimestamp(upd_at)

                days_ago = (current_time - dt_object).days
                formatted_date = dt_object.strftime(
                    "%A, %d %B, %Y at %H:%M"
                )
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
                # AI summaries
                model_resp = await openai_client.chat.completions.create(
                    model=REPO_LLM,
                    messages=stream,
                    max_completion_tokens=input.max_tokens(),
                    presence_penalty=input.pres_pen(),
                    temperature=input.temp(),
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
            #  Meta summary
            meta_resp = await openai_client.chat.completions.create(
                    model=META_LLM,
                    messages=[
                        system_prompt,
                        {"role": "user", "content": summary_prompt},
                        ],
                    max_completion_tokens=input.max_tokens(),
                    presence_penalty=input.pres_pen(),
                    temperature=input.temp(),
                )
            summ_resp = meta_resp.choices[0].message.content
            response = (
                f"**Outcome:** {summ_resp}\n***" +
                f"\n**Results:**\n{repo_results}"
            )
            await chat.append_message(response)

app = App(app_ui, server, static_assets=app_dir / "www")
