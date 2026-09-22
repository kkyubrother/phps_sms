class SMSError(Exception):
    """Invalid input, transport failure, or an unreadable service response."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message
        self.text = message  # PhpsSMS compatibility
