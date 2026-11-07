"""Reference correction: source-pattern proofs inspect cited source only.

Narrative remains available for display and other intentional uses. This is
an in-memory intervention, never an installed-package edit.
"""
from contextlib import contextmanager


@contextmanager
def source_only_patterns(selector):
    original = selector.PathFacts.has_source_pattern

    def has_source_pattern(self, refs, pattern):
        matched = []
        for ref in self.direct_refs(refs):
            ev = self.evidence[ref]
            text = self.source.text(str(ev.get('chunk_id') or ''),
                                    int(ev.get('start_line') or 0),
                                    int(ev.get('end_line') or 0))
            if pattern.search(text):
                matched.append(ref)
        return bool(matched), matched

    selector.PathFacts.has_source_pattern = has_source_pattern
    try:
        yield
    finally:
        selector.PathFacts.has_source_pattern = original
