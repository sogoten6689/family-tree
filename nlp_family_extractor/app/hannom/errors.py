class HannomApiError(Exception):
    """Raised when Kim Hán Nôm API returns an error or an invalid response."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        api_code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.api_code = api_code
