"""Embeddings de phrases (all-MiniLM-L6-v2), chargés à la demande et partagés."""

from __future__ import annotations

from functools import lru_cache
from typing import Protocol

import numpy as np

MODELE_MINILM = "sentence-transformers/all-MiniLM-L6-v2"


class Encodeur(Protocol):
    """Tout objet qui transforme des textes en vecteurs normalisés (n, d)."""

    def encode(self, textes: list[str]) -> np.ndarray: ...


class MiniLM:
    """Enveloppe de sentence-transformers ; le modèle (~90 Mo) est téléchargé une fois."""

    def __init__(self, nom: str = MODELE_MINILM, longueur_max: int = 128) -> None:
        from sentence_transformers import SentenceTransformer

        self._modele = SentenceTransformer(nom, device="cpu")
        self._modele.max_seq_length = longueur_max

    def mots(self) -> frozenset[str]:
        """Mots anglais entiers du tokenizer (~21 700) : sert de dictionnaire à la correction."""
        vocab = self._modele.tokenizer.get_vocab()
        return frozenset(w for w in vocab if w.isalpha() and w.isascii())

    def encode(self, textes: list[str]) -> np.ndarray:
        vecteurs = self._modele.encode(
            textes, batch_size=64, normalize_embeddings=True, show_progress_bar=False
        )
        return np.asarray(vecteurs, dtype=np.float32)


@lru_cache(maxsize=2)
def charger_encodeur(nom: str = MODELE_MINILM) -> Encodeur:
    return MiniLM(nom)
