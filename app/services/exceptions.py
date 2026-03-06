class ExternalServiceError(Exception):
    def __init__(self, service: str, message: str, status_code: int = 502):
        super().__init__(message)
        self.service = service
        self.message = message
        self.status_code = status_code

    def to_dict(self) -> dict:
        return {
            "service": self.service,
            "message": self.message,
            "status_code": self.status_code,
        }
