import logging
import logging.config


class ColoredFormatter(logging.Formatter):
    """Custom formatter to add colors to log messages."""

    COLORS = {
        "DEBUG": "\033[94m",  # Blue
        "INFO_DEFAULT": "\033[97m",  # White (default INFO)
        "INFO_HEADER": "\033[1;36m",  # Blue
        "INFO_SUCCESS": "\033[92m",  # Green
        "WARNING": "\033[93m",  # Yellow
        "ERROR": "\033[91m",  # Red
        "CRITICAL": "\033[95m",  # Magenta
        "RESET": "\033[0m",  # Reset color
    }

    def format(self, record):
        """Format the log record with color."""
        if record.levelname == "INFO":
            color_key = f"INFO_{getattr(record, 'info_type', 'DEFAULT').upper()}"
            color = self.COLORS.get(
                color_key, self.COLORS["INFO_DEFAULT"]
            )  # Default to white
        else:
            color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        message = super().format(record)
        return f"{color}{message}{self.COLORS['RESET']}"


class ConsoleFormatterFactory:
    """Factory class for creating console formatters."""

    @staticmethod
    def get_colored_formatter(fmt=None, datefmt=None, style="%"):
        return ColoredFormatter(fmt, datefmt, style)
