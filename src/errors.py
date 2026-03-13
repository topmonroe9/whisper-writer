class MissingApiKeyError(Exception):
    """Raised when a required API key is not configured."""
    def __init__(self, provider: str):
        self.provider = provider
        super().__init__(f"API key for {provider} is not configured. Please add it in Settings.")
