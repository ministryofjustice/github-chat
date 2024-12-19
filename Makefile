.PHONY: ingest-data

ingest-data:
	python3 -m scripts.01_ingest_data
	python3 -m scripts.02_create_vector_store
	