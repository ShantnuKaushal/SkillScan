from __future__ import annotations

from dataclasses import dataclass

import spacy
from spacy.matcher import PhraseMatcher
from spacy.tokens import Doc


@dataclass(frozen=True)
class ExtractedPhrase:
    canonical: str
    original: str
    start: int
    end: int


class SpacySkillExtractor:
    def __init__(self, aliases: dict[str, tuple[str, ...]]) -> None:
        self.nlp = spacy.blank("en")
        self.matcher = PhraseMatcher(self.nlp.vocab, attr="LOWER")
        self._label_to_canonical: dict[str, str] = {}

        for canonical, variants in aliases.items():
            label = self._label_for(canonical)
            self._label_to_canonical[label] = canonical
            phrases = tuple(dict.fromkeys((canonical, *variants)))
            patterns = [self.nlp.make_doc(phrase) for phrase in phrases if phrase.strip()]
            if patterns:
                self.matcher.add(label, patterns)

    def extract(self, text: str | None) -> list[ExtractedPhrase]:
        if not text:
            return []

        doc = self.nlp(text)
        matches_by_canonical: dict[str, ExtractedPhrase] = {}
        for label, start, end in self._dedupe_overlapping_matches(doc):
            canonical = self._label_to_canonical[self.nlp.vocab.strings[label]]
            span = doc[start:end]
            candidate = ExtractedPhrase(
                canonical=canonical,
                original=span.text,
                start=span.start_char,
                end=span.end_char,
            )
            current = matches_by_canonical.get(canonical)
            if current is None or _is_better_candidate(candidate, current):
                matches_by_canonical[canonical] = candidate

        return sorted(matches_by_canonical.values(), key=lambda item: item.start)

    def _dedupe_overlapping_matches(self, doc: Doc) -> list[tuple[int, int, int]]:
        raw_matches = list(self.matcher(doc))
        raw_matches.sort(key=lambda item: (item[1], -(item[2] - item[1])))
        accepted: list[tuple[int, int, int]] = []
        occupied_tokens: set[int] = set()
        for label, start, end in raw_matches:
            token_range = set(range(start, end))
            if occupied_tokens.intersection(token_range):
                continue
            accepted.append((label, start, end))
            occupied_tokens.update(token_range)
        return accepted

    @staticmethod
    def _label_for(canonical: str) -> str:
        normalized = "".join(character if character.isalnum() else "_" for character in canonical.upper())
        return f"SKILL_{normalized}"


def _is_better_candidate(candidate: ExtractedPhrase, current: ExtractedPhrase) -> bool:
    if candidate.start != current.start:
        return candidate.start < current.start
    return len(candidate.original) > len(current.original)
