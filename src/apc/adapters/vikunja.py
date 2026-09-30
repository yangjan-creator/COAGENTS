"""Adapter seam for Vikunja's REST API; no direct database access."""

from apc.adapters.base import AdapterError, ExternalWorkItem


class VikunjaAdapter:
    provider = "vikunja"

    def __init__(self, base_url: str, api_token: str):
        self.base_url, self.api_token = base_url.rstrip("/"), api_token

    def pull_work_item(self, remote_id: str) -> ExternalWorkItem:
        raise AdapterError("Map Vikunja projects/tasks before pulling")

    def publish_status(self, remote_id: str, status: str, note: str) -> None:
        raise AdapterError("Outbound sync requires explicit project mapping")
