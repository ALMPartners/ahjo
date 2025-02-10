import logging
import re


class DatabaseFormatter(logging.Formatter):
    """Formatter for database logging."""

    def __init__(self):
        """Constructor for DatabaseFormatter class."""
        super().__init__()

    def format(self, record):
        """Format the log record.

        Arguments:
        -----------
        record (LogRecord):
            The log record to be formatted.

        Returns:
        -----------
        str:
            The formatted log record.
        """

        message = record.getMessage()

        if hasattr(record, "module") and record.module == "operation_manager":

            # remove timestamp from the start of message
            if len(message) > 20 and message.startswith("[") and message[20] == "]":
                return re.sub(r"^([\[]).*?([\]])", "", str(message)).lstrip()

        if hasattr(record, "record_class") and record.record_class == "deployment":
            # return f"File {message} deploy completed"
            return f"Deployment of {message} completed"

        return message
