"""Retrieval benchmark for medsim: are the retrieved documents relevant, useful, and correct?

Steps (each writes JSONL under one workspace directory and resumes where it stopped):
extract -> redact -> run -> judge -> validate -> report. See bench/README.md.
"""
