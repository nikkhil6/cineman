# Helper for loading the GEMINI_API_KEY from Secret Manager at runtime.
# Usage:
#   - Add "import cineman.secret_helper as secret_helper; secret_helper.inject_gemini_key()" 
#     at the top of your application startup (before AI chain initialization)
#
# This helper:
#  - returns the value for local development from the GEMINI_API_KEY env var (if present)
#  - otherwise reads the secret named by GEMINI_SECRET_NAME in the project GCP_PROJECT
#  - sets os.environ['GEMINI_API_KEY'] so existing code that expects the env var will work
#  - logs errors rather than crashing (so app can choose to degrade functionality)

from google.cloud import secretmanager
import os
import logging

_logger = logging.getLogger(__name__)

def get_secret_from_manager(project_id: str, secret_name: str) -> str:
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("utf-8")

def load_gemini_key(project_id: str = None, secret_name: str = None) -> str | None:
    """
    Return GEMINI API key. Priority:
      1) GEMINI_API_KEY environment variable (local/dev fallback)
      2) Secret Manager secret identified by (project_id, secret_name)
    If it fails to retrieve from Secret Manager, returns None and logs the error.
    """
    # 1) env var fallback for local dev
    env_val = os.environ.get("GEMINI_API_KEY")
    if env_val:
        _logger.debug("Using GEMINI_API_KEY from environment (local/dev fallback).")
        return env_val

    # 2) get project and secret name from env variables set in app.yaml
    project_id = project_id or os.environ.get("GCP_PROJECT")
    secret_name = secret_name or os.environ.get("GEMINI_SECRET_NAME", "gemini-api-key")

    if not project_id or not secret_name:
        _logger.error("GCP_PROJECT or GEMINI_SECRET_NAME not set and no GEMINI_API_KEY env var found.")
        return None

    # Check if we are running in a likely GCP environment or have credentials
    # to avoid hanging/crashing on local machines without GCP creds.
    is_gcp = os.environ.get("GAE_ENV") or os.environ.get("CLOUD_RUN_SERVICE") or os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not is_gcp and not os.environ.get("ENABLE_GCP_SECRETS"):
        _logger.warning("Not running in GCP and ENABLE_GCP_SECRETS not set. Skipping Secret Manager lookup.")
        return None

    try:
        key = get_secret_from_manager(project_id, secret_name)
        _logger.info("Loaded GEMINI_API_KEY from Secret Manager.")
        return key
    except Exception as e:
        _logger.exception("Failed to load GEMINI_API_KEY from Secret Manager: %s", e)
        return None

def inject_gemini_key(project_id: str = None, secret_name: str = None) -> bool:
    """
    Ensure os.environ['GEMINI_API_KEY'] is set.
    Returns True if the key was set (from env or Secret Manager), False otherwise.
    """
    if os.environ.get("GEMINI_API_KEY"):
        return True

    key = load_gemini_key(project_id=project_id, secret_name=secret_name)
    if key:
        os.environ["GEMINI_API_KEY"] = key
        # Optionally clear 'key' from local variable (best effort)
        return True

    return False