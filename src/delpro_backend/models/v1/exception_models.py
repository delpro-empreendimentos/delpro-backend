"""Class to store all application exceptions."""


class ResourceNotFoundError(Exception):
    """Raised when a requested resource is not found in the database."""

    def __init__(self, resource_type: str, resource_id: str):
        """Initialize the exception.

        Args:
            resource_type: Type of resource (e.g., "Document", "Chunk")
            resource_id: ID of the resource that was not found
        """
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(f"{resource_type} with ID '{resource_id}' not found")


class DocumentProcessingError(Exception):
    """Raised when document processing fails."""

    def __init__(self, document_id: str, reason: str):
        """Initialize the exception.

        Args:
            document_id: ID of the document that failed processing
            reason: Reason for the failure
        """
        self.document_id = document_id
        self.reason = reason
        super().__init__(f"Failed to process document '{document_id}': {reason}")


class WebhookValidationError(Exception):
    """Error while valitaing webhook."""

    pass


class InvalidWhatsappMessageError(Exception):
    """Invalid whatsapp message error."""

    pass


class DuplicatedWhatsappRequestError(Exception):
    """Duplicated whatsapp request."""

    pass


# Request Errors


class MissingParametersRequestError(Exception):
    """Raised when the request does not contain all parameters needded."""

    pass


class InvalidRequestError(Exception):
    """Raised when a request is invalid."""

    pass
