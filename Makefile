.PHONY: ingest-data

ingest-data:
	python3 pipeline/01_ingest_data.py
	python3 pipeline/02_create_vector_store.py
	