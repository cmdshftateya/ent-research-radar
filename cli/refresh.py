import typer

from backend.app.ingest import refresh_all, seed_sample_data

app = typer.Typer(help="ENT Research data refresh tools.")


@app.command("refresh")
def refresh():
    """
    Run full data refresh (scrape + enrich).
    """
    refresh_all()
    typer.echo("Refresh complete.")


@app.command("seed-sample")
def seed_sample():
    """
    Load sample data to exercise the API/UI without scraping.
    """
    seed_sample_data()
    typer.echo("Sample data inserted.")


if __name__ == "__main__":
    app()
