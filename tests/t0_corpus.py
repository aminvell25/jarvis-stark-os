"""EVAL — il corpus del parser T0 (§7.6, §22).

Frasi etichettate: **90 comandi** con l'intento atteso e **43
conversazionali** che devono dare `None`. (Erano 80 e 20 quando questo file
nacque; le venti conversazionali aggiunte il 25 agosto cominciano tutte con un
verbo di comando, ed e' cosi' che ne hanno trovate due rubate a T1.)

Il rischio che questo corpus sorveglia non e' che il parser manchi un comando —
quello si nota subito, perche' il comando non funziona. E' che **ne rubi uno a
T1**: la regola `search_files` e' deliberatamente permissiva e sta in fondo, e
una regola aggiunta sopra di lei con un pattern largo si mangerebbe frasi che
dovrebbero diventare conversazione. Quel guasto e' silenzioso — JARVIS
risponderebbe con un'azione invece che con una frase — ed e' la ragione per cui
le frasi conversazionali contano quanto i comandi.

Misura anche la **latenza mediana**: §7.6 impone meno di 10 ms, ed e' il numero
che tiene in piedi il budget di §7.5.
"""

from __future__ import annotations

import hashlib
import json
import platform
import statistics
import time
from pathlib import Path

import pytest

from core.llm.grammar import Intent, parse

