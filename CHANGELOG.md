# `GitHub Chat` Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Clear chat button wipes messages.
- Chat is re-initialised when the session is flushed on page refresh.

### Changed

- System prompt uses few shot to improve entity extraction of keywords in
cases where prompt contains multiple keywords.

## [0.2.1] - 2025-01-20

### Changed

- Total results are filtered to the value selected in "n results", when
prompts with multiple extracted key terms would return more than this
value.

## [0.2.0] - 2025-01-15

### Added

- Model has access to a tool for extracting keywords from user prompts.
- Model is able to initiate vector store query with keyword entities
extracted from user prompts.
- Database queried for as many keywords as supplied by user.
- Deduplication in event of identical results retrieved for different
search terms.
- Retrieved results combined and sorted on distance.

### Changed

- Nomic embeddings & chroma query & retrieval abstracted to
`scripts.chroma_utils.ChromaDBPipeline`.

### Removed

- Streaming capability in order to implement function calling for entity
extraction, allowing a more conversational tone with the chatbot.

## [0.1.0] - 2024-12-20

### Added

- A switch component to UI that allows user to ask for streamed model 
responses.
- Server logic to conditionally return streamed model responses, improving
time to first token.

### Changed

- AI Repo sumaries are no longer requested within the application runtime, 
they are generated during the data ingestion phase and stored within the
vector store.

## [0.0.3] - 2024-12-18

### Added

- Added input selectors for model temperature, presence penalty, frequency
penalty and maximum tokens.
- A maximum value of 1.5 was applied to the temperature parameter to
mitigate non-UTF-8 tokens and extremely slow responses.

## [0.0.2] - 2024-12-16

### Added

- App uses openai moderations endpoint to ensure user prompts are compliant
with openai usage policies.

### Changed

- Tabset navigation is sticky with user scroll.
- Include additional metadata in results.
- Summary of results with chatgpt-4o-latest.
- AI repo summaries done with gpt-4o-mini.
- Prompts updated:
    - Reduce behaviour of asking for further user input.
    - Influence model confidence with regards to README length.
- User query embeddings calculated with [Nomic Atlas](https://docs.nomic.ai/)
- Distance threshold selector max increased to 2.0

## [0.0.1] - 2024-12-12

### Added

- Script to ingest repo metadata with GitHub developer Rest API.
- Script to create Chromadb vector store.
- Model handling with Ollama.
- Embeddings with [Nomic Embed](https://www.nomic.ai/blog/posts/nomic-embed-text-v1) .
- Retrieval with [Meta Llama 3.2](https://www.llama.com/).
- UI with n_results selector, distance threshold selector and chat components.
- MoJ-x styling applied
