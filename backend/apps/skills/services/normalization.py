from __future__ import annotations

from dataclasses import dataclass
import re

from apps.skills.services.spacy_extractor import SpacySkillExtractor


DEFAULT_SKILL_ALIASES: dict[str, tuple[str, ...]] = {
    "AWS": ("aws", "amazon web services"),
    "Apache Kafka": ("apache kafka", "kafka"),
    "Django": ("django", "django rest framework", "django rest api", "django rest apis", "drf", "django rest"),
    "Docker": (
        "docker",
        "containers",
        "containerization",
        "containerized deployments",
        "containerized deployment",
        "containerized applications",
    ),
    "Elasticsearch": ("elasticsearch", "elastic search", "elastic"),
    "FastAPI": ("fastapi", "fast api"),
    "GraphQL": ("graphql", "graph ql"),
    "JavaScript": ("javascript", "ecmascript"),
    "Kubernetes": ("kubernetes", "k8s"),
    "Neo4j": ("neo4j", "neo 4j", "cypher"),
    "Next.js": ("next.js", "nextjs", "next js"),
    "Node.js": ("node.js", "nodejs", "node js"),
    "Pandas": ("pandas",),
    "PostgreSQL": ("postgresql", "postgres", "postgre sql"),
    "Python": ("python", "python3"),
    "React": ("react", "react.js", "reactjs"),
    "Redis": ("redis",),
    "SQL": ("sql",),
    "spaCy": ("spacy", "spa cy"),
    "TypeScript": ("typescript", "ts"),
}


@dataclass(frozen=True)
class SkillMatch:
    canonical: str
    original: str
    start: int
    end: int


class SkillNormalizer:
    def __init__(self, aliases: dict[str, tuple[str, ...]] | None = None) -> None:
        self.aliases = aliases or DEFAULT_SKILL_ALIASES
        self.extractor = SpacySkillExtractor(self.aliases)
        self._lookup: dict[str, str] = {}
        for canonical, variants in self.aliases.items():
            self._lookup[_normalize_key(canonical)] = canonical
            for variant in variants:
                self._lookup[_normalize_key(variant)] = canonical

        escaped_phrases = sorted(
            (re.escape(alias) for alias in self._lookup.keys()),
            key=len,
            reverse=True,
        )
        self._pattern = re.compile(
            r"(?<![A-Za-z0-9])(" + "|".join(escaped_phrases) + r")(?![A-Za-z0-9])",
            re.IGNORECASE,
        )

    def normalize_term(self, term: str) -> str | None:
        return self._lookup.get(_normalize_key(term))

    def extract_skills(self, text: str | None) -> list[SkillMatch]:
        if not text:
            return []

        matches_by_canonical: dict[str, SkillMatch] = {
            item.canonical: SkillMatch(
                canonical=item.canonical,
                original=item.original,
                start=item.start,
                end=item.end,
            )
            for item in self.extractor.extract(text)
        }
        for match in self._pattern.finditer(text):
            original = match.group(0)
            canonical = self.normalize_term(original)
            if canonical is None or canonical in matches_by_canonical:
                continue
            matches_by_canonical[canonical] = SkillMatch(
                canonical=canonical,
                original=original,
                start=match.start(),
                end=match.end(),
            )

        return sorted(matches_by_canonical.values(), key=lambda item: item.start)


def _normalize_key(value: str) -> str:
    value = value.strip().casefold()
    value = value.replace("+", " plus ")
    value = re.sub(r"[\s._/-]+", " ", value)
    return value.strip()