#: (frase, tool atteso, argomenti attesi o None se non si controllano)
COMANDI: list[tuple[str, str, dict | None]] = [
    # ── pannelli (16) ────────────────────────────────────────────────────────
    ("apri la telemetria", "open_panel", {"panel": "telemetria"}),
    ("apri telemetria", "open_panel", {"panel": "telemetria"}),
    ("mostra la console", "open_panel", {"panel": "console"}),
    ("mostra il globo", "open_panel", {"panel": "globo"}),
    ("apri i file", "open_panel", None),
    ("apri il pannello file", "open_panel", {"panel": "file"}),
    ("mostra gli agenti", "open_panel", {"panel": "agenti"}),
    ("apri le news", "open_panel", {"panel": "news"}),
    ("mostra la sorgente", "open_panel", {"panel": "sorgente"}),
    ("apri le impostazioni", "open_panel", {"panel": "impostazioni"}),
    ("chiudi la console", "close_panel", {"panel": "console"}),
    ("chiudi telemetria", "close_panel", {"panel": "telemetria"}),
    ("chiudi il globo", "close_panel", {"panel": "globo"}),
    ("nascondi tutto", "hide_all", {}),
    ("via tutto", "hide_all", {}),
    ("affianca", "tile_panels", {}),
    # ── workspace (8) ────────────────────────────────────────────────────────
    ("workspace 1", "switch_workspace", {"n": 1}),
    ("workspace 2", "switch_workspace", {"n": 2}),
    ("workspace 3", "switch_workspace", {"n": 3}),
    ("workspace 4", "switch_workspace", {"n": 4}),
    ("workspace uno", "switch_workspace", {"n": 1}),
    ("workspace due", "switch_workspace", {"n": 2}),
    ("workspace tre", "switch_workspace", {"n": 3}),
    ("vai al workspace quattro", "switch_workspace", {"n": 4}),
    # ── sistema (18) ─────────────────────────────────────────────────────────
    ("come sta la cpu", "system_status", {}),
    ("come sta la memoria", "system_status", {}),
    ("come sta la ram", "system_status", {}),
    ("come sta il sistema", "system_status", {}),
    ("stato cpu", "system_status", {}),
    ("stato della memoria", "system_status", {}),
    ("stato del sistema", "system_status", {}),
    ("cosa sta rallentando", "top_processes", {}),
    ("cosa rallenta il pc", "top_processes", {}),
    ("chi sta rallentando tutto", "top_processes", {}),
    ("chi rallenta la macchina", "top_processes", {}),
    ("volume 40", "set_volume", {"level": 40}),
    ("volume 0", "set_volume", {"level": 0}),
    ("volume 100", "set_volume", {"level": 100}),
    ("metti il volume 65", "set_volume", {"level": 65}),
    ("volume 250", "set_volume", {"level": 100}),      # si satura, non si rifiuta
    ("silenzio", "mute", {}),
    ("muto", "mute", {}),
    # ── meta-comandi (12) ────────────────────────────────────────────────────
    ("riassumimi la giornata", "brief_me", {}),
    ("briefing", "brief_me", {}),
    ("fammi il punto", "brief_me", {}),
    ("dai fammi il punto della situazione", "brief_me", {}),
    ("cosa richiede la mia attenzione", "needs_attention", {}),
    ("cosa serve la mia attenzione", "needs_attention", {}),
    ("cosa vuole la mia attenzione", "needs_attention", {}),
    ("come stiamo", "doctor", {}),
    ("jarvis come stiamo", "doctor", {}),
    ("stato dei sistemi", "doctor", {}),
    ("diagnostica", "doctor", {}),
    ("fammi una diagnostica", "doctor", {}),
    # ── file (14) ────────────────────────────────────────────────────────────
    ("cerca fattura", "search_files", {"query": "fattura"}),
    ("cerca fattura agosto", "search_files", {"query": "fattura agosto"}),
    ("cerca il file contratto", "search_files", {"query": "contratto"}),
    ("cerca i file di agosto", "search_files", {"query": "di agosto"}),
    ("cerca preventivo nei file", "search_files", {"query": "preventivo"}),
    ("cerca curriculum", "search_files", {"query": "curriculum"}),
    ("cerca le foto delle vacanze", "search_files", None),
    ("cerca staffa v3", "search_files", {"query": "staffa v3"}),
    ("cerca dump sql", "search_files", {"query": "dump sql"}),
    ("cerca il file di configurazione", "search_files", None),
    ("cerca appunti", "search_files", {"query": "appunti"}),
    ("cerca backup", "search_files", {"query": "backup"}),
    ("cerca schema", "search_files", {"query": "schema"}),
    ("cerca relazione trimestrale", "search_files", {"query": "relazione trimestrale"}),
    # ── varianti con rumore intorno (12) ─────────────────────────────────────
    ("jarvis apri la telemetria", "open_panel", {"panel": "telemetria"}),
    ("per favore apri la console", "open_panel", {"panel": "console"}),
    ("ok apri il globo", "open_panel", {"panel": "globo"}),
    ("jarvis workspace 2", "switch_workspace", {"n": 2}),
    ("senti, come sta la cpu", "system_status", {}),
    ("dimmi come sta il sistema", "system_status", {}),
    ("jarvis silenzio", "mute", {}),
    ("mettiti in silenzio", "mute", {}),
    ("jarvis volume 30", "set_volume", {"level": 30}),
    ("allora, cosa sta rallentando il computer", "top_processes", {}),
    ("jarvis briefing", "brief_me", {}),
    ("jarvis diagnostica", "doctor", {}),

    # ── web e YouTube (10) — Fase 6, §6.3 ────────────────────────────────────
    # La prima e' la frase del criterio di §22, parola per parola.
    ("apri youtube e metti synthwave", "youtube_search", {"query": "synthwave"}),
    ("apri youtube", "youtube_search", {"query": ""}),
    ("vai su youtube", "youtube_search", {"query": ""}),
    ("metti synthwave su youtube", "youtube_search", {"query": "synthwave"}),
    ("cerca synthwave su youtube", "youtube_search", {"query": "synthwave"}),
    ("riproduci i pink floyd su youtube", "youtube_search", {"query": "i pink floyd"}),
    ("fai partire miles davis su youtube", "youtube_search", {"query": "miles davis"}),
    ("apri https://esempio.it/pagina", "open_web", {"url": "https://esempio.it/pagina"}),
    ("apri il browser", "open_panel", {"panel": "browser"}),
    ("chiudi il browser", "close_panel", {"panel": "browser"}),
]

#: Frasi che devono andare a T1. **Non sono riempimento**: sono la meta' del
#: corpus che scopre una regola troppo avida.

