from src.utils.security.credentials import CredentialError, get_credential


def validate_required_credentials():
    """Validate all required credentials are available on startup."""
    required_credentials = [
        "OPENAI_API_KEY",
        "OPENROUTER_API_KEY",
        "API_SECRET_KEY",
        "SUPABASE_URL",
        "SUPABASE_KEY",
        "SUPABASE_DB_URL",
        # Add all other required credentials
    ]

    missing = []
    for cred in required_credentials:
        try:
            get_credential(cred)
        except CredentialError:
            missing.append(cred)

    if missing:
        raise RuntimeError(
            f"Missing required credentials: {
                ', '.join(missing)}")
