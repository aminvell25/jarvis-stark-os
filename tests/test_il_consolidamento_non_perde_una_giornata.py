"""Il consolidamento saltava una sessione e non la rivedeva mai più.

## Il difetto, misurato sul disco vero

`esegui()` partiva da `da = self.ultimo_run()` e filtrava i turni con
`sessioni_dal(da)`. Ma quel timbro è un **orologio di parete scritto a fine
ciclo**: ogni giro sale sopra il `ts` di tutte le sessioni che *non* ha
consolidato — quella caduta sul ramo `not r.ok`, quella lasciata a metà da un
crash — e le rende invisibili per sempre.

Misurato il 29 agosto 2026 su `~/.local/share/jarvis-os/memory_data`:

    sessions/2026-08-27.jsonl   7 turni, ts 1787784175..1787853324
    _ultimo-consolidamento.txt  1787882411      (le 04:00 del 28)
    turni visibili al giro dopo 0
    topics/                     solo sessione-2026-08-26.md

Non un difetto ipotetico: **una giornata di memoria già persa.**

## Perché la cura «ovvia» sarebbe stata peggiore

Spostare `_segna_run()` dentro il ciclo — due righe — scrive `time.time()` di
adesso, che è maggiore del `ts` di **tutte** le sessioni non ancora lavorate:
sostituisce un doppione rumoroso con una perdita silenziosa, e la suite resta
verde.

## La cura

La frontiera non è più un numero ma un **insieme di nomi**: le sessioni senza
una riga in `initiatives/`, che è il registro che chi consolida scrive già.
Spariscono con lei tutte le domande che il confronto fra `ts` portava — `>=` o
`>`, l'ordine in cui si lavorano le sessioni, il turno scritto mentre il
consolidamento gira.

⚠️ **Prezzo dichiarato**: la sessione di oggi si lascia stare finché è aperta.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from core.memory.consolidate import Consolidatore
from core.memory.store import MemoryStore


class _Risultato:
    ok, testo, costo_usd, durata_s, errore = True, "nota durevole", 0.0, 0.1, None


class _Caduto:
    ok, testo, costo_usd, durata_s = False, "", 0.0, 0.1
    errore = "il modello non ha risposto"


class _T2:
    """Registra SU QUALE SESSIONE è stato interpellato.

    ⚠️ Senza il registro delle etichette la prova è verde anche sul difetto:
    contare gli spawn non dice *quale* sessione è stata rifatta, e il difetto è
    esattamente quale.
    """

    def __init__(self, cade_su: set[str] | None = None) -> None:
        self.chiamate: list[str] = []
        self._cade = cade_su or set()

    async def esegui(self, compito: str, etichetta: str):
        sessione = _sessione(etichetta)
        if not self.chiamate or self.chiamate[-1] != sessione:
            self.chiamate.append(sessione)
        return _Caduto() if sessione in self._cade else _Risultato()


#: L'etichetta dello spawn e' `consolidamento-<sessione>-<corpus>` da quando il
#: consolidamento riassume DUE volte (fetta 3: la classe viene da quale corpus
#: il modello ha visto, non da cio' che risponde). Qui si torna alla sessione,
#: e i due richiami consecutivi della stessa sessione si contano per uno: ogni
#: asserzione di questo file parla di QUALI SESSIONI sono state lavorate e in
#: che ordine, non di quante chiamate siano servite.
def _sessione(etichetta: str) -> str:
    coda = etichetta.split("consolidamento-", 1)[-1]
    for corpus in ("-utente", "-jarvis"):
        if coda.endswith(corpus):
            return coda[: -len(corpus)]
    return coda


def _store_con(tmp_path: Path, sessioni: dict[str, int]) -> MemoryStore:
    """Uno store VERO, con sessioni dai `ts` distinti e crescenti."""
    s = MemoryStore(tmp_path)
    base = time.time() - 10 * 86_400
    for i, (nome, quanti) in enumerate(sessioni.items()):
        p = s.sessions / f"{nome}.jsonl"
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as f:
            for k in range(quanti):
                f.write(json.dumps({
                    "ts": base + i * 3600 + k,
                    "utente": f"domanda {i}.{k}", "jarvis": f"risposta {i}.{k}",
                }) + "\n")
    return s


IERI = {"2026-01-01": 2, "2026-01-02": 2, "2026-01-03": 2}


class TestUnaSessioneSALTATANonSiPerde:
    async def test_dopo_un_guasto_a_META_si_riprende_da_LI(self, tmp_path) -> None:
        """⚠️ La prova che boccia. Oggi rossa in un verso — rifà la prima — e
        con la cura sbagliata rossa nell'altro: perde le altre due."""
        store = _store_con(tmp_path, IERI)

        primo = _T2(cade_su={"2026-01-02"})
        await Consolidatore(store, primo).esegui(oggi="2026-01-09")
        assert primo.chiamate == ["2026-01-01", "2026-01-02", "2026-01-03"]

        secondo = _T2()
        await Consolidatore(store, secondo).esegui(oggi="2026-01-09")
        assert secondo.chiamate == ["2026-01-02"], (
            f"alla ripresa ha lavorato {secondo.chiamate}: o rifà una sessione "
            "già riassunta — e ribrucia uno spawn — o ne perde una per sempre"
        )

    async def test_e_al_terzo_giro_non_c_e_piu_niente_da_fare(self, tmp_path) -> None:
        """Idempotente: la frontiera è ciò che è stato fatto, non quando."""
        store = _store_con(tmp_path, IERI)
        await Consolidatore(store, _T2()).esegui(oggi="2026-01-09")
        terzo = _T2()
        esito = await Consolidatore(store, terzo).esegui(oggi="2026-01-09")
        assert terzo.chiamate == []
        assert esito["motivo"] == "niente di nuovo"

    async def test_una_QUOTA_esaurita_lascia_intatto_il_resto(self, tmp_path) -> None:
        """Il ramo `QuotaEsaurita` esce dal ciclo: le sessioni non raggiunte
        non devono sparire con lui."""
        from core.llm.governor import Permesso, QuotaEsaurita, Rifiuto

        store = _store_con(tmp_path, IERI)

        class _Quota(_T2):
            async def esegui(self, compito, etichetta):
                sessione = _sessione(etichetta)
                if not self.chiamate or self.chiamate[-1] != sessione:
                    self.chiamate.append(sessione)
                if sessione == "2026-01-02":
                    raise QuotaEsaurita(Permesso(False, Rifiuto.QUOTA, riprova_fra_s=60))
                return _Risultato()

        await Consolidatore(store, _Quota()).esegui(oggi="2026-01-09")
        dopo = _T2()
        await Consolidatore(store, dopo).esegui(oggi="2026-01-09")
        assert dopo.chiamate == ["2026-01-02", "2026-01-03"], (
            "la quota è finita a metà e le sessioni non raggiunte sono sparite"
        )


