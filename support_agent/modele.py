"""Modèle de l'agent : classement de l'incident + recherche de l'article + priorité.

Représentation du texte = TF-IDF mots (1-2) + TF-IDF caractères (2-5) + embedding MiniLM.
Classifieur = LinearSVC calibré (probabilités) ; sous le seuil de confiance, l'agent
s'abstient (`INDETERMINE`) et le message part au tri humain.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import scipy.sparse as sp
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.pipeline import FeatureUnion
from sklearn.svm import LinearSVC

from support_agent.config import HORS_SUJET, INDETERMINE, MODELS
from support_agent.data import Article, charger_base
from support_agent.encodeur import MODELE_MINILM, Encodeur, charger_encodeur
from support_agent.kb import BaseConnaissances, phrases_article
from support_agent.priorite import est_critique, priorite

CHEMIN_MODELE = MODELS / "support.joblib"
POIDS_BASE = 3.0  # les phrases de la base sont rares et sûres : elles comptent triple
LAMBDA_CATEGORIE = 0.1  # poids de la probabilité de catégorie dans le choix de l'article

_MOTS = re.compile(r"[a-z0-9]+")
# Mots qui ne disent rien du problème : un message fait seulement de ces mots est trop vague.
_VIDES_TEXTE = """
a an the it its this that my our me i we you is are was be been does do did doesn don t s
not no can cannot won wont work works working worked broken problem problems issue
issues help please urgent something anything thing stuff again still anymore now today
there here what why how wrong error fix fixed bad ok hi hello so very really just
"""
VIDES = frozenset(_VIDES_TEXTE.split())


SEUIL_HORS_SUJET = 0.85  # sous ce seuil, un message avec du vocabulaire IT n'est pas refusé


def trop_vague(texte: str) -> bool:
    """Vrai si le message ne contient aucun mot qui décrit le problème (« It does not work »)."""
    return not [m for m in _MOTS.findall(texte.lower()) if m not in VIDES]


def vocabulaire_base(articles: list[Article]) -> frozenset[str]:
    """Mots porteurs de sens des titres et symptômes de la base (4 lettres ou plus)."""
    mots = {m for a in articles for p in phrases_article(a) for m in _MOTS.findall(p.lower())}
    return frozenset(m for m in mots if len(m) >= 4 and m not in ENGLISH_STOP_WORDS)


@dataclass(frozen=True)
class Hyper:
    C: float = 1.0
    seuil: float = 0.50
    min_df: int = 2


def exemples_base(articles: list[Article]) -> pd.DataFrame:
    """Titre et symptômes de chaque article, utilisés comme exemples courts étiquetés."""
    lignes = [(p, a.categorie) for a in articles for p in phrases_article(a)]
    return pd.DataFrame(lignes, columns=["text", "categorie"]).assign(source="base")


def _tfidf(min_df: int) -> FeatureUnion:
    return FeatureUnion([
        ("mots", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=min_df)),
        ("car", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True,
                                min_df=min_df)),
    ])


@dataclass
class Prediction:
    texte: str
    categorie: str  # une catégorie, `hors_sujet` ou `INDETERMINE`
    categorie_probable: str  # meilleure étiquette même en cas d'abstention
    confiance: float
    priorite: str
    critique: bool
    articles: list[dict[str, Any]] = field(default_factory=list)
    alternatives: list[dict[str, Any]] = field(default_factory=list)

    def en_dict(self) -> dict[str, Any]:
        return asdict(self)


class ModeleSupport:
    def __init__(self, hyper: Hyper | None = None, nom_encodeur: str = MODELE_MINILM) -> None:
        self.hyper = hyper or Hyper()
        self.nom_encodeur = nom_encodeur
        self.tfidf = _tfidf(self.hyper.min_df)
        self.clf: CalibratedClassifierCV | None = None
        self._encodeur: Encodeur | None = None
        self._kb: BaseConnaissances | None = None
        self._vocab: frozenset[str] | None = None

    # -- encodeur et base : non sauvegardés, reconstruits au chargement -------------
    @property
    def encodeur(self) -> Encodeur:
        if self._encodeur is None:
            self._encodeur = charger_encodeur(self.nom_encodeur)
        return self._encodeur

    @property
    def kb(self) -> BaseConnaissances:
        if self._kb is None:
            self._kb = BaseConnaissances(self.encodeur)
        return self._kb

    def utiliser(self, encodeur: Encodeur, kb: BaseConnaissances | None = None) -> ModeleSupport:
        """Injecte un encodeur (et une base) déjà chargés, par exemple dans les tests."""
        self._encodeur, self._kb, self._vocab = encodeur, kb, None
        return self

    def __getstate__(self) -> dict[str, Any]:
        etat = self.__dict__.copy()
        etat["_encodeur"] = etat["_kb"] = etat["_vocab"] = None
        return etat

    # -- apprentissage --------------------------------------------------------------
    def _matrice(self, textes: list[str], vecteurs: np.ndarray, apprendre: bool) -> sp.csr_matrix:
        t = self.tfidf.fit_transform(textes) if apprendre else self.tfidf.transform(textes)
        return sp.hstack([t, sp.csr_matrix(vecteurs)]).tocsr()

    def entrainer(
        self, df: pd.DataFrame, vecteurs: np.ndarray | None = None,
        articles: list[Article] | None = None,
    ) -> ModeleSupport:
        """`df` : colonnes text, categorie, source. `vecteurs` : embeddings de df.text."""
        base = exemples_base(articles if articles is not None else charger_base())
        textes = df["text"].astype(str).tolist() + base["text"].tolist()
        if vecteurs is None:
            vecteurs = self.encodeur.encode(df["text"].astype(str).tolist())
        tous = np.vstack([vecteurs, self.encodeur.encode(base["text"].tolist())])
        y = pd.concat([df["categorie"], base["categorie"]]).to_numpy()
        poids = np.r_[np.ones(len(df)), np.full(len(base), POIDS_BASE)]
        X = self._matrice(textes, tous, apprendre=True)
        svc = LinearSVC(C=self.hyper.C, class_weight="balanced")
        self.clf = CalibratedClassifierCV(svc, cv=3, method="sigmoid")
        self.clf.fit(X, y, sample_weight=poids)
        return self

    # -- prédiction -----------------------------------------------------------------
    def probabilites(self, textes: list[str], vecteurs: np.ndarray | None = None) -> pd.DataFrame:
        if self.clf is None:
            raise RuntimeError("modèle non entraîné")
        if vecteurs is None:
            vecteurs = self.encodeur.encode(textes)
        X = self._matrice(textes, vecteurs, apprendre=False)
        return pd.DataFrame(self.clf.predict_proba(X), columns=self.clf.classes_)

    def predire(self, texte: str, k: int = 3) -> Prediction:
        texte = texte.strip()
        vecteur = self.encodeur.encode([texte])
        proba = self.probabilites([texte], vecteur).iloc[0].sort_values(ascending=False)
        probable, confiance = str(proba.index[0]), float(proba.iloc[0])
        vague = trop_vague(texte)
        if vague or confiance < self.hyper.seuil:
            categorie = INDETERMINE
        elif probable == HORS_SUJET and confiance < SEUIL_HORS_SUJET and self._parle_it(texte):
            categorie = INDETERMINE  # doute : un humain tranche plutôt qu'un refus à tort
        else:
            categorie = probable
        if categorie == INDETERMINE and probable == HORS_SUJET and not vague:
            probable = str(proba.index[1])  # meilleure piste informatique pour le technicien
        alternatives = [{"categorie": str(c), "proba": round(float(p), 3)}
                        for c, p in proba.iloc[:3].items()]
        if categorie == HORS_SUJET or vague:
            prio = "low" if categorie == HORS_SUJET else "medium"
            return Prediction(texte, categorie, probable, round(confiance, 3), prio, False,
                              [], alternatives)
        bonus = {str(c): LAMBDA_CATEGORIE * float(p) for c, p in proba.items()}
        articles = [
            {"id": r.article.id, "titre": r.article.titre, "categorie": r.article.categorie,
             "score": r.score, "etapes": list(r.article.etapes),
             "escalade_si": r.article.escalade_si}
            for r in self.kb.chercher(texte, k=k, vecteur=vecteur[0], bonus=bonus)
        ]
        prio = priorite(texte, probable)
        return Prediction(texte, categorie, probable, round(confiance, 3), prio,
                          est_critique(texte, probable), articles, alternatives)

    def _parle_it(self, texte: str) -> bool:
        vocab = getattr(self, "_vocab", None)
        if vocab is None:
            vocab = self._vocab = vocabulaire_base(self.kb.articles)
        return bool(set(_MOTS.findall(texte.lower())) & vocab)

    # -- sauvegarde -----------------------------------------------------------------
    def sauver(self, chemin: Path = CHEMIN_MODELE) -> Path:
        chemin.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, chemin)
        return chemin

    @staticmethod
    def charger(chemin: Path = CHEMIN_MODELE) -> ModeleSupport:
        if not chemin.exists():
            raise FileNotFoundError(
                f"{chemin} absent : lancer d'abord `python -m support_agent.train`"
            )
        modele = joblib.load(chemin)
        if not isinstance(modele, ModeleSupport):
            raise TypeError(f"{chemin} ne contient pas un ModeleSupport")
        return modele
