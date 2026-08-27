"""Il consolidamento notturno aveva mani che §5.5 gli aveva vietato.

`docs/SPEC.md:403`, alla lettera:

    «Usa un processo T2 dedicato con --allowedTools "": legge e scrive solo
    tramite i tool memoria dell'allowlist, mai direttamente.»

Riceveva `_t2_meta`, cioè `Read,Edit,Bash(git *),Glob,Grep`.

⚠️ **Misurato, non dedotto.** Il 27 agosto, in una copia scratch con lo stesso
`.claude/settings.json` del progetto e la stessa riga di comando di `ClaudeT2`:

    Write                        → negato
    Bash generico                → negato
    Edit                         → RIUSCITO, il file è stato modificato
    Bash(git add && git commit)  → RIUSCITO, commit creato

`--allowedTools` regge — `permissions.allow` di `settings.json` **non lo
allarga**, e su questo il commento a `claude_t2.py:43` aveva ragione. Ma `Edit`
e `Bash(git *)` sono **dentro** quell'allowlist, e girano senza che nessuno
confermi.

Quindi il consolidamento poteva modificare un file qualunque del repository e
committarlo, alle 04:00, con nessuno davanti. A tenerlo dentro `topics/` era
**il testo del prompt** — cioè un confine imposto da una frase invece che da un
meccanismo, che è la forma di difetto che questo progetto rifiuta ovunque.

E non gli servivano: `Consolidatore.esegui()` passa gli scambi **dentro il
compito** e scrive con `MemoryStore.scrivi_topic`.
"""

from __future__ import annotations

from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent


def _sorgente(nome: str) -> str:
    return (RADICE / nome).read_text(encoding="utf-8")


def _senza_commenti(s: str) -> str:
    """Il codice, non le spiegazioni."""
    fuori = []
    for r in s.splitlines():
        t = "" if r.lstrip().startswith(("#", "#:")) else r.split("#", 1)[0]
        fuori.append(t)
    return "\n".join(fuori)


class TestIlConsolidamentoNonHaMani:
    def test_ha_un_T2_SUO_con_zero_tool(self) -> None:
        s = _senza_commenti(_sorgente("core/engine.py"))
        assert 'self._t2_conso = ClaudeT2(self._governor, RADICE, tool="", max_turns=1,' in s

    def test_e_il_consolidatore_riceve_QUELLO(self) -> None:
        """La prova che conta: non basta costruirlo, deve arrivargli."""
        s = _senza_commenti(_sorgente("core/engine.py"))
        assert "Consolidatore(self._memoria, self._t2_conso," in s
        assert "Consolidatore(self._memoria, self._t2_meta," not in s

    def test_il_meta_conserva_le_mani_che_gli_SERVONO(self) -> None:
        """⚠️ Non si toglie a tutti: `brief_me` e `needs_attention` guardano
        `git log` e `docs/acceptance/`, e senza `Read` e `Bash(git *)` non
        potrebbero. Il difetto era il consolidamento, non T2.

        Ma `Edit` non serviva a nessuno dei tre chiamanti — i due meta-comandi
        GUARDANO e basta — ed e' stato tolto: un tool di scrittura che nessuno
        usa e' superficie regalata."""
        from core.llm.claude_t2 import TOOL_CONSENTITI

        assert "Read" in TOOL_CONSENTITI and "Bash(git *)" in TOOL_CONSENTITI
        assert "Edit" not in TOOL_CONSENTITI
        assert "Write" not in TOOL_CONSENTITI

    def test_il_default_di_ClaudeT2_e_ancora_quello(self) -> None:
        """Se qualcuno svuotasse `TOOL_CONSENTITI` invece di passare `tool=""`,
        questo test resterebbe verde e il precedente no: sono la stessa
        proprietà da due lati."""
        import inspect

        from core.llm.claude_t2 import TOOL_CONSENTITI, ClaudeT2

        assert inspect.signature(ClaudeT2.__init__).parameters["tool"].default \
            == TOOL_CONSENTITI

    def test_max_turns_1_non_e_un_numero_SCELTO(self) -> None:
        """Con zero tool non c'è niente su cui iterare: un secondo turno non
        potrebbe fare nulla di diverso dal primo."""
        s = _senza_commenti(_sorgente("core/engine.py"))
        i = s.index('self._t2_conso = ClaudeT2(')
        assert 'tool=""' in s[i:i + 200] and "max_turns=1" in s[i:i + 200]


class TestIlConsolidatoreNonHaBISOGNOdiMani:
    def test_gli_scambi_viaggiano_nel_COMPITO(self) -> None:
        """Se il modello dovesse LEGGERE le sessioni, `Read` servirebbe. Non
        deve: il testo glielo passa il core."""
        s = _sorgente("core/memory/consolidate.py")
        dopo = s.split("async def esegui", 1)[1]
        assert 'compito = (' in dopo and '+ testo' in dopo

    def test_e_la_scrittura_la_fa_il_CORE(self) -> None:
        s = _senza_commenti(_sorgente("core/memory/consolidate.py"))
        assert "self._store.scrivi_topic(" in s
        assert "self._store.registra_iniziativa(" in s
