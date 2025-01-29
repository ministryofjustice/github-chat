import datetime as dt
import io
import json
import logging
from pathlib import Path

import dotenv
import openai
import pandas as pd
from pyprojroot import here
from shiny import App, reactive, render, ui

from scripts.app_config import APP_LLM
from scripts.chat_utils import _init_stream
from scripts.chroma_utils import ChromaDBPipeline
from scripts.icons import question_circle
from scripts.custom_tools import ExtractKeywordEntities, ExportDataToTSV, toolbox
from scripts.moderations import check_moderation
from scripts.custom_components import (
    feedback_tab, more_info_tab, inputs_with_popovers
)
from scripts.string_utils import sanitise_string

# Before ==================================================================
EXPORT_FILENM = "export.tsv"
secrets = dotenv.dotenv_values(here(".env"))
app_dir = Path(__file__).parent
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(here("logs/app.log"))],
    )
stream = []
_init_stream(_stream=stream)

openai_client = openai.OpenAI(api_key=secrets["OPENAI_KEY"])
chroma_pipeline = ChromaDBPipeline()
chroma_pipeline.get_data_vintage()
vintage = chroma_pipeline.data_vintage

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
            "Model Parameters",

            ui.popover(
                ui.span(
                    question_circle,
                    style="position: relative; bottom: 28px; left: 185px; z-index: 1;",

                ),
                """
                Re-initialises the chat stream to the system prompt and
                welcome message.""",
                placement="top",
                id="clear_chat_popover",

            ),

            ui.input_action_button(
                id="flush_chat",
                label="Clear Chat",
                style="position: relative; bottom: 60px;",
            ),
            ui.span(
            *inputs_with_popovers,
            style="position: relative; bottom: 80px;",
            ),
            ui.popover(
                ui.span(
                    question_circle,
                    style="position: relative; bottom: 68px; left: 185px; z-index: 1;",

                ),
                """
                Exports the results of your repo searches to file. Will
                refuse if you have not asked for any repo details. You can
                also ask the model to do this for you by typing in the
                chat.""",
                placement="top",
                id="download_button_popover",

            ),
            ui.download_button("download_df", "Download Table", class_="btn-primary", style="position: relative; bottom: 100px;",),
            ui.tags.script(
                    """
                    Shiny.addCustomMessageHandler("clickButton", function(id) {
                        document.getElementById(id)?.click();
                    });
                    """
                ),

            bg="#f0e3ff"
            ), 
        ui.navset_tab(
            ui.nav_panel(
                f"Chat with {APP_LLM}",
                ui.chat_ui(
                    id="chat",
                    format="openai"
                ),
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
        messages=stream,
        tokenizer=None
    )


    @reactive.Effect
    @reactive.event(input.flush_chat)
    async def clear_chats():
        """Erase all user & assistant response content from chat stream"""
        # wipe to sys & welcome msg only
        _init_stream(_stream=stream)
        await chat.clear_messages()
        await chat.append_message(stream[-1]) 


    @chat.on_user_submit
    async def respond():
        """A callback to run when the user submits a message."""
        sanitised_prompt = sanitise_string(chat.user_input())
        logging.info("User submitted prompt =============================")
        logging.info(f"Santised user input: {sanitised_prompt}")
        logging.info("Moderating prompt =================================")
        flagged_prompt = await check_moderation(
            prompt=sanitised_prompt, openai_client=openai_client
            )
        logging.info(f"Moderation outcome: {flagged_prompt}")
        if flagged_prompt != sanitised_prompt:
            await chat.append_message({
                "role": "assistant",
                "content": ("Your message may violate OpenAI's usage "
                f"policy, categories: {flagged_prompt}. Please rephrase "
                "your input and try again."),
            })
            logging.info("Discarding moderated prompt ===================")
            logging.info(f"Discarded prompt: {sanitised_prompt}")
            del sanitised_prompt
        else:
            # prompt has passed moderation
            stream.append({"role": "user", "content": sanitised_prompt})
            #  Meta summary -----------------------------------------------
            completions_params = {
                "model": APP_LLM,
                "messages": stream,
                "stream": False,
                "tools": toolbox,
                "max_completion_tokens": input.max_tokens(),
                "presence_penalty": input.pres_pen(),
                "frequency_penalty": input.freq_pen(),
                "temperature": input.temp(),
            }
            response = openai_client.chat.completions.create(
                **completions_params
            )
            # implement conditional flow dependent upon whether a tool call
            # is asked for
            resp = response.choices[0]
            if (refusal := resp.message.refusal):
                sanitised_refusal = sanitise_string(refusal)
                await chat.append_message(sanitised_refusal)
                stream.append(
                    {"role": "assistant", "content": sanitised_refusal}
                    )
            elif (msg := resp.message.content):
                sanitised_msg = sanitise_string(msg)
                await chat.append_message(sanitised_msg)
                stream.append(
                    {"role": "assistant", "content": sanitised_msg}
                    )
            elif (tool_call := resp.message.tool_calls):
                function_name = tool_call[0].function.name
                arguments = tool_call[0].function.arguments
                sanitised_func_nm = sanitise_string(function_name)
                if sanitised_func_nm == "ExtractKeywordEntities":
                    sanitised_args = [
                        sanitise_string(arg) for arg in
                        json.loads(arguments)["keywords"]
                    ]
                    # Pydantic will raise if keywords violate schema rules
                    extracted_terms = ExtractKeywordEntities(
                        keywords=sanitised_args
                        )
                    ui.notification_show(
                        ("Searching database for keywords:"
                        f" {', '.join(extracted_terms.keywords)}")
                        )
                    summarise_this = chroma_pipeline.execute_pipeline(
                        keywords=extracted_terms.keywords,
                        n_results=input.selected_n(),
                        distance_threshold=input.dist_thresh(),
                        sanitised_prompt=sanitised_prompt
                    )
                    if (n_removed := chroma_pipeline.total_removed) > 0:
                        ui.notification_show(
                            f"{n_removed} results were removed."
                            )
                    if len(chroma_pipeline.results) == 0:
                        ui.notification_show(
                            "No results shown, increase distance threshold"
                            )
                    stream.append(summarise_this)
                    response = openai_client.chat.completions.create(
                        **completions_params
                        )
                    meta_resp = {
                        "role": "assistant",
                        "content": response.choices[0].message.content
                        }
                    await chat.append_message(response)
                    await chat.append_message(
                        {
                            "role": "asisstant",
                            "content": chroma_pipeline.chat_ui_results
                            })
                    stream.append(meta_resp)

                elif sanitised_func_nm == "ExportDataToTSV":
                    dat = chroma_pipeline.export_table
                    if len(dat) == 0:
                        await chat.append_message(
                            "No results found, please ask for repos first"
                        )
                    else:
                        ui.notification_show("Exporting data...")
                        sanitised_filenm = sanitise_string(json.loads(arguments)["filename"]).replace(" ", "")
                        # pydantic will raise if doesn't conform to spec
                        filenm = ExportDataToTSV(filename=sanitised_filenm)
                        await session.send_custom_message(
                            "clickButton", "download_df"
                            )
                        await chat.append_message(
                            f"Please check your downloads for file {EXPORT_FILENM}"
                        )
                    

    def reset_chat():
        """Call this when session is flushed to wipe messages to scratch"""
        _init_stream(_stream=stream)


    @render.download(filename=EXPORT_FILENM)
    def download_df():
        """Output current export table to tsv"""
        df = chroma_pipeline.export_table
        with io.StringIO() as buf:
            df.to_csv(buf, sep="\t", index=False)
            yield buf.getvalue()


    session.on_flush(reset_chat, once=False)

app = App(app_ui, server, static_assets=app_dir / "www")
