# `GitHub Chat` Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Added input selectors for model temperature, presence penalty and maximum
tokens.

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