CONVERSAZIONALI: list[str] = [
    # Fase 6: frasi che NOMINANO il web senza chiedere niente. Le regole di
    # §6.3 hanno pattern larghi, e sono queste a dire se ne hanno di troppo.
    "mi metti un po' di musica mentre lavoro",
    "cosa ne pensi dei video di divulgazione scientifica",
    "ieri ho visto un documentario interessante",
    "che ne pensi di questo progetto",
    "come stai oggi",
    "raccontami una cosa interessante",
    "spiegami come funziona un motore diesel",
    "quanto manca a natale",
    "ho avuto una giornata pesante",
    "secondo te conviene comprarlo",
    "che tempo fa domani",
    "scrivimi due righe per un'email di scuse",
    "non ricordo dove ho messo le chiavi",
    "mi sento stanco",
    "qual e' la capitale del portogallo",
    "aiutami a decidere",
    "traduci questa frase in inglese",
    "perche' il cielo e' blu",
    "fammi ridere",
    "cosa ne dici se andiamo avanti cosi'",
    "ricordami perche' l'avevamo deciso",
    "sto pensando di rifare il bagno",
    "buonanotte jarvis",

    # ⚠️ LE VENTI CHE ASSOMIGLIANO A UN COMANDO, aggiunte il 25 agosto 2026.
    #
    # Le frasi qui sopra parlano d'altro: nessuna regola le sfiora, e passavano
    # tutte. Il guasto che questo blocco sorveglia e' un altro — una frase che
    # COMINCIA come un comando e non lo e', cioe' l'unico posto in cui un
    # pattern permissivo puo' davvero rubare.
    #
    # Delle venti, **due venivano rubate**, e sono difetti veri corretti in
    # `core/llm/grammar.py`:
    #
    #     "cerca di capirmi"          -> search_files {"query": "di capirmi"}
    #     "chiudi un occhio stavolta" -> close_panel  {"panel": "occhio"}
    #
    # La prima frugava nel filesystem invece di rispondere; la seconda chiudeva
    # un pannello che non esiste. Entrambe silenziose, entrambe al posto di una
    # conversazione — che e' esattamente quello che il commento in cima a questo
    # file dice di sorvegliare, e che nessuna delle venti frasi precedenti
    # poteva scoprire perche' nessuna comincia con un verbo di comando.
    "cerco sempre di arrivare puntuale",
    "non trovo mai il tempo di leggere",
    "apriti cielo",
    "chiudiamo qui il discorso",
    "mostrati un po' piu' paziente",
    "vai tranquillo",
    "alza pure la voce se non mi senti",
    "abbassa i toni per favore",
    "cerca di capirmi",
    "trova il modo di dirglielo",
    "apri bene le orecchie",
    "chiudi un occhio stavolta",
    "mostra un po' di pazienza",
    "vado a fare due passi",
    "spegni la luce quando esci",
    "accendi la fantasia",
    "il file e' importante",
    "workspace non e' una parola italiana",
    "volume alto di poesie",
    "nascondi la delusione",
]


class TestComandi:
    @pytest.mark.parametrize("frase,tool,args", COMANDI, ids=[c[0] for c in COMANDI])
    def test_riconosce_il_comando(self, frase: str, tool: str, args: dict | None) -> None:
        i = parse(frase)
        assert isinstance(i, Intent), f"{frase!r} non riconosciuto"
        assert i.tool == tool, f"{frase!r} -> {i.tool}, atteso {tool}"
        if args is not None:
            assert i.args == args, f"{frase!r} -> {i.args}, attesi {args}"

    def test_almeno_ottanta_comandi(self) -> None:
        assert len(COMANDI) >= 80, f"il corpus ha solo {len(COMANDI)} comandi"


class TestConversazione:
    @pytest.mark.parametrize("frase", CONVERSAZIONALI)
    def test_va_a_t1(self, frase: str) -> None:
        """`None` e' la risposta CORRETTA: questa frase deve diventare
        conversazione, non un'azione."""
        i = parse(frase)
        assert i is None, (
            f"{frase!r} e' stata rubata a T1 da `{i.tool}`. Una regola nuova ha un "
            f"pattern troppo largo, oppure e' finita sopra `search_files`."
        )

    def test_almeno_venti_conversazionali(self) -> None:
        assert len(CONVERSAZIONALI) >= 20


#: Dove finisce la misura. `docs/acceptance/` e non `shots/`, che git ignora:
#: un numero che sparisce al primo `clean` non e' una registrazione.
ESITO = Path(__file__).resolve().parent.parent / "docs" / "acceptance" / "T0-CORPUS.json"
#: L'impronta copre la grammatica e il corpus: sono le due cose che, cambiando,
#: rendono vecchio il numero.
FONTI = ("core/llm/grammar.py", "tests/t0_corpus.py")


