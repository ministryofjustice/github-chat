from pyprojroot import here

COLLECTION_NM = "moj-github"
EMBEDDINGS_MODEL = "nomic-embed-text"
LLM = "llama3.2:1b" # 1Gb
# LLM = "llama3.2:3b" # 2Gb - better but slower...
VECTOR_STORE_PTH = here("data/nomic-embeddings")
TEMP = 1.0
