"""Utilities for working with chromadb"""
from collections import OrderedDict
import datetime
from itertools import islice
from pathlib import Path
import re
from typing import List, Union

import chromadb
import dotenv
from nomic import embed, login
import pandas as pd
from pyprojroot import here

from scripts.app_config import EMBEDDINGS_MODEL
from scripts.pipeline_config import VECTOR_STORE_PTH
from scripts.string_utils import (
    format_results,
    format_meta_prompt,
    get_vintage_from_str,
)

secrets = dotenv.dotenv_values(here(".env"))

# results collection begins ===================================

class ChromaDBPipeline:
    """
    A pipeline for interacting with ChromaDB.

    Attributes
    ----------
    nomic_api_key : str
        API key for Nomic.
    vector_store_pth : str
        Path to the vector store.
    client : chromadb.PersistentClient
        Persistent client for ChromaDB.
    nomic_logged_in : bool
        Flag indicating if logged into Nomic.
    chat_ui_results: str
        Formatted db results for presentation in chat UI.
    collection : Optional[chromadb.Collection]
        Current ChromaDB collection.
    collection_nm : Optional[str]
        Name of the current ChromaDB collection.
    data_vintage : Optional[str]
        Data vintage of the current collection.
    embeddings : Optional[dict]
        Embeddings generated from keywords.
    results : Optional[dict]
        Results from querying the collection.
    current_keywords: list
        The list of keywords extracted from the user's latest prompt.
    export_table : pd.DataFrame
        Tabular form of results for export to Excel. This will extend as
        the user makes additional requests.

    Methods
    -------
    embed_keywords(keywords: list, model: str) -> dict
        Embed a list of keywords using the specified model.
    get_latest_chroma_collection() -> None
        Retrieve the latest ChromaDB collection.
    get_data_vintage() -> str
        Get the data vintage from the current collection name.
    query_collection(
        embedded_keywords: Union[dict, None], n_results: int
        ) -> dict
        Query the collection with embedded keywords and return results.
    filter_results(dist_threshold: float) -> OrderedDict
        Filter the query results based on a distance threshold.
    respond_with_db_results(sanitised_prompt: str) -> dict
        Generate a response with database results formatted for user
        interaction.
    _login_nomic() -> None
        Log in to Nomic using the provided API key.
    """

    def __init__(
        self,
        vector_store_pth: Union[str, Path]=VECTOR_STORE_PTH,
        nomic_api_key:str=secrets["NOMIC_KEY"],
        ):
        self.nomic_api_key = nomic_api_key
        self.vector_store_pth = str(vector_store_pth)
        self.client = chromadb.PersistentClient(path=self.vector_store_pth)
        self.nomic_logged_in = False
        self.total_removed = 0
        self.chat_ui_results = None
        self.collection = None
        self.collection_nm = None
        self.data_vintage = None
        self.embeddings = None
        self.results = None
        self.current_keywords = []
        self.export_table = pd.DataFrame()

    def embed_keywords(
        self,
        keywords:list,
        model:str=EMBEDDINGS_MODEL,
        ) -> dict:
        """
        Embed a list of keywords using the specified model.
        This method uses the Nomic Atlas to embed a list of keywords. If
        the user is not logged in to Nomic, it will log in first before
        proceeding with the embedding.

        Parameters
        ----------
        keywords : list
            A list of keywords to be embedded.
        model : str, optional
            The model to use for embedding the keywords. Default is
            EMBEDDINGS_MODEL.
        Returns
        -------
        dict
            A dictionary containing the embeddings of the provided
            keywords.
        """
        self.current_keywords = keywords
        if not self.nomic_logged_in:
            self._login_nomic()
            self.nomic_logged_in = True
        # embed with nomic Atlas
        embeddings = embed.text(
            texts=keywords,
            model=model,
            task_type="search_query",
        )
        self.embeddings = embeddings
        return embeddings

    def get_latest_chroma_collection(self) -> None:
        """
        Retrieve the latest Chroma collection.

        This method fetches the latest Chroma collection by name and
        updates the instance attributes `collection_nm` and `collection`
        with the name and the collection object respectively.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        self.collection_nm = max(self.client.list_collections()).name
        self.collection = self.client.get_collection(
            name=self.collection_nm
            )

    def get_data_vintage(self) -> str:
        """
        Retrieve the data vintage from the collection name.
        This method checks if the `collection_nm` attribute is set. If not,
        it calls `get_latest_chroma_collection()` to set it. Then, it
        extracts the vintage from the `collection_nm` and assigns it to the
        `data_vintage` attribute.

        Returns
        -------
        str
            The vintage extracted from the collection name.
        """
        
        if not self.collection_nm:
            self.get_latest_chroma_collection()
        vintage = get_vintage_from_str(self.collection_nm)
        self.data_vintage = vintage
        return vintage

    def query_collection(
        self,
        embedded_keywords:Union[dict, None]=None,
        n_results:int=3,
        ):
        """
        Query the collection with embedded keywords.

        Parameters
        ----------
        embedded_keywords : Union[dict, None], optional
            A dictionary containing the embedded keywords to query with. If
            None, the default embeddings will be used.
        n_results : int, optional
            The number of results to return from the query. Default is 3.
        Returns
        -------
        results
            The results of the query from the collection.
        """
        
        if not embedded_keywords:
            results = self.collection.query(
                query_embeddings=self.embeddings.get("embeddings"),
                # n_results=input.selected_n()
                n_results=n_results,
                )
        else:
            results = self.collection.query(
                query_embeddings=embedded_keywords.get("embeddings"),
                n_results=n_results,
            )
        self.results = results
        return results
    
    def filter_results(
        self, dist_thresh:float, n_results:int=None,
        ) -> OrderedDict:
        """
        Filters the results based on a distance threshold.

        Parameters
        ----------
        dist_thresh: float
            The distance threshold above which results will be filtered
            out.
        n_results: int
            If an integer is passed, the output will be filtered to this
            number of results. Defaults to None.

        Returns
        -------
        OrderedDict
            An ordered dictionary of filtered results, sorted by
            distance.

        Notes
        -----
        - Results with distances greater than `dist_thresh` are
        removed.
        - The filtered results are sorted by distance for intuitive
        presentation.
        """
        self.total_removed = 0
        filtering = False
        for i, distances in enumerate(
            self.results.get("distances")
            ):
            rem_inds = [
                j for j, dist in enumerate(distances) if dist > dist_thresh
                ]

            if (n_filter := len(rem_inds)) > 0:
                # delete results over selected threshold
                filtering = True
                for k in rem_inds[::-1]:
                    # careful with removing as adjusts index
                    del self.results.get("ids")[i][k]
                    del self.results.get("documents")[i][k]
                    del self.results.get("distances")[i][k]
                    del self.results.get("metadatas")[i][k]
                    self.total_removed += 1  

        # combine documents into a single dict will dedupe the results
        filtered_results = {}

        for i, ids in enumerate(self.results.get("ids")):

            for j, _id in enumerate(ids):
                filtered_results[_id] = {
                    "document": self.results.get("documents")[i][j],
                    "distance": self.results.get("distances")[i][j],
                    "metadata": self.results.get("metadatas")[i][j],
                    }

        # sort on distance for intuitive presentation to user
        sorted_results = OrderedDict(
            sorted(
                filtered_results.items(),
                key=lambda item: item[1].get("distance")
                )
            )
        if n_results:
            filtered_sorted = OrderedDict(
                islice(sorted_results.items(), n_results)
                )
            self.total_removed += (
                len(sorted_results) - len(filtered_sorted)
                )
            self.results = filtered_sorted
            return filtered_sorted
        else:
            self.results = sorted_results
            return sorted_results

    def respond_with_db_results(self, sanitised_prompt:str) -> dict:
        """
        Process database results and format them into a response.

        This method extracts relevant information from the database
        results, formats it, and combines it into a summary prompt.

        Parameters
        ----------
        sanitised_prompt : str
            The sanitised user prompt to be included in the summary.

        Returns
        -------
        dict
            A dictionary containing the role and the formatted summary
            prompt.
        """

        nm_pat = re.compile(r"Name:\s*([^,]+)", re.IGNORECASE)
        url_pat = re.compile(r"url:\s*([^,]+)", re.IGNORECASE)
        desc_pat = re.compile(
            r"Description: (.*?)(?=\sREADME:)", re.IGNORECASE
            )
        readme_pat = re.compile(
            r"README: (.*?)(?=,AI Summary:)", re.IGNORECASE
            )
        aisummary_pat = re.compile(r"AI Summary: (.*)", re.IGNORECASE)
        # for each result, extract properties and inject into template
        ui_resps = []  
        current_time = datetime.datetime.now()
        for k, v in self.results.items():
            doc = v.get("document")
            nm = nm_pat.findall(doc)
            url = url_pat.findall(doc)
            desc = desc_pat.findall(doc)
            readme = readme_pat.findall(doc)
            ai_summary = aisummary_pat.findall(doc)
            dist = v.get("distance")
            metas = v.get("metadata")
            upd_at = metas.get("updated_at")
            dt_object = datetime.datetime.fromtimestamp(upd_at)
            days_ago = (current_time - dt_object).days
            formatted_date = dt_object.strftime(
                "%A, %d %B, %Y at %H:%M"
            )
            date_out = f"{formatted_date} ({days_ago} days ago)."
            meta_dict = {
                "search_terms": ", ".join(self.current_keywords),
                "org_nm": metas.get("org_nm"),
                "repo_nm": nm[0] if nm else None,
                "html_url": url[0] if url else None,
                "repo_desc": desc[0] if desc else None,
                "is_private": metas.get("is_private"),
                "is_archived": metas.get("is_archived"),
                "programming_language": metas.get("programming_language"),
                "updated_at": date_out,
                "distance": dist, 
                "model_summary": ai_summary[0] if ai_summary else None,
            }
            self.export_table = pd.concat(
                [self.export_table, pd.DataFrame(meta_dict, index=[0])],
                ignore_index=True, axis=0,
            )
            ui_resp = format_results(
                db_result=meta_dict,
                )
            ui_resps.append(ui_resp)
        
        self.export_table.reset_index(drop=True, inplace=True)
        repo_results = "***".join(ui_resps)
        self.chat_ui_results = repo_results
        summary_prompt = format_meta_prompt(
            usr_prompt=sanitised_prompt, res=repo_results
            )

        return {"role": "user", "content": summary_prompt.replace("\n", " ").replace("  ", " ")}

    def _login_nomic(self) -> None:
        """
        Logs in to the Nomic API using the provided API key.

        This method uses the `login` function to authenticate with the
        Nomic API using the API key stored in the `nomic_api_key`
        attribute of the class.

        Parameters
        ----------
        None
        Returns
        -------
        None
        """
        login(token=self.nomic_api_key)


    def execute_pipeline(self, keywords:List[str], n_results:int, distance_threshold:float, sanitised_prompt:str) -> str:
        """
        Executes the pipeline methods in the correct order.

        Parameters
        ----------
        keywords : List[str]
            List of keywords to embed.
        distance_threshold : float
            Distance threshold for filtering results.
        sanitised_prompt: str
            Processed user's prompt.

        Returns
        -------
        dict
            The response with summary prompt content formatted with db
            results.
        """
        self._login_nomic()
        self.embed_keywords(keywords)
        self.get_latest_chroma_collection()
        self.get_data_vintage()
        self.query_collection(n_results=n_results)
        self.filter_results(
            dist_thresh=distance_threshold,
            n_results=n_results
            )
        return self.respond_with_db_results(
            sanitised_prompt=sanitised_prompt
            )
