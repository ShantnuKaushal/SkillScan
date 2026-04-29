import csv
from pathlib import Path


def create_deterministic_sample(
    source_path: Path,
    output_path: Path,
    limit: int,
    include_terms: list[str] | None = None,
) -> int:
    if limit <= 0:
        raise ValueError("Sample limit must be greater than zero.")

    source = Path(source_path)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with source.open(newline="", encoding="utf-8") as source_handle:
        reader = csv.DictReader(source_handle)
        if reader.fieldnames is None:
            raise ValueError(f"{source} does not contain a CSV header.")

        with output.open("w", newline="", encoding="utf-8") as output_handle:
            writer = csv.DictWriter(output_handle, fieldnames=reader.fieldnames)
            writer.writeheader()

            written = 0
            normalized_terms = [term.casefold() for term in include_terms or [] if term.strip()]
            for row in reader:
                if normalized_terms and not _row_contains_any_term(row, normalized_terms):
                    continue
                writer.writerow(row)
                written += 1
                if written >= limit:
                    break

    return written


def _row_contains_any_term(row: dict[str, str], terms: list[str]) -> bool:
    searchable = " ".join(
        [
            row.get("title", ""),
            row.get("description", ""),
            row.get("skills_desc", ""),
            row.get("company_name", ""),
        ]
    ).casefold()
    return any(term in searchable for term in terms)
