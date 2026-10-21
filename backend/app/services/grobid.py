from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

import httpx


@dataclass(slots=True)
class ParsedSection:
    heading: str | None
    section_type: str | None
    paragraphs: list[tuple[str, int | None]]


class GrobidError(RuntimeError):
    pass


class GrobidClient:
    def __init__(self, base_url: str, timeout: int = 180) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def process(self, pdf_path: Path) -> bytes:
        try:
            with pdf_path.open("rb") as pdf:
                response = httpx.post(
                    f"{self.base_url}/api/processFulltextDocument",
                    files={"input": (pdf_path.name, pdf, "application/pdf")},
                    data={"consolidateHeader": "1", "consolidateCitations": "0"},
                    timeout=self.timeout,
                )
            response.raise_for_status()
        except (OSError, httpx.HTTPError) as exc:
            raise GrobidError(f"GROBID processing failed: {exc}") from exc
        return response.content


def _text(element: ET.Element | None) -> str:
    return " ".join("".join(element.itertext()).split()) if element is not None else ""


def parse_tei(tei_xml: bytes) -> list[ParsedSection]:
    """Extract section-aware paragraphs and best-effort page markers from TEI."""
    try:
        root = ET.fromstring(tei_xml)
    except ET.ParseError as exc:
        raise GrobidError(f"Malformed TEI from GROBID: {exc}") from exc

    ns = {"tei": "http://www.tei-c.org/ns/1.0"}
    sections: list[ParsedSection] = []

    abstract = root.find(".//tei:profileDesc/tei:abstract", ns)
    if abstract is not None and _text(abstract):
        sections.append(ParsedSection("Abstract", "abstract", [(_text(abstract), None)]))

    for div in root.findall(".//tei:text/tei:body/tei:div", ns):
        head = _text(div.find("tei:head", ns)) or None
        section_type = div.attrib.get("type", "body")
        paragraphs: list[tuple[str, int | None]] = []
        current_page: int | None = None
        for child in div.iter():
            local_name = child.tag.rsplit("}", 1)[-1]
            if local_name == "pb":
                with suppress(ValueError):
                    current_page = int(child.attrib.get("n", ""))
            elif local_name in {"p", "figDesc"}:
                value = _text(child)
                if value:
                    paragraphs.append((value, current_page))
        if paragraphs:
            sections.append(ParsedSection(head, section_type, paragraphs))

    references = root.findall(".//tei:text/tei:back//tei:biblStruct", ns)
    reference_text = [_text(reference) for reference in references if _text(reference)]
    if reference_text:
        sections.append(
            ParsedSection("References", "references", [(item, None) for item in reference_text])
        )
    return sections
