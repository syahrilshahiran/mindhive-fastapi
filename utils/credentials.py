import os
import tempfile


def load_credentials():
    """Load credentials from environment variable (as string)"""
    if "GOOGLE_APPLICATION_CREDENTIALS_JSON" in os.environ:
        creds_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
        creds_path = tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".json")
        creds_path.write(creds_json)
        creds_path.close()
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path.name
