"""The policy wording and the claims manual, section by section."""

import re

from fastapi import APIRouter, HTTPException

from backend.models import Section, SectionHeading
from backend.seed import DATA

router = APIRouter(prefix="/api/documents")

DOCUMENTS = {"policy_wording": "policy_wording.md", "claims_manual": "claims_manual.md"}
TOPIC = re.compile(r"^(?:- )?\*\*(.+?)[.:]\*\*", re.MULTILINE)


def sections(document: str) -> list[Section]:
    """Split a document into its numbered sections, or raise 404."""
    if document not in DOCUMENTS:
        raise HTTPException(404, f"Document {document} not found")
    text = (DATA / DOCUMENTS[document]).read_text(encoding="utf-8")
    found = []
    for part in text.split("\n## ")[1:]:
        heading, _, body = part.partition("\n")
        number, _, title = heading.partition(". ")
        found.append(
            Section(
                document=document, section=int(number), title=title, text=body.strip()
            )
        )
    return found


@router.get("/{document}/sections", operation_id="list_sections")
def list_sections(document: str) -> list[SectionHeading]:
    """List a document's numbered sections with the topics in each."""
    return [
        SectionHeading(section=s.section, title=s.title, topics=TOPIC.findall(s.text))
        for s in sections(document)
    ]


@router.get("/{document}/sections/{section}", operation_id="read_section")
def read_section(document: str, section: int) -> Section:
    """Read one numbered section of a document."""
    for found in sections(document):
        if found.section == section:
            return found
    raise HTTPException(404, f"Section {section} of {document} not found")
