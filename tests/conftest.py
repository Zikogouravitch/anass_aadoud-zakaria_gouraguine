"""Outils partagés : un faux encodeur rapide (sac de mots haché) à la place de MiniLM."""

from __future__ import annotations

import re
import zlib

import numpy as np
import pandas as pd
import pytest

from support_agent.kb import BaseConnaissances
from support_agent.modele import Hyper, ModeleSupport


class FauxEncodeur:
    """Vecteur normalisé de mots hachés : deux textes qui partagent des mots se ressemblent."""

    dim = 256

    def encode(self, textes: list[str]) -> np.ndarray:
        sortie = np.zeros((len(textes), self.dim), dtype=np.float32)
        for i, t in enumerate(textes):
            for m in re.findall(r"[a-z0-9]+", t.lower()):
                sortie[i, zlib.crc32(m.encode()) % self.dim] += 1.0
        normes = np.linalg.norm(sortie, axis=1, keepdims=True)
        return sortie / np.where(normes == 0, 1, normes)


HORS_SUJET = [
    "What is the weather in Paris", "Tell me a joke please", "Book a flight to Rome",
    "Give me a pasta recipe", "Who won the football match", "Play some jazz music",
    "How many calories in an apple", "Set an alarm for 7am",
]


@pytest.fixture(scope="session")
def encodeur() -> FauxEncodeur:
    return FauxEncodeur()


@pytest.fixture(scope="session")
def petit_jeu() -> pd.DataFrame:
    lignes = [(t, "hors_sujet", "clinc150") for t in HORS_SUJET]
    lignes += [
        ("My VPN keeps disconnecting from home", "reseau", "superuser"),
        ("Wi-Fi drops every few minutes", "reseau", "superuser"),
        ("Printer is offline and will not print", "materiel", "superuser"),
        ("Outlook does not receive new emails", "logiciel", "superuser"),
    ]
    return pd.DataFrame(lignes, columns=["text", "categorie", "source"])


@pytest.fixture(scope="session")
def modele(encodeur: FauxEncodeur, petit_jeu: pd.DataFrame) -> ModeleSupport:
    m = ModeleSupport(Hyper(C=1.0, seuil=0.3, min_df=1))
    m.utiliser(encodeur, BaseConnaissances(encodeur))
    return m.entrainer(petit_jeu)
