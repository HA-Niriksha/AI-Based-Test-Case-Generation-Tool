import os
from dotenv import load_dotenv

load_dotenv()

# No API key. No LLM endpoint. Fully offline.
ENGINE = "rule-based-nlp"
VERSION = "1.0.0"

SPACY_MODEL = os.getenv("SPACY_MODEL", "en_core_web_sm")
CHUNK_SIZE_WORDS = int(os.getenv("CHUNK_SIZE_WORDS", "1500"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
DEDUP_THRESHOLD = float(os.getenv("DEDUP_THRESHOLD", "0.85"))
