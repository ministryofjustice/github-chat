"""Ingest repo metadata & summarise with pipeline_config.REPO_LLM"""
import datetime
from time import sleep

from ai_nexus_backend.github_api import GithubClient
import dotenv
import openai
import pandas as pd
from pyprojroot import here
from requests import HTTPError

from scripts.pipeline_config import REPO_LLM
from scripts.prompts import REPO_SUMMARY_PROMPT, REPO_SUMMARY_SYS_PROMPT
from scripts.string_utils import sanitise_string

def ingest():

    # configure -----------------------------------------------------------
    secrets = dotenv.dotenv_values(here(".env"))
    github_pat = secrets["GITHUB_PAT"]
    user_agent = secrets["AGENT"]
    org_nms = [secrets["ORG_NM1"], secrets["ORG_NM2"]]
    openai_key = secrets["OPENAI_KEY"]

    github_client = GithubClient(
        github_pat=github_pat, user_agent=user_agent)

    # get repo lists ------------------------------------------------------
    org1 = github_client.get_org_repos(org_nms[0], public_only=True)
    org2 = github_client.get_org_repos(org_nms[1], public_only=True)

    # append the topics from each repo ------------------------------------
    topics1 = github_client.get_all_repo_metadata(
        html_urls=org1["html_url"],
        metadata="topics",
    )
    topics2 = github_client.get_all_repo_metadata(
        html_urls=org2["html_url"],
        metadata="topics",
    )
    
    # munge tables --------------------------------------------------------
    repo_metadata = pd.concat([org1, org2], ignore_index=True)
    all_topics = pd.concat([topics1, topics2], ignore_index=True)
    # README: there's inconsistency in column labelling here, need to look
    # into it in ainexus_backend:
    # https://github.com/ministryofjustice/rd-service-catalogue/issues/35
    all_topics.set_index("repo_url", inplace=True)
    repo_metadata.set_index("html_url", inplace=True, drop=False)
    repo_metadata = repo_metadata.join(all_topics)

    # ingest READMEs ------------------------------------------------------
    readmes = []
    for i, row in repo_metadata.iterrows():
        html_url = row["html_url"]
        try:
            print(f"Ingest README.md for {html_url}")
            readme = github_client.get_readme_content(html_url)
            readmes.append(readme)
        except HTTPError as e:
            print(f"repo {html_url} returned an error:\n{e}")
            readmes.append("None")

    repo_metadata["readme"] = readmes

    # AI summarises repos -------------------------------------------------
    openai_client = openai.OpenAI(api_key=openai_key)
    system_prompt = {
        "role": "system",
        "content": REPO_SUMMARY_SYS_PROMPT.replace("\n", " ").replace("  ", "")
    }
    stream = [system_prompt]

    ai_summaries = []
    for i, row in repo_metadata.iterrows():
                repo_deets = f"""
                Name: {row['name']},\n
                url: {row['html_url']},\n
                Description: {row['description']},\n
                Is Private: {row['is_private']},\n
                Is Archived: {row['is_archived']},\n
                Programming Language: {row['programming_language']},\n
                Topics: {row['topics']},\n
                README: {row['readme']}

                """
                repo_content = {
                "role": "user",
                "content": sanitise_string(REPO_SUMMARY_PROMPT.format(repo_deets=repo_deets))
                }
                stream.append(repo_content)
                model_resp = openai_client.chat.completions.create(
                    model=REPO_LLM,
                    messages=stream,
                    temperature=0.0,
                )
                ai_summary = model_resp.choices[0].message.content
                # rm summary to avoid growing context for next iter
                stream.pop()
                ai_summaries.append(ai_summary)
                sleep(0.3)

    repo_metadata["ai_summary"] = ai_summaries


    # write to parquet ----------------------------------------------------
    now = datetime.datetime.today().isoformat().replace(":", "_")
    filenm = f"repo-metadata-{now}.parquet"
    repo_metadata.to_parquet(here(f"data/{filenm}"))

if __name__ == "__main__":
    ingest()
