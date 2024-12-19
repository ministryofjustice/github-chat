import argparse
import datetime as dt
import glob
import re

from ai_nexus_backend.github_api import GithubClient
import chromadb 
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
import dotenv
import ollama
import pandas as pd
from pyprojroot import here
from requests import HTTPError
import tiktoken

from scripts.pipeline_config import EMBEDDINGS_MODEL
from scripts.string_utils import sanitise_string


def embed():

    # Define the argument parser
    parser = argparse.ArgumentParser(description="Process some integers.")
    parser.add_argument(
        "--est_cost",
        action="store_true",
        help="Estimate the cost of embedding the documents"
        )

    # Parse the arguments
    args = parser.parse_args()
    # pull embeddings model if needed
    ollama.pull(EMBEDDINGS_MODEL)

    # bring in the latest version of the data only
    latest_pth = max(glob.glob(str(here("data/*.parquet"))))
    latest_dat = pd.read_parquet(latest_pth)
    # get the vintage in order to label the collection later
    date_pat = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}_\d{2}_\d{2}.\d{6}")
    match = date_pat.search(latest_pth)
    vintage = match[0] 
    # format documents for embedding & storage. chromadb IDs must be string
    ids = latest_dat["id"].astype(str).to_list() 
    metas = []
    documents = []
    target_metas = [
        "is_private",
        "is_archived",
        "programming_language",
        "updated_at",
        "org_nm"
        ]
    for i, row in latest_dat.iterrows():
        ts = dt.datetime.strptime(
            row["updated_at"], "%Y-%m-%dT%H:%M:%SZ"
        ).timestamp()
        # metadata must be str, int, float or bool, will not tolerate None             
        metas.append(
            {
                "is_private": bool(row["is_private"]),
                "is_archived": bool(row["is_archived"]),
                "programming_language": str(row["programming_language"]),
                "updated_at": ts,
                "org_nm": row["org_nm"],
            }
        )
        documents.append(
            sanitise_string(
                f"""
                search_document: 
                Name: {row['name']},\n
                url: {row['html_url']},\n
                Description: {row['description']},\n
                README: {row['readme']},\n
                AI Summary: {row['ai_summary']}

                """
            ))

    documents = [
        doc.replace("\n", " ").replace("  ", "").strip() for doc in documents
        ]

    # Estimate cost =======================================================
    if args.est_cost:

        # Load the encoder for the OpenAI text-embedding-3-small model
        enc = tiktoken.encoding_for_model("text-embedding-3-small")
        # Encode each text in documents and calculate the total tokens
        total_tokens = sum(len(enc.encode(text)) for text in documents)

        cost_per_1M_tokens = 0.02
        # Display number of tokens and cost
        print("Total tokens:", total_tokens)
        print(
            "Cost:",
            cost_per_1M_tokens * total_tokens / 1_000_000,
            "dollars")

    # Calculate embeddings ================================================

    ollama_response = ollama.embed(model=EMBEDDINGS_MODEL, input=documents)

    # Vector store ========================================================
    chroma_client = chromadb.PersistentClient(
        path=str(here("data/nomic-embeddings")),
        settings=chromadb.config.Settings(allow_reset=True),
        )
    chroma_client.reset()
    collection = chroma_client.create_collection(
        name=f"moj-github-{vintage}")
    collection.add(
        ids=ids,
        metadatas=metas,
        documents=[
            doc.replace("search_document: ", "") for doc in documents
            ],
        embeddings=ollama_response.embeddings
        )
    collection.peek()


if __name__ == "__main__":
    embed()
