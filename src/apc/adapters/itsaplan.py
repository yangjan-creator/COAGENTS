"""Adapter seam for It's a Plan REST/OpenAPI and webhook events."""

from apc.adapters.base import AdapterError, ExternalWorkItem


class ItsAPlanAdapter:
    provider = "itsaplan"

    def __init__(self, base_url: str, api_key: str):
        self.base_url, self.api_key = base_url.rstrip("/"), api_key

    def pull_work_item(self, remote_id: str) -> ExternalWorkItem:
        raise AdapterError("Bind this adapter to a tested upstream OpenAPI version during connector setup")

    def publish_status(self, remote_id: str, status: str, note: str) -> None:
        raise AdapterError("Outbound sync requires explicit project mapping")
