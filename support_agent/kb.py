"""Recherche d'articles dans la base de connaissances (sans génération libre).

Chaque article est représenté par son titre et chacun de ses symptômes. Le score d'un
article est la meilleure similarité cosinus (MiniLM) entre le message et l'une de ces
phrases : un message court qui ressemble à un seul symptôme suffit à trouver l'article.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from support_agent.data import Article, charger_base
from support_agent.encodeur import Encodeur


def phrases_article(article: Article) -> list[str]:
    symptomes = [s.strip() for s in article.symptomes.split(";") if s.strip()]
    return [article.titre, *symptomes]


@dataclass(frozen=True)
class Resultat:
    article: Article
    score: float


class BaseConnaissances:
    def __init__(self, encodeur: Encodeur, articles: list[Article] | None = None) -> None:
        self.articles = articles if articles is not None else charger_base()
        self._encodeur = encodeur
        phrases: list[str] = []
        proprietaire: list[int] = []
        for i, a in enumerate(self.articles):
            for p in phrases_article(a):
                phrases.append(p)
                proprietaire.append(i)
        self._proprietaire = np.array(proprietaire)
        self._vecteurs = encodeur.encode(phrases)

    def par_id(self, ident: str) -> Article | None:
        return next((a for a in self.articles if a.id == ident), None)

    def chercher(
        self, texte: str, k: int = 3, categorie: str | None = None,
        vecteur: np.ndarray | None = None, bonus: dict[str, float] | None = None,
    ) -> list[Resultat]:
        """Les `k` meilleurs articles.

        `categorie` restreint la recherche ; `bonus` ajoute un petit poids par catégorie
        (probabilités du classifieur) pour garder l'article cohérent avec la catégorie.
        """
        q = vecteur if vecteur is not None else self._encodeur.encode([texte])[0]
        sims = self._vecteurs @ q
        similarite = np.full(len(self.articles), -np.inf)
        np.maximum.at(similarite, self._proprietaire, sims)
        rang = similarite.copy()
        if bonus:
            rang = rang + np.array([bonus.get(a.categorie, 0.0) for a in self.articles])
        if categorie is not None:
            for i, a in enumerate(self.articles):
                if a.categorie != categorie:
                    rang[i] = -np.inf
        ordre = [i for i in np.argsort(-rang)[:k] if np.isfinite(rang[i])]
        # le score affiché reste la similarité (0 à 1), le bonus ne sert qu'au classement
        return [Resultat(self.articles[i], round(float(similarite[i]), 3)) for i in ordre]
