class CustomError(Exception):
    """Custom exception with an optional message."""

    def __init__(self, status_code=400, detail="Something went wrong"):
        # Initialize the exception with status code and detail message
        self.status_code = status_code
        self.detail = detail
        super().__init__(self.detail)