class TestLaFrontieraNONeUnOrologio:
    def test_e_l_insieme_di_cio_che_e_stato_FATTO(self, tmp_path) -> None:
        store = _store_con(tmp_path, IERI)
        assert store.sessioni_consolidate() == set()
        store.registra_iniziativa("consolidamento", {"sessione": "2026-01-01"})
        assert store.sessioni_consolidate() == {"2026-01-01"}

    def test_una_riga_STORTA_non_fa_cadere_il_giro(self, tmp_path) -> None:
        store = _store_con(tmp_path, IERI)
        store.registra_iniziativa("consolidamento", {"sessione": "2026-01-01"})
        p = next(store.initiatives.glob("*.jsonl"))
        with p.open("a", encoding="utf-8") as f:
            f.write("{ questa non e' json\n")
        assert store.sessioni_consolidate() == {"2026-01-01"}

    def test_e_le_ALTRE_iniziative_non_contano(self, tmp_path) -> None:
        """`initiatives/` raccoglie anche i protocolli e il resoconto: solo le
        righe del consolidamento dicono che una sessione è stata riassunta."""
        store = _store_con(tmp_path, IERI)
        store.registra_iniziativa("protocollo", {"sessione": "2026-01-01"})
        assert store.sessioni_consolidate() == set()

    def test_il_timbro_ha_UN_mestiere_solo(self, tmp_path) -> None:
        """Il freno alla frequenza resta il suo; la frontiera non è più sua.

        ⚠️ Rispondeva a due domande — «quando fu l'ultimo giro» e «fin dove
        abbiamo consolidato» — e reggeva finché le due risposte coincidevano.
        Non coincidevano.
        """
        store = _store_con(tmp_path, IERI)
        c = Consolidatore(store, _T2())
        assert c.saltato(adesso=time.time()) is True, "mai girato: è saltato"
        c._segna_run()
        assert c.saltato(adesso=time.time()) is False

    async def test_e_un_timbro_RECENTE_non_nasconde_una_sessione(
            self, tmp_path) -> None:
        """La prova che il timbro non decide più che cosa si consolida.

        Con la vecchia frontiera questo scenario era il difetto in una riga: un
        timbro appena scritto rendeva invisibile ogni sessione precedente.
        """
        store = _store_con(tmp_path, IERI)
        c = Consolidatore(store, _T2())
        c._segna_run()                       # timbro di ADESSO, dopo i turni

        t2 = _T2()
        await Consolidatore(store, t2).esegui(oggi="2026-01-09")
        assert t2.chiamate == ["2026-01-01", "2026-01-02", "2026-01-03"], (
            f"il timbro ha nascosto {set(IERI) - set(t2.chiamate)}: è "
            "esattamente il difetto che ha mangiato il 27 agosto"
        )


