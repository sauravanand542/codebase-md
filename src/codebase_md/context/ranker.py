"""Ranker — relevance scoring for context chunks against a query.

Scores each ContextChunk's relevance to a given text query using
multi-signal scoring: exact keyword matching, tag overlap, topic
affinity, term frequency weighting, and base priority.
"""

from __future__ import annotations

import math
import re
from collections import Counter

from pydantic import BaseModel, ConfigDict, Field

from codebase_md.context.chunker import ContextChunk


class RankingError(Exception):
    """Raised when relevance ranking fails."""


class ScoredChunk(BaseModel):
    """A context chunk with its computed relevance score.

    Attributes:
        chunk: The original ContextChunk.
        score: Combined relevance score (higher = more relevant).
        matched_terms: Query terms that matched this chunk.
        signal_scores: Breakdown of individual signal contributions.
    """

    model_config = ConfigDict(frozen=True)

    chunk: ContextChunk = Field(description="The scored context chunk")
    score: float = Field(default=0.0, description="Combined relevance score")
    matched_terms: list[str] = Field(
        default_factory=list,
        description="Query terms that matched",
    )
    signal_scores: dict[str, float] = Field(
        default_factory=dict,
        description="Breakdown: signal_name → score contribution",
    )


# ---------------------------------------------------------------------------
# Scoring weights — tune these to adjust ranking behavior
# ---------------------------------------------------------------------------

_WEIGHT_TAG_MATCH = 3.0
_WEIGHT_CONTENT_MATCH = 1.5
_WEIGHT_TITLE_MATCH = 2.5
_WEIGHT_TOPIC_MATCH = 2.0
_WEIGHT_PRIORITY = 1.0
_WEIGHT_TERM_FREQUENCY = 0.5


# Words too common to be useful for matching
_STOP_WORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "shall",
        "can",
        "to",
        "of",
        "in",
        "for",
        "on",
        "with",
        "at",
        "by",
        "from",
        "as",
        "into",
        "about",
        "between",
        "through",
        "after",
        "before",
        "above",
        "below",
        "up",
        "down",
        "out",
        "off",
        "over",
        "under",
        "again",
        "further",
        "then",
        "once",
        "here",
        "there",
        "when",
        "where",
        "why",
        "how",
        "all",
        "each",
        "every",
        "both",
        "few",
        "more",
        "most",
        "other",
        "some",
        "such",
        "no",
        "not",
        "only",
        "own",
        "same",
        "so",
        "than",
        "too",
        "very",
        "just",
        "because",
        "but",
        "and",
        "or",
        "if",
        "while",
        "that",
        "this",
        "what",
        "which",
        "who",
        "whom",
        "its",
        "it",
        "i",
        "me",
        "my",
        "we",
        "our",
        "you",
        "your",
        "he",
        "she",
        "they",
        "them",
        "his",
        "her",
    }
)


def rank_chunks(
    query: str,
    chunks: list[ContextChunk],
) -> list[ScoredChunk]:
    """Score and rank context chunks by relevance to a query.

    Uses multiple signals to produce a combined relevance score:
    1. Tag match — query terms found in chunk tags (high weight)
    2. Title match — query terms in chunk title (high weight)
    3. Topic match — query terms matching chunk topic (medium weight)
    4. Content match — query terms found in chunk content (medium weight)
    5. Term frequency — TF-IDF-inspired weighting for content matches
    6. Priority — chunk's base priority as a tiebreaker

    Results are sorted by score descending.

    Args:
        query: The search query string.
        chunks: List of ContextChunks to score.

    Returns:
        List of ScoredChunk instances, sorted by score (highest first).

    Raises:
        RankingError: If ranking fails.
    """
    if not query.strip():
        raise RankingError("Query cannot be empty")

    if not chunks:
        return []

    try:
        query_terms = _tokenize_query(query)
        if not query_terms:
            # If all query words are stop words, use the full lowered query
            query_terms = [query.strip().lower()]

        # Compute IDF for each term across all chunks
        idf_scores = _compute_idf(query_terms, chunks)

        scored: list[ScoredChunk] = []
        for chunk in chunks:
            score, matched, signals = _score_chunk(
                query_terms,
                chunk,
                idf_scores,
            )
            scored.append(
                ScoredChunk(
                    chunk=chunk,
                    score=round(score, 4),
                    matched_terms=matched,
                    signal_scores={k: round(v, 4) for k, v in signals.items()},
                )
            )

        # Sort by score descending, then by priority descending as tiebreaker
        scored.sort(key=lambda s: (s.score, s.chunk.priority), reverse=True)
        return scored
    except RankingError:
        raise
    except Exception as e:
        raise RankingError(f"Failed to rank chunks: {e}") from e


