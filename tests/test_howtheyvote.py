import gzip
from pathlib import Path

from transparent_scrape.sources import howtheyvote


def test_rebellion_stats_from_fixture(tmp_path: Path) -> None:
    src = Path(__file__).parent / "fixtures" / "htv_member_votes.csv"
    gz = tmp_path / "member_votes.csv.gz"
    with gzip.open(gz, "wt", encoding="utf-8") as handle:
        handle.write(src.read_text(encoding="utf-8"))

    stats = howtheyvote.compute_rebellion_stats(gz)
    assert stats["12"]["rebel_votes"] == 1
    assert stats["11"]["rebel_votes"] == 1
    assert stats["10"]["rebel_votes"] == 0
