"""Modèle de l'agent : classement de l'incident + recherche de l'article + priorité.

Représentation du texte = TF-IDF mots (1-2) + TF-IDF caractères (2-5) + embedding MiniLM.
Classifieur = LinearSVC calibré (probabilités) ; sous le seuil de confiance, l'agent
s'abstient (`INDETERMINE`) et le message part au tri humain.
"""

from __future__ import annotations

import difflib
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
SEUIL_CORRECTION = 0.8  # ressemblance minimale (difflib) pour corriger une faute de frappe
N_MOTS_FREQUENTS = 6000  # mots candidats à la correction : les plus fréquents du vocabulaire


def trop_vague(texte: str) -> bool:
    """Vrai si le message ne contient aucun mot qui décrit le problème (« It does not work »)."""
    return not [m for m in _MOTS.findall(texte.lower()) if m not in VIDES]


def vocabulaire_base(articles: list[Article]) -> frozenset[str]:
    """Mots porteurs de sens des titres et symptômes de la base (4 lettres ou plus)."""
    mots = {m for a in articles for p in phrases_article(a) for m in _MOTS.findall(p.lower())}
    return frozenset(m for m in mots if len(m) >= 4 and m not in ENGLISH_STOP_WORDS)


SUFFIXES = ("ing", "ed", "es", "s", "er", "ly", "y")


