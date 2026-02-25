""" """

from __future__ import annotations

from typing import TYPE_CHECKING

from conda.common.io import dashlist
from conda.exceptions import CondaError

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any


class LockfileFormatNotSupported(CondaError):
    def __init__(self, path: str):
        message = f"The specified file {path} is not supported."
        super().__init__(message)


class ExportLockfileFormatNotSupported(CondaError):
    def __init__(self, lockfile_format: str):
        message = f"Exporting to lockfile format {lockfile_format} is not supported."
        super().__init__(message)


class EnvironmentExportNotSupported(CondaError):
    def __init__(self, lockfile_format: str, addendum: str | None = None):
        message = (
            "The specified environment cannot be exporting "
            f"to lockfile format {lockfile_format}."
        )
        addendum = f" {addendum.strip()}" if addendum else ""
        super().__init__(message + addendum)


def format_validation_errors(errors: list[dict[str, Any]], file_path: Path) -> str:
    """
    Format Pydantic validation errors into user-friendly messages.

    :param errors: List of error dicts from ValidationError.errors()
    :param file_path: Path to the file being validated
    :return: Formatted error message string
    """

    def format_location(loc: tuple) -> str:
        """Convert Pydantic location tuple to readable field path."""
        return ".".join(str(item) for item in loc)

    error_messages = []
    for error in errors:
        loc = error.get("loc", ())
        msg = error.get("msg", "validation failed")
        error_type = error.get("type", "")

        # Create concise error description based on error type
        if loc:
            field_path = format_location(loc)
            if error_type == "missing":
                description = f"missing required field '{field_path}'"
            elif "value_error" in error_type or "assertion_error" in error_type:
                # Custom validator errors - use the message directly
                description = msg
            else:
                description = f"field '{field_path}': {msg}"
        else:
            description = msg

        error_messages.append(description)

    # Format the final message
    if len(error_messages) == 1:
        return error_messages[0]
    else:
        formatted_list = dashlist(error_messages)
        return f"File {file_path} has validation errors:\n{formatted_list}"
