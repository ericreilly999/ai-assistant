from __future__ import annotations

from assistant_app.models import DocumentReference


class GoogleDriveAdapter:
    key = "google_drive"
    display_name = "Google Drive"
    capabilities = ["documents.read"]

    def list_mock_documents(self) -> list[DocumentReference]:
        return [
            DocumentReference(
                id="gdoc-1",
                title="Architecture Review Notes",
                source=self.key,
                mime_type="application/vnd.google-apps.document",
                web_view_link="https://drive.google.com/file/d/gdoc-1/view",
            )
        ]

    def normalize_file(self, payload: dict) -> DocumentReference:
        return DocumentReference(
            id=payload["id"],
            title=payload.get("name", "Untitled document"),
            source=self.key,
            mime_type=payload.get("mimeType", "application/octet-stream"),
            web_view_link=payload.get("webViewLink", ""),
        )
