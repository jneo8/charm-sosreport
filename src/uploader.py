"""Collections of different upload methods."""

import logging
import socket
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, List, Optional

import paramiko
from paramiko.sftp_client import SFTPClient

logger = logging.getLogger(__name__)

AVAILABLE_METHODS = {"sftp", "scp", "http"}


class UnknownUploaderError(Exception):
    """Unknown uploader exception."""


class Uploader(ABC):  # pylint: disable=too-few-public-methods
    """Base class for any uploader."""

    @abstractmethod
    def upload(self, files: Any) -> bool:
        """Upload the report to the server."""


class SftpUploader(Uploader):  # pylint: disable=too-few-public-methods
    """A concrete sftp uploader class."""

    def __init__(self, server: str, username: str, password: str):
        """Initialize the sftp uploader class."""
        self.server = server
        self.username = username
        self.password = password
        self.client = paramiko.Transport((server, 22))

    def upload(self, files: List[str]) -> bool:
        """Upload sos reports to the sftp server."""
        success = True
        sftp = self._start_sftp_session()
        if not sftp:
            logger.error("Failed to open sftp client. Check juju debug-log for more details.")
            return False

        for file in files:
            # If the file name begins with 'sosreport-', STS-API will add a
            # comment to SF case. Rename the file from sos-collector* to
            # sosreport*
            localpath = Path(file)
            remotepath = localpath.parent / localpath.name.replace("sos-collector", "sosreport", 1)
            success = self._upload_file(str(localpath), str(remotepath), sftp)
        sftp.close()
        return success

    def _start_sftp_session(self) -> Optional[SFTPClient]:
        if not self.client.is_active():
            self.client.connect(username=self.username, password=self.password)
        return self.client.open_sftp_client()

    def _upload_file(self, localpath: str, remotepath: str, sftp: SFTPClient) -> bool:
        try:
            logger.info("uploading local file '%s' to sftp server '%s'.", localpath, remotepath)
            sftp.put(localpath, remotepath)
            return True
        except (socket.error, paramiko.ssh_exception.AuthenticationException) as error:
            logger.error(str(error))
            return False


def create_uploader(upload_method: str, **kwargs: Any) -> Uploader:
    """Create a uploader based on the upload method and kwargs."""
    uploader = None
    if upload_method == "sftp":
        server = kwargs.get("server", "")
        username = kwargs.get("username", "")
        password = kwargs.get("password", "")
        uploader = SftpUploader(server, username, password)
    elif upload_method == "scp":
        raise UnknownUploaderError(
            f"'{upload_method}' is not supported. "
            f"Supported upload methods are {AVAILABLE_METHODS}"
        )
    elif upload_method == "http":
        raise NotImplementedError(
            f"'{upload_method}' is not implemented. "
            f"Supported upload methods are {AVAILABLE_METHODS}"
        )
    else:
        raise NotImplementedError(
            f"'{upload_method}' is not implemented. "
            f"Supported upload methods are {AVAILABLE_METHODS}"
        )
    return uploader
