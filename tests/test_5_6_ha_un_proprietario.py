"""§5.6 — la scadenza del token aveva due gestori, e quello che riferisce era muto.

`Supervisore.su_evento()` **non aveva chiamanti**: né T1 né T2 gli passavano un
solo evento dello stream. Eppure è lui che:

- annuncia a voce con una voce che non dipende da Claude (§5.6);
- pubblica l'`agent.advisory`;
- fa uscire il core col codice 41, che `RestartPreventExitStatus` riconosce;
- risponde a `jarvis doctor` con `stato_doctor()`.

Nel frattempo T1 aveva un suo ramo — una ricerca per sottostringa
`"authentication" in json.dumps(e)` — che degradava e annunciava per conto suo.

Il risultato peggiore non è la duplicazione: è che **`jarvis doctor` avrebbe
detto `auth ok` con T1 già degradato**, perché il supervisore non lo sapeva. E
il core non sarebbe uscito col codice 41, quindi systemd lo avrebbe rilanciato
contro il muro — che è esattamente ciò che §5.6 esiste per impedire.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.llm.supervisor import AUTH_ERRORS, USCITA_AUTH, Supervisore

EVENTO_AUTH = {"type": "system", "subtype": "api_retry",
               "error": "authentication_failed"}
EVENTO_RITARDO = {"type": "system", "subtype": "api_retry", "error": "overloaded"}


def _supervisore():
    detto: list[str] = []
    pubblicato: list[dict] = []
    uscite: list[int] = []

    async def parla(f): detto.append(f)
    async def pubblica(m): pubblicato.append(m)

    s = Supervisore(parla=parla, pubblica=pubblica, esci=uscite.append)
    return s, detto, pubblicato, uscite


class TestIlProprietarioRICEVE:
    def test_T1_gli_passa_gli_eventi(self) -> None:
        s = (Path(__file__).resolve().parent.parent / "core" / "engine.py"
             ).read_text(encoding="utf-8")
        assert "su_evento=self._supervisore.su_evento," in s, (
            "T1 non parla col supervisore: `jarvis doctor` direbbe `auth ok` "
            "con la sessione già degradata"
        )

    def test_anche_i_DUE_T2(self) -> None:
        s = (Path(__file__).resolve().parent.parent / "core" / "engine.py"
             ).read_text(encoding="utf-8")
        assert s.count("su_evento=self._supervisore.su_evento") == 3, (
            "uno dei tre — T1, T2 dei meta-comandi, T2 degli argomenti — non "
            "passa gli eventi al supervisore"
        )

    async def test_lo_stream_di_T2_lo_CHIAMA(self) -> None:
        """La riga sta accanto a `Governor.osserva`: sono due domande diverse
        sullo stesso flusso, e finora la seconda non la faceva nessuno."""
        sorgente = (Path(__file__).resolve().parent.parent / "core" / "llm"
                    / "claude_t2.py").read_text(encoding="utf-8")
        dopo = sorgente.split("self._gov.osserva(e)", 1)[1][:200]
        assert "await self._su_evento(e)" in dopo


class TestT1DELEGA_e_non_annuncia_due_volte:
    async def test_se_il_supervisore_gestisce_T1_TACE(self) -> None:
        """Annunciare due volte sarebbe due metà in disaccordo."""
        from core.llm.claude_t1 import ClaudeT1

        sup, detto, _, uscite = _supervisore()
        annunci: list[str] = []
        t1 = ClaudeT1("sonnet", Path("/tmp"), su_annuncio=annunci.append,
                      su_evento=sup.su_evento)
        gestito = await t1._su_evento(EVENTO_AUTH)

        assert gestito is True
        assert len(detto) == 1, "il supervisore non ha annunciato"
        assert annunci == [], f"T1 ha annunciato anche lui: {annunci}"
        assert uscite == [USCITA_AUTH], "il core non esce col codice di §5.6"

    async def test_senza_supervisore_T1_ha_ancora_il_suo_RIPIEGO(self) -> None:
        """I test costruiscono T1 da solo, e un T1 che ignorasse un token
        scaduto riproverebbe a ciclo — ciò che §5.6 vieta."""
        from core.llm.claude_t1 import ClaudeT1

        t1 = ClaudeT1("sonnet", Path("/tmp"))
        assert t1._su_evento is None
        assert "authentication" in json.dumps(EVENTO_AUTH).lower()

    def test_il_ramo_di_T1_DELEGA_e_SI_FERMA(self) -> None:
        """⚠️ La prima stesura guardava solo l'ORDINE — che `su_evento` venisse
        prima del ripiego per sottostringa — e **non discriminava**: togliendo
        il corto circuito, T1 avrebbe chiamato il supervisore *e poi* sarebbe
        caduto anche nel proprio ramo, annunciando due volte. L'ordine era
        ancora giusto e il test restava verde.

        Quel che conta non è l'ordine: è che quando il proprietario ha gestito,
        T1 **si ferma**.
        """
        sorgente = (Path(__file__).resolve().parent.parent / "core" / "llm"
                    / "claude_t1.py").read_text(encoding="utf-8")
        dopo = sorgente.split('e.get("subtype") == "api_retry"', 1)[1][:1400]
        assert "and await self._su_evento(e):" in dopo, (
            "T1 chiama il supervisore ma non guarda se ha gestito: cadrà anche "
            "nel proprio ramo e annuncerà due volte"
        )
        delega = dopo.index("and await self._su_evento(e):")
        ripiego = dopo.index('"authentication" in')
        assert delega < dopo.index("return", delega) < ripiego, (
            "manca il `return` fra la delega e il ripiego"
        )


class TestCosaSuccedeQuandoARRIVA:
    @pytest.mark.parametrize("errore", sorted(AUTH_ERRORS))
    async def test_ogni_errore_di_auth_degrada_e_ESCE(self, errore: str) -> None:
        sup, detto, pubblicato, uscite = _supervisore()
        assert await sup.su_evento({"type": "system", "subtype": "api_retry",
                                    "error": errore}) is True
        assert sup.stato == "degraded_llm"
        assert detto and pubblicato[0]["level"] == "critical"
        assert uscite == [USCITA_AUTH]

    async def test_un_ritardo_NON_e_una_scadenza(self) -> None:
        """Un `api_retry` che non è di autenticazione lo guarda il Governor."""
        sup, detto, pubblicato, uscite = _supervisore()
        assert await sup.su_evento(EVENTO_RITARDO) is False
        assert sup.stato != "degraded_llm"
        assert (detto, pubblicato, uscite) == ([], [], [])

    async def test_non_lo_ripete_a_ogni_evento(self) -> None:
        sup, detto, _, uscite = _supervisore()
        for _ in range(3):
            await sup.su_evento(EVENTO_AUTH)
        assert len(detto) == 1 and len(uscite) == 1

    async def test_e_DOPO_non_si_riavvia(self) -> None:
        """Il cuore di §5.6: riprovare un token scaduto non lo fa tornare
        valido, e produce solo un servizio che sbatte contro il muro."""
        sup, *_ = _supervisore()
        assert sup.puo_riavviare is True
        await sup.su_evento(EVENTO_AUTH)
        assert sup.puo_riavviare is False

    async def test_e_jarvis_doctor_lo_SA(self) -> None:
        """Il difetto peggiore era questo: lo stato riferito e lo stato vero
        erano due cose diverse."""
        sup, *_ = _supervisore()
        prima = sup.stato_doctor()
        await sup.su_evento(EVENTO_AUTH)
        assert sup.stato_doctor() != prima
