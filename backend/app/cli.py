from datetime import UTC, datetime

import typer
from sqlalchemy import select

from app.config import get_settings
from app.database import SessionLocal
from app.models import Author, Paper, Tag
from app.services.zotero import ZoteroError, sync_zotero

app = typer.Typer(help="PaperMind administration commands")


@app.command("zotero-sync")
def zotero_sync() -> None:
    """Incrementally synchronize the configured Zotero library."""
    with SessionLocal() as db:
        try:
            result = sync_zotero(db, get_settings())
        except ZoteroError as exc:
            typer.echo(f"Sync failed: {exc}", err=True)
            raise typer.Exit(1) from exc
    typer.echo(result.model_dump_json(indent=2))


@app.command("seed-demo")
def seed_demo() -> None:
    """Create public-domain metadata-only examples for UI development."""
    examples = [
        (
            "Attention Is All You Need",
            "Ashish",
            "Vaswani",
            2017,
            "Advances in Neural Information Processing Systems",
        ),
        (
            "Deep Residual Learning for Image Recognition",
            "Kaiming",
            "He",
            2016,
            "CVPR",
        ),
        (
            "BERT: Pre-training of Deep Bidirectional Transformers",
            "Jacob",
            "Devlin",
            2019,
            "NAACL",
        ),
    ]
    with SessionLocal() as db:
        demo_tag = db.scalar(select(Tag).where(Tag.name == "demo")) or Tag(name="demo")
        db.add(demo_tag)
        for title, first, last, year, journal in examples:
            if db.scalar(select(Paper).where(Paper.title == title)):
                continue
            normalized = f"{first} {last}".casefold()
            author = db.scalar(select(Author).where(Author.normalized_name == normalized))
            author = author or Author(first_name=first, last_name=last, normalized_name=normalized)
            db.add(
                Paper(
                    title=title,
                    publication_year=year,
                    journal=journal,
                    authors=[author],
                    tags=[demo_tag],
                    date_added=datetime.now(UTC),
                )
            )
        db.commit()
    typer.echo("Demo metadata created. Upload your own PDFs from a paper page.")


if __name__ == "__main__":
    app()
