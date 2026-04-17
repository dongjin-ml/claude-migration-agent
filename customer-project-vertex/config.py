"""
Vertex AI backend configuration.
Loads Vertex env vars from this project's .env and re-exports them for the app.
The migration scanner must detect the Vertex backend from BOTH the .env file and
this module, and the fixer must leave every value below untouched.
"""

import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

VERTEX_PROJECT_ID = os.environ["ANTHROPIC_VERTEX_PROJECT_ID"]
VERTEX_REGION = os.environ["CLOUD_ML_REGION"]
VERTEX_BASE_URL = os.environ["ANTHROPIC_VERTEX_BASE_URL"]

# Ensure ADC picks up the service account if provided.
os.environ.setdefault(
    "GOOGLE_APPLICATION_CREDENTIALS",
    os.getenv("GOOGLE_APPLICATION_CREDENTIALS", ""),
)
