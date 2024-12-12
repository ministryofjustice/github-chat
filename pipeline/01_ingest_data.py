import datetime

from ai_nexus_backend.github_api import GithubClient
import dotenv
import pandas as pd
from pyprojroot import here

def ingest():

    # configure -----------------------------------------------------------

    secrets = dotenv.dotenv_values(here(".env"))
    github_pat = secrets["GITHUB_PAT"]
    user_agent = secrets["AGENT"]
    org_nms = [secrets["ORG_NM1"], secrets["ORG_NM2"]]

    github_client = GithubClient(
        github_pat=github_pat, user_agent=user_agent)

    # get repo lists ------------------------------------------------------

    org1 = github_client.get_org_repos(org_nms[0])
    org2 = github_client.get_org_repos(org_nms[1])

    # append the topics from each repo ------------------------------------

    topics1 = github_client.get_all_org_repo_metadata(
        metadata="topics",
        repo_nms=org1["name"],
        org_nm=org_nms[0],
    )
    topics2 = github_client.get_all_org_repo_metadata(
        metadata="topics",
        repo_nms=org2["name"],
        org_nm=org_nms[1],
    )

    [i for i, nm in enumerate(org2["name"]) if nm == "judicial_demand"]
    org2.reset_index(drop=True).iloc[1325, :]
    # this one is an internal archive

    # munge tables --------------------------------------------------------

    repo_metadata = pd.concat([org1, org2], ignore_index=True)
    all_topics = pd.concat([topics1, topics2], ignore_index=True)
    for tab in [repo_metadata, all_topics]:
        tab.set_index("repo_url", inplace=True)

    out = repo_metadata.join(all_topics)

    # write to parquet ----------------------------------------------------
    now = datetime.datetime.today().isoformat().replace(":", "_")
    filenm = f"repo-metadata-{now}.parquet"
    repo_metadata.to_parquet(here(f"data/{filenm}"))

if __name__ == "__main__":
    ingest()