def formes_de_base(mot: str) -> set[str]:
    """Formes possibles sans suffixe : renewing -> renew, choppy -> chop, braking -> brake."""
    formes = {mot}
    for suffixe in SUFFIXES:
        if mot.endswith(suffixe) and len(mot) - len(suffixe) >= 3:
            racine = mot[: -len(suffixe)]
            formes |= {racine, racine + "e"}
            if racine[-1] == racine[-2]:
                formes.add(racine[:-1])
            if racine.endswith("i"):
                formes.add(racine[:-1] + "y")
    return formes


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
    # pourquoi l'agent s'abstient : vague, incomprehensible, confiance_faible,
    # hors_sujet_douteux ; vide quand il répond
    raison: str = ""
    texte_corrige: str = ""  # texte après correction des fautes, s'il a changé

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
        self._mots_frequents: list[str] | None = None
        self._dico: frozenset[str] | None = None

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
        self._encodeur, self._kb, self._vocab, self._dico = encodeur, kb, None, None
        return self

    def __getstate__(self) -> dict[str, Any]:
        etat = self.__dict__.copy()
        etat["_encodeur"] = etat["_kb"] = etat["_vocab"] = etat["_mots_frequents"] = None
        etat["_dico"] = None
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
        self._mots_frequents = None  # le vocabulaire a changé
        return self

    # -- prédiction -----------------------------------------------------------------
    def probabilites(self, textes: list[str], vecteurs: np.ndarray | None = None) -> pd.DataFrame:
        if self.clf is None:
            raise RuntimeError("modèle non entraîné")
        if vecteurs is None:
            vecteurs = self.encodeur.encode(textes)
        X = self._matrice(textes, vecteurs, apprendre=False)
        return pd.DataFrame(self.clf.predict_proba(X), columns=self.clf.classes_)

    def corriger(self, texte: str) -> str:
        """Corrige les fautes de frappe : un mot inconnu (4 lettres ou plus) est remplacé par
        le mot fréquent du vocabulaire le plus proche (« printr » -> « printer »).
        Le charabia (« asdfgh ») n'a pas de voisin assez proche et reste tel quel."""
        vocabulaire = self.tfidf.transformer_list[0][1].vocabulary_
        frequents = self._frequents()

        dico = self._dictionnaire()

        def remplacer(m: re.Match[str]) -> str:
            mot = m.group(0)
            bas = mot.lower()
            # un mot anglais correct n'est jamais touché, même s'il est absent de
            # l'entraînement : « ransom » ne doit pas devenir « random »
            if len(bas) < 4 or bas in vocabulaire or bas in dico:
                return mot
            proches = difflib.get_close_matches(bas, frequents, n=1, cutoff=SEUIL_CORRECTION)
            if not proches:
                return mot
            bases = [b for b in formes_de_base(bas) if b != bas and b in dico]
            if bases and not any(proches[0].startswith(b) for b in bases):
                return mot  # « renewing » (renew) ne devient pas « reviewing »
            return proches[0]

        return re.sub(r"[A-Za-z]+", remplacer, texte)

    def _dictionnaire(self) -> frozenset[str]:
        """Mots anglais connus : tokenizer de MiniLM (si l'encodeur le fournit)."""
        dico: frozenset[str] | None = getattr(self, "_dico", None)
        if dico is None:
            mots = getattr(self.encodeur, "mots", None)
            dico = frozenset(mots()) if callable(mots) else frozenset()
            self._dico = dico
        return dico

    def _frequents(self) -> list[str]:
        frequents: list[str] | None = getattr(self, "_mots_frequents", None)
        if frequents is None:
            v = self.tfidf.transformer_list[0][1]
            ordre = np.argsort(v.idf_)[:N_MOTS_FREQUENTS]  # idf faible = mot fréquent
            par_indice = {i: w for w, i in v.vocabulary_.items()}
            frequents = [par_indice[i] for i in ordre
                         if par_indice[i].isalpha() and len(par_indice[i]) >= 3]
            self._mots_frequents = frequents
        return frequents

    def predire(self, texte: str, k: int = 3) -> Prediction:
        original = texte.strip()
        texte = self.corriger(original)
        corrige = texte if texte != original else ""
        p = self._predire(texte, k)
        p.texte, p.texte_corrige = original, corrige
        return p

    def _predire(self, texte: str, k: int) -> Prediction:
        vecteur = self.encodeur.encode([texte])
        proba = self.probabilites([texte], vecteur).iloc[0].sort_values(ascending=False)
        probable, confiance = str(proba.index[0]), float(proba.iloc[0])
        vague = trop_vague(texte)
        raison = ""
        if vague:
            categorie, raison = INDETERMINE, "vague"
        elif probable == HORS_SUJET and not self._mot_connu(texte):
            # aucun mot connu et rien d'informatique : charabia (« asdfgh », « 123456 »).
            # Une faute de frappe (« Prnter jamed ») est, elle, reconnue par les n-grammes
            # de caractères et n'arrive pas ici.
            categorie, raison = INDETERMINE, "incomprehensible"
        elif confiance < self.hyper.seuil:
            categorie, raison = INDETERMINE, "confiance_faible"
        elif probable == HORS_SUJET and confiance < SEUIL_HORS_SUJET and self._parle_it(texte):
            # doute : un humain tranche plutôt qu'un refus à tort
            categorie, raison = INDETERMINE, "hors_sujet_douteux"
        else:
            categorie = probable
        if categorie == INDETERMINE and probable == HORS_SUJET and raison not in (
                "vague", "incomprehensible"):
            probable = str(proba.index[1])  # meilleure piste informatique pour le technicien
        alternatives = [{"categorie": str(c), "proba": round(float(p), 3)}
                        for c, p in proba.iloc[:3].items()]
        if categorie == HORS_SUJET or raison in ("vague", "incomprehensible"):
            prio = "low" if categorie == HORS_SUJET else "medium"
            return Prediction(texte, categorie, probable, round(confiance, 3), prio, False,
                              [], alternatives, raison)
        bonus = {str(c): LAMBDA_CATEGORIE * float(p) for c, p in proba.items()}
        articles = [
            {"id": r.article.id, "titre": r.article.titre, "categorie": r.article.categorie,
             "score": r.score, "etapes": list(r.article.etapes),
             "escalade_si": r.article.escalade_si}
            for r in self.kb.chercher(texte, k=k, vecteur=vecteur[0], bonus=bonus)
        ]
        prio = priorite(texte, probable)
        return Prediction(texte, categorie, probable, round(confiance, 3), prio,
                          est_critique(texte, probable), articles, alternatives, raison)

    def _mot_connu(self, texte: str) -> bool:
        """Au moins un mot du message existe dans le vocabulaire appris (TF-IDF mots)."""
        vocabulaire = self.tfidf.transformer_list[0][1].vocabulary_
        return any(m in vocabulaire for m in re.findall(r"(?u)\b\w\w+\b", texte.lower()))

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
