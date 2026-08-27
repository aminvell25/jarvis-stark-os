"""`--allowedTools` non è un confine: è una richiesta.

`core/llm/claude_t2.py` commentava `TOOL_CONSENTITI` con «ristretti ma reali»,
e la parola «confine» era sottintesa. Misurato il 27 agosto con quella stessa
riga di comando — `--permission-mode dontAsk`, in una copia scratch con lo
stesso `.claude/settings.json` del progetto:

    Write                                        negato
    Bash(printf 'OK' > prova.txt && cat ...)     negato
    Bash(cd ... && ls -la && cat ...)            negato
    Bash(git add -A && git commit -m zero)       RIUSCITO
    Bash(echo PERIMETRO_APERTO)                  RIUSCITO
    Edit                                         RIUSCITO

`echo` non compare né in `--allowedTools` né in `permissions.allow`, e passa.
`ls` e `cat` compaiono in `permissions.allow`, e non passano. **Il perimetro
reale non è nessuna delle due fonti che questo progetto dichiara**: lo decide
l'ambiente di Claude Code, e da qui non si enumera.

Questo file non prova quel perimetro — non è nostro. Prova le due cose che
restano vere e che JARVIS controlla:

1. **che cosa chiediamo**, che è l'unica leva onesta;
2. che il confine degli EFFETTI resta l'allowlist del core con la conferma di
   §6.2, dove i tool di Claude Code non passano affatto.
"""

from __future__ import annotations

from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent


class TestChiediamoSoloCioCheServe:
    def test_niente_tool_di_SCRITTURA(self) -> None:
        """⚠️ `Edit` c'era e non serviva a nessuno dei tre chiamanti:
        `_t2_conso` gira con zero tool, `_t2_argomenti` pure, e i due
        `META_COMANDI` chiedono di GUARDARE il log di git e i documenti in
        `docs/acceptance/`.

        Un tool di scrittura che nessun chiamante usa è superficie regalata — e
        il consolidamento notturno l'ha avuto in mano per giorni, alle 04:00,
        con nessuno davanti.
        """
        from core.llm.claude_t2 import TOOL_CONSENTITI

        for scrittura in ("Edit", "Write", "NotebookEdit"):
            assert scrittura not in TOOL_CONSENTITI, (
                f"{scrittura} e' tornato: quale chiamante lo usa?"
            )

    def test_e_conserva_quelle_che_SERVONO(self) -> None:
        from core.llm.claude_t2 import TOOL_CONSENTITI

        assert "Read" in TOOL_CONSENTITI
        assert "Bash(git *)" in TOOL_CONSENTITI

    def test_i_due_META_COMANDI_sono_domande_di_SOLA_LETTURA(self) -> None:
        """La ragione per cui togliere `Edit` non toglie niente. Se un
        meta-comando cominciasse a chiedere di SCRIVERE, questo test lo dice
        prima che qualcuno rimetta il tool «perché serviva»."""
        from core.engine import Engine

        for quale, testo in Engine.META_COMANDI.items():
            basso = testo.lower()
            assert "guarda" in basso, f"{quale} non guarda: che cosa fa?"
            for scrivere in ("scrivi", "crea ", "modifica", "cancella",
                             "sposta", "commit"):
                assert scrivere not in basso, (
                    f"{quale} chiede di {scrivere.strip()}: allora serve un "
                    "tool di scrittura, e va deciso, non trovato"
                )


class TestIlConfineVEROstaNelCore:
    def test_i_tool_di_claude_code_NON_sono_nel_registro(self) -> None:
        """La distinzione che il commento vecchio confondeva: `Read`, `Edit`,
        `Bash` sono i tool di **Claude Code**, non i 27 del registro di JARVIS.
        Non passano da `registry.invoke()`, quindi non incontrano né l'allowlist
        né la conferma di §6.2 — e non ne fanno parte."""
        from core.llm.claude_t2 import TOOL_CONSENTITI
        from core.tools import registry

        nomi = set(registry.names())
        for t in ("Read", "Bash", "Glob", "Grep"):
            assert t not in nomi, (
                f"{t} e' finito nel registro: due allowlist per la stessa cosa"
            )
        assert "Read" in TOOL_CONSENTITI, "questo test misura la cosa sbagliata"

    def test_il_commento_non_promette_piu_un_CONFINE(self) -> None:
        """Un commento che dice «ristretti ma reali» fa credere a chi legge che
        quella stringa sia la superficie di attacco. Non lo è, ed è misurato."""
        s = (RADICE / "core" / "llm" / "claude_t2.py").read_text(encoding="utf-8")
        testa = s.split("TOOL_CONSENTITI =", 1)[0]
        assert "non e' un confine" in testa.lower() or "richiesta" in testa.lower()
        assert "PERIMETRO_APERTO" in testa, "manca la misura che lo dimostra"
