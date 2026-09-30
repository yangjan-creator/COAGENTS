"""External PM adapters never touch an upstream database directly."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ExternalWorkItem:
    provider: str
    remote_id: str
    title: str
    status: str
    parent_remote_id: str | None
    url: str | None
    raw: dict


class ProjectAdapter(Protocol):
    provider: str

    def pull_work_item(self, remote_id: str) -> ExternalWorkItem: ...

    def publish_status(self, remote_id: str, status: str, note: str) -> None: ...


class AdapterError(RuntimeError):
    pass
