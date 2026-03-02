"""
FileProvider abstraction — swap storage backend via FILE_PROVIDER env var.

Current:  local  (./uploaded_files)
Future:   azure_blob  / sharepoint / webdav
"""
from abc import ABC, abstractmethod
from pathlib import Path
from app.config import settings


class FileProvider(ABC):
    @abstractmethod
    async def save(self, file_id: str, filename: str, content: bytes) -> None:
        ...

    @abstractmethod
    async def load(self, file_id: str) -> bytes:
        ...

    @abstractmethod
    async def delete(self, file_id: str) -> None:
        ...


class LocalFileProvider(FileProvider):
    def __init__(self) -> None:
        self._base = Path(settings.local_files_dir)
        self._base.mkdir(parents=True, exist_ok=True)

    def _path(self, file_id: str) -> Path:
        # sanitize: allow only the UUID portion before any path separator
        return self._base / Path(file_id).name

    async def save(self, file_id: str, filename: str, content: bytes) -> None:
        self._path(file_id).write_bytes(content)

    async def load(self, file_id: str) -> bytes:
        p = self._path(file_id)
        if not p.exists():
            raise FileNotFoundError(file_id)
        return p.read_bytes()

    async def delete(self, file_id: str) -> None:
        p = self._path(file_id)
        if p.exists():
            p.unlink()


# ─── Factory ──────────────────────────────────────────────────────────────────

_instance: FileProvider | None = None

def get_file_provider() -> FileProvider:
    global _instance
    if _instance is None:
        prov = settings.file_provider
        if prov == "local":
            _instance = LocalFileProvider()
        # elif prov == "azure_blob":
        #     from app.services.file_provider_azure import AzureBlobProvider
        #     _instance = AzureBlobProvider()
        # elif prov == "sharepoint":
        #     from app.services.file_provider_sharepoint import SharePointProvider
        #     _instance = SharePointProvider()
        else:
            raise ValueError(f"Unknown FILE_PROVIDER: {prov!r}")
    return _instance
