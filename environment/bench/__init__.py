"""Retrieval benchmark for medsim: are its literature answers correct and consistent with the case?

Steps (each writes JSONL under one workspace directory and resumes where it stopped):
extract -> redact -> run -> judge -> validate -> report. See bench/README.md.
"""