def _tokenize_query(query: str) -> list[str]:
    """Tokenize a query string into meaningful terms.

    Lowercases, splits on non-alphanumeric characters, removes stop words,
    and deduplicates while preserving order.

    Args:
        query: The raw query string.

    Returns:
        List of unique, meaningful query terms.
    """
    # Split on non-alphanumeric characters (keep underscores for snake_case)
    raw_tokens = re.split(r"[^a-zA-Z0-9_]+", query.lower())
    seen: set[str] = set()
    terms: list[str] = []
    for token in raw_tokens:
        token = token.strip("_")
        if token and token not in _STOP_WORDS and token not in seen:
            seen.add(token)
            terms.append(token)
    return terms


def _compute_idf(
    terms: list[str],
    chunks: list[ContextChunk],
) -> dict[str, float]:
    """Compute inverse document frequency for query terms.

    Terms that appear in fewer chunks get higher IDF scores,
    boosting rare-but-relevant matches.

    Args:
        terms: Query terms to compute IDF for.
        chunks: All available chunks.

    Returns:
        Dictionary mapping term → IDF score.
    """
    n = len(chunks)
    idf: dict[str, float] = {}

    for term in terms:
        doc_count = 0
        for chunk in chunks:
            content_lower = chunk.content.lower()
            tags_str = " ".join(chunk.tags)
            if term in content_lower or term in tags_str:
                doc_count += 1
        # Standard IDF: log(N / (1 + df)) to avoid division by zero
        idf[term] = math.log(n / (1 + doc_count)) + 1.0

    return idf


def _score_chunk(
    query_terms: list[str],
    chunk: ContextChunk,
    idf_scores: dict[str, float],
) -> tuple[float, list[str], dict[str, float]]:
    """Compute the relevance score for a single chunk.

    Args:
        query_terms: Tokenized query terms.
        chunk: The chunk to score.
        idf_scores: Precomputed IDF scores for query terms.

    Returns:
        Tuple of (total_score, matched_terms, signal_breakdown).
    """
    signals: dict[str, float] = {}
    matched_terms: list[str] = []

    content_lower = chunk.content.lower()
    title_lower = chunk.title.lower()
    topic_lower = chunk.topic.value.lower()
    tags_set = set(chunk.tags)

    # --- Signal 1: Tag match ---
    tag_score = 0.0
    for term in query_terms:
        if term in tags_set:
            tag_score += 1.0
            if term not in matched_terms:
                matched_terms.append(term)
    if tags_set:
        tag_score = tag_score / max(len(query_terms), 1)
    signals["tag_match"] = tag_score * _WEIGHT_TAG_MATCH

    # --- Signal 2: Title match ---
    title_score = 0.0
    for term in query_terms:
        if term in title_lower:
            title_score += 1.0
            if term not in matched_terms:
                matched_terms.append(term)
    title_score = title_score / max(len(query_terms), 1)
    signals["title_match"] = title_score * _WEIGHT_TITLE_MATCH

    # --- Signal 3: Topic match ---
    topic_score = 0.0
    for term in query_terms:
        if term in topic_lower:
            topic_score += 1.0
            if term not in matched_terms:
                matched_terms.append(term)
    topic_score = topic_score / max(len(query_terms), 1)
    signals["topic_match"] = topic_score * _WEIGHT_TOPIC_MATCH

    # --- Signal 4: Content match ---
    content_score = 0.0
    for term in query_terms:
        if term in content_lower:
            content_score += 1.0
            if term not in matched_terms:
                matched_terms.append(term)
    content_score = content_score / max(len(query_terms), 1)
    signals["content_match"] = content_score * _WEIGHT_CONTENT_MATCH

    # --- Signal 5: Term frequency (TF-IDF inspired) ---
    tf_score = 0.0
    if content_lower:
        content_words = Counter(re.split(r"[^a-zA-Z0-9_]+", content_lower))
        for term in query_terms:
            tf = content_words.get(term, 0)
            idf = idf_scores.get(term, 1.0)
            tf_score += tf * idf
        # Normalize by content length to avoid bias toward longer chunks
        total_words = sum(content_words.values()) or 1
        tf_score = tf_score / math.sqrt(total_words)
    signals["term_frequency"] = tf_score * _WEIGHT_TERM_FREQUENCY

    # --- Signal 6: Base priority ---
    signals["priority"] = chunk.priority * _WEIGHT_PRIORITY

    # Combine all signals
    total_score = sum(signals.values())

    return total_score, matched_terms, signals
