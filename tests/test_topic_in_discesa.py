"""I topic che la scrivania ASPETTA contro quelli che il core EMETTE.

`tests/test_ws_contract.py` guarda la salita — che cosa il renderer puo'
mandare al core — e i campi di un messaggio. Nessuno guardava la discesa: un
pannello puo' iscriversi a un topic che il core non pubblica da nessuna parte,
e resta per sempre nello stato vuoto senza un errore, che e' esattamente la
forma di guasto che §11.9 rende invisibile.

Misurato il 2 settembre 2026: due topic in questa condizione, da settimane.
Non si chiudono qui — chiuderli e' lavoro, e ognuno e' una fetta sua — ma da
oggi sono DICHIARATI, e il test diventa rosso in due direzioni: un topic nuovo
che il core non manda, e una lacuna dichiarata che qualcuno ha chiuso senza
toglierla dall'elenco.

Il test non ripete a mano i due elenchi: li estrae dai sorgenti, come fa il
contratto in salita.
"""

from __future__ import annotations

import re
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
UI = RADICE / "ui/src"
CORE = RADICE / "core"

#: Le lacune dichiarate, con la ragione. Un elenco chiuso: e' il punto del test.
LACUNE_DICHIARATE = {
    # Il tracker (`core/gestures/tracker.py`) non fa uscire i fotogrammi per
    # scelta — §18.3 — e pubblica solo `gesture.intent`. Il pannello `gesture`
    # e l'apertura automatica in `desk/scrivania.js` aspettano un topic che
    # nessuno emette: anche con MediaPipe installato non si accenderebbero.
    "gesture.frame",
    # Il pannello `news` scrive «argomenti: …» da un messaggio che il core non
    # manda: gli argomenti vivono in `MotoreNews.argomenti` e servono al gate,
    # ma nessuno li pubblica. La riga resta vuota, e non e' uno stato vuoto
    # dichiarato: e' un dato che esiste e non arriva.
    "news.argomenti",
}


def _sorgenti_ui() -> list[Path]:
    # La galleria monta i pannelli con dati finti e topic finti (§11.9, l'unica
    # eccezione): non e' un contratto con il core, e non si conta.
    return [p for p in UI.rglob("*.js") if "gallery" not in p.parts]


def topic_attesi_dalla_ui() -> set[str]:
    """Gli argomenti letterali di `daTopic(...)` e di `bus.su("...")`."""
    fuori: set[str] = set()
    for p in _sorgenti_ui():
        s = p.read_text(encoding="utf-8")
        for m in re.finditer(r"daTopic\(([^)]*)\)", s):
            fuori.update(re.findall(r'"([^"]+)"', m.group(1)))
        fuori.update(re.findall(r'bus\.su\(\s*"([^"]+)"', s))
    return fuori


def topic_emessi_dal_core() -> set[str]:
    """I `"topic": "..."` letterali e le costanti `TOPIC = "..."` in `core/`."""
    fuori: set[str] = set()
    for p in CORE.rglob("*.py"):
        s = p.read_text(encoding="utf-8")
        fuori.update(re.findall(r'"topic":\s*"([^"]+)"', s))
        fuori.update(re.findall(r'^TOPIC\s*=\s*"([^"]+)"', s, re.MULTILINE))
    return fuori


class TestLaDiscesa:
    def test_gli_elenchi_non_sono_vuoti(self) -> None:
        # Un'estrazione che torna vuoto renderebbe verde tutto il resto per il
        # motivo sbagliato (§11.7 regola 4).
        assert len(topic_attesi_dalla_ui()) >= 10
        assert len(topic_emessi_dal_core()) >= 10

    def test_ogni_topic_atteso_e_emesso_o_dichiarato(self) -> None:
        mancanti = topic_attesi_dalla_ui() - topic_emessi_dal_core()
        assert mancanti == LACUNE_DICHIARATE, (
            "la scrivania aspetta topic che il core non emette, e non sono "
            f"quelli dichiarati: {sorted(mancanti ^ LACUNE_DICHIARATE)}")

    def test_una_lacuna_dichiarata_e_ancora_attesa(self) -> None:
        # Se un pannello smette di iscriversi, la dichiarazione va tolta: un
        # elenco di lacune che nessuno legge piu' e' una riga falsa.
        assert LACUNE_DICHIARATE <= topic_attesi_dalla_ui()
