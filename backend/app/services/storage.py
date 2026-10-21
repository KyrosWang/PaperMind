import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO


class StorageBackend(ABC):
    @abstractmethod
    def save_file(self, relative_path: str, source: BinaryIO) -> str: ...

    @abstractmethod
    def open_file(self, relative_path: str) -> BinaryIO: ...

    @abstractmethod
    def delete_file(self, relative_path: str) -> None: ...

    @abstractmethod
    def exists(self, relative_path: str) -> bool: ...

    @abstractmethod
    def absolute_path(self, relative_path: str) -> Path: ...


class LocalFilesystemStorage(StorageBackend):
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, relative_path: str) -> Path:
        candidate = (self.root / relative_path).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise ValueError("Storage path escapes DATA_ROOT")
        return candidate

    def save_file(self, relative_path: str, source: BinaryIO) -> str:
        destination = self._resolve(relative_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as output:
            shutil.copyfileobj(source, output)
        return relative_path

    def open_file(self, relative_path: str) -> BinaryIO:
        return self._resolve(relative_path).open("rb")

    def delete_file(self, relative_path: str) -> None:
        self._resolve(relative_path).unlink(missing_ok=True)

    def exists(self, relative_path: str) -> bool:
        return self._resolve(relative_path).is_file()

    def absolute_path(self, relative_path: str) -> Path:
        return self._resolve(relative_path)