def _registra(n: int, mediana: float, p95: float, massimo: float) -> None:
    """Scrive la misura — **solo se e' cambiato cio' che misura**.

    ⚠️ Prima riscriveva sempre, e i numeri di latenza dipendono dal carico
    della macchina: `git status` non era mai pulito dopo un giro di test, e una
    modifica vera a questo file si sarebbe nascosta in mezzo al rumore.
    Misurato: due esecuzioni di fila davano 0,0033 e 0,0057 ms di mediana con
    l'impronta identica.

    L'impronta dice **che cosa** e' stato misurato. Se non e' cambiata, il
    numero registrato descrive ancora quei sorgenti, e sostituirlo con quello
    di oggi non aggiunge niente: aggiunge solo una riga di diff.
    """
    radice = ESITO.parent.parent.parent
    h = hashlib.sha256()
    for f in FONTI:
        h.update((radice / f).read_bytes())
    impronta = h.hexdigest()[:16]
    if ESITO.exists():
        try:
            vecchio = json.loads(ESITO.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            vecchio = {}
        if vecchio.get("impronta") == impronta:
            return
    ESITO.write_text(json.dumps({
        "_": "GENERATO da tests/t0_corpus.py — non modificare a mano",
        "fonti": list(FONTI),
        "impronta": impronta,
        "frasi": n,
        "comandi": len(COMANDI),
        "conversazionali": len(CONVERSAZIONALI),
        "budget_ms": 10.0,
        "mediana_ms": round(mediana, 4),
        "p95_ms": round(p95, 4),
        "max_ms": round(massimo, 4),
        # ⚠️ Questa e' la misura del PARSER su testo, non del microfono.
        # La catena vera — acustica, wake, STT, T0 — non e' mai stata accesa:
        # vedi docs/acceptance/T0-E-IL-MICROFONO.md.
        "misura": "parse() su testo, non dal microfono",
        "python": platform.python_version(),
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


class TestLatenza:
    def test_mediana_sotto_dieci_millisecondi(self) -> None:
        """§7.6: sotto i 10 ms. E' il numero che tiene in piedi §7.5."""
        frasi = [c[0] for c in COMANDI] + CONVERSAZIONALI
        for f in frasi:                                   # scalda le regex
            parse(f)

        tempi = []
        for f in frasi:
            t0 = time.perf_counter()
            parse(f)
            tempi.append((time.perf_counter() - t0) * 1000)

        mediana = statistics.median(tempi)
        p95 = sorted(tempi)[int(len(tempi) * 0.95)]
        print(f"\n  T0 su {len(frasi)} frasi: mediana {mediana:.4f} ms · p95 {p95:.4f} ms")
        assert mediana < 10.0, f"mediana {mediana:.3f} ms, il budget e' 10 ms"

        # ⚠️ IL NUMERO SI REGISTRA, e prima si stampava e si perdeva.
        # §22 chiede «latenza mediana» fra le misure della Fase 3, e una misura
        # che vive solo nell'output di pytest non si puo' confrontare col mese
        # prossimo. Stessa forma di DENSITA.json: l'impronta dice CHE COSA e'
        # stato misurato, cosi' un numero vecchio si riconosce.
        _registra(len(frasi), mediana, p95, max(tempi))

    def test_non_solleva_su_nulla(self) -> None:
        """E' sul percorso della voce: un'eccezione qui zittisce JARVIS."""
        for strano in ["", "   ", "\x00", "a" * 10_000, "?!?!", "123", "\n\t",
                       "cerca", "workspace", "volume"]:
            parse(strano)          # basta che non sollevi


class TestOrdineDelleRegole:
    def test_search_files_resta_in_fondo(self) -> None:
        """§7.6 nota 1: il suo pattern e' il piu' permissivo. In cima
        catturerebbe tutto, e questo test lo impedisce a chi riordinera'."""
        from core.llm.grammar import regole

        tools = [t for _, t in regole()]
        assert tools[-1] == "search_files", (
            f"search_files non e' l'ultima regola ma la {tools.index('search_files') + 1}a: "
            f"il suo pattern permissivo si mangerebbe le regole che seguono"
        )

    def test_un_comando_specifico_batte_la_ricerca(self) -> None:
        """La prova che l'ordine serve davvero."""
        assert parse("cerca il file contratto").tool == "search_files"
        assert parse("come stiamo").tool == "doctor"
