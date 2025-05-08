""" """

from conda.exceptions import CondaError


class LockfileFormatNotSupported(CondaError):
    def __init__(self, path: str):
        message = f"The specified file {path} is not supported."
        super().__init__(message)


class ExportLockfileFormatNotSupported(CondaError):
    def __init__(self, lockfile_format: str):
        message = f"Exporting to lockfile format {lockfile_format} is not supported."
        super().__init__(message)
