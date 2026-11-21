"""Chargeurs des sources, cache de téléchargement et script `decrire`, sans réseau."""

import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import httpx
import pandas as pd
import pytest

from support_agent import decrire
from support_agent.datasets import clinc, construire, superuser, telechargement, tobi_bueck

# --- cache de téléchargement -----------------------------------------------------


class _Reponse:
    def __init__(self, contenu: bytes = b"", donnees: Any = None) -> None:
        self.contenu, self.donnees = contenu, donnees

    def raise_for_status(self) -> None: ...

    def iter_bytes(self) -> Iterator[bytes]:
        yield self.contenu

    def json(self) -> Any:
        return self.donnees


def test_telecharger_puis_cache(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    appels: list[str] = []

    @contextmanager
    def faux_stream(methode: str, url: str, **kw: Any) -> Iterator[_Reponse]:
        appels.append(url)
        yield _Reponse(b"a,b\n1,2\n")

    monkeypatch.setattr(httpx, "stream", faux_stream)
    dest = tmp_path / "x" / "f.csv"
    assert telechargement.telecharger("http://u", dest).read_text() == "a,b\n1,2\n"
    telechargement.telecharger("http://u", dest)  # déjà en cache : pas de 2e appel
    assert appels == ["http://u"]


def test_fichier_hf(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(telechargement, "RAW", tmp_path)
    vus: list[str] = []

    def faux(url: str, dest: Path) -> Path:
        vus.append(url)
        return dest

    monkeypatch.setattr(telechargement, "telecharger", faux)
    assert telechargement.fichier_hf("o/d", "data/f.csv", "src") == tmp_path / "src" / "f.csv"
    assert vus == ["https://huggingface.co/datasets/o/d/resolve/main/data/f.csv"]


def test_json_en_cache(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    appels: list[dict[str, Any]] = []

    def faux_get(url: str, params: dict[str, Any], **kw: Any) -> _Reponse:
        appels.append(params)
        return _Reponse(donnees={"items": [1], "backoff": 0})

    monkeypatch.setattr(httpx, "get", faux_get)
    monkeypatch.setattr(telechargement.time, "sleep", lambda s: None)
    dest = tmp_path / "r.json"
    assert telechargement.json_en_cache("http://api", {"p": 1}, dest) == {"items": [1],
                                                                            "backoff": 0}
    assert telechargement.json_en_cache("http://api", {"p": 1}, dest)["items"] == [1]
    assert len(appels) == 1


# --- chargeurs -------------------------------------------------------------------


def test_tobi_charger(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    f = tmp_path / "t.csv"
    pd.DataFrame([{"subject": "VPN", "body": "down", "type": "Incident", "language": "en",
                   "queue": "IT Support", "priority": "low", "tag_1": "Network"}]).to_csv(f)
    monkeypatch.setattr(tobi_bueck, "fichier_hf", lambda *a: f)
    assert len(tobi_bueck.charger()) == 2  # même fichier lu pour les 2 noms


def test_superuser_charger(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    f = tmp_path / "su.parquet"
    pd.DataFrame({"TOPIC_TITLE": ["Printer not printing"], "CATEGORIES": ["printer;printer"],
                  "POST": [""], "ANSWERS": [""]}).to_parquet(f)
    monkeypatch.setattr(superuser, "fichier_hf", lambda *a: f)

    def faux_api(url: str, params: dict[str, Any], dest: Path) -> dict[str, Any]:
        items = [{"title": "My VPN keeps dropping", "tags": ["vpn"]}] if params["page"] == 1 else []
        return {"items": items, "has_more": params["page"] == 1 and params["tagged"] == "vpn"}

    monkeypatch.setattr(superuser, "json_en_cache", faux_api)
    df = superuser.charger()
    assert set(df["source"]) == {"superuser", "stackexchange"}
    assert "Printer not printing" in df["text"].tolist()


def test_clinc_charger(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    pq = tmp_path / "c.parquet"
    pd.DataFrame({"text": ["will it rain", "hello"], "intent": [0, 1]}).to_parquet(pq)
    info = tmp_path / "info.json"
    info.write_text(json.dumps({"dataset_info": {"features": {"intent": {
        "names": ["weather", "greeting"]}}}}), encoding="utf-8")
    monkeypatch.setattr(clinc, "telecharger", lambda url, dest: info if "info" in url else pq)
    assert clinc.charger(10)["text"].tolist() == ["Will it rain"]


def test_textes_evaluation() -> None:
    # 246 lignes des CSV + 41 messages des 30 conversations de test
    assert len(construire.textes_evaluation()) == 287


def test_main_construire(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
                         ) -> None:
    monkeypatch.setattr(construire, "construire", lambda n: {"hors_sujet": n})
    construire.main(["--hors-sujet", "7"])
    assert '"hors_sujet": 7' in capsys.readouterr().out


# --- decrire ---------------------------------------------------------------------


def test_decrire(tmp_path: Path) -> None:
    f = tmp_path / "e.csv"
    pd.DataFrame({"text": ["vpn down", "hello there"], "categorie": ["reseau", "hors_sujet"],
                  "priorite": [None, None], "source": ["superuser", "clinc150"]}).to_csv(f)
    res = decrire.decrire(f)
    assert res["echantillon_tobi_bueck"]["lignes"] == 100
    assert res["echantillon_tobi_bueck"]["mots_moyens"] == 62.8  # chiffre de la fiche
    assert res["jeu_independant"]["critiques"] == 32
    assert res["entrainement"]["par_source"] == {"superuser": 1, "clinc150": 1}
    md = decrire.en_markdown(res)
    assert "| jeu_validation | 120 |" in md and "Entraînement par source" in md


def test_decrire_main(capsys: pytest.CaptureFixture[str]) -> None:
    decrire.main(["--json"])
    assert json.loads(capsys.readouterr().out)["base_connaissances"]["articles"] == 57
    decrire.main([])
    assert "| Jeu |" in capsys.readouterr().out