class TestLaSessioneDiOGGISiLasciaStare:
    """Il prezzo dichiarato della cura: una sessione aperta si riassumerebbe a
    metà, e il topic è un `write_text` — la seconda scrittura cancellerebbe la
    prima."""

    async def test_oggi_non_si_tocca(self, tmp_path) -> None:
        store = _store_con(tmp_path, {"2026-01-01": 2, "2026-01-02": 2})
        t2 = _T2()
        await Consolidatore(store, t2).esegui(oggi="2026-01-02")
        assert t2.chiamate == ["2026-01-01"]

    async def test_e_domani_tocca_a_lei(self, tmp_path) -> None:
        store = _store_con(tmp_path, {"2026-01-01": 2, "2026-01-02": 2})
        await Consolidatore(store, _T2()).esegui(oggi="2026-01-02")
        domani = _T2()
        await Consolidatore(store, domani).esegui(oggi="2026-01-03")
        assert domani.chiamate == ["2026-01-02"]


class TestSiLeggeLaSessioneINTERA:
    def test_e_non_una_coda(self, tmp_path) -> None:
        """⚠️ `scrivi_topic` fa `write_text`: leggendo una coda, rifare una
        sessione ne riscriverebbe il riassunto con la sola parte finale — una
        nota che si accorcia sotto le mani di chi la rilegge."""
        store = _store_con(tmp_path, {"2026-01-01": 5})
        assert len(store.turni_di("2026-01-01")) == 5
        assert store.turni_di("non-esiste") == []

    async def test_e_il_topic_riscritto_e_lo_STESSO(self, tmp_path) -> None:
        store = _store_con(tmp_path, {"2026-01-01": 5})
        await Consolidatore(store, _T2()).esegui(oggi="2026-01-09")
        primo = store.leggi_topic("sessione 2026-01-01").contenuto

        # si cancella la traccia: la sessione torna «da fare», come farebbe una
        # riparazione a mano
        for p in store.initiatives.glob("*.jsonl"):
            p.unlink()
        await Consolidatore(store, _T2()).esegui(oggi="2026-01-09")
        assert store.leggi_topic("sessione 2026-01-01").contenuto == primo
