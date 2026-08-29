"""Consolidamento notturno — SPEC §5.5.

Il `ContextPruner` e' **reattivo**: pota quando il budget e' saturo, e cio' che
scarta e' perso. Questo passaggio e' **programmato**: gira quando nessuno usa il
sistema e ha tempo di ragionare su cosa vale la pena conservare.

> «Potatura sotto pressione e consolidamento a mente fredda non sono lo stesso
> lavoro. Servono entrambi.»

Idea adottata da `Grominet95/jarvis-OS` (`docs/ANALISI-REPO-E-TECNOLOGIE.md`
§1.1①), **reimplementata da zero** come impone l'invariante 30.

⚠️ **NON TOCCA I FATTI FISSATI**: sono dell'utente (§5.5).

⚠️ **SE NON GIRA, LO DICE** (rilievo R33). Passa dal Governor come ogni T2
(invariante 16), e se la finestra e' esaurita o il token e' scaduto nella notte
non gira. §16 vieta le degradazioni silenziose: emette un `agent.advisory`, e
la mattina dopo si sa perche' la memoria non e' stata consolidata.

⚠️ **SCRIVE SENZA CONFERMA UMANA, ed e' una tensione dichiarata.** L'invariante
3 vuole conferma per ogni `side_effect=True`, ma alle 04:00 non c'e' nessuno che
confermi. La si scioglie restringendo il raggio: scrive **solo** dentro
`topics/`, non tocca i fatti fissati, e ogni scrittura finisce in
`initiatives/`, visibile al risveglio. E' un compromesso, non una scappatoia, e
sta scritto in `docs/acceptance/FASE-04.md`.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import structlog

from core.llm.governor import QuotaEsaurita
from core.memory.store import MemoryStore

log = structlog.get_logger(__name__)

ORA_DEFAULT = 4          # le 04:00 di §5.5
SEGNAPOSTO = "_ultimo-consolidamento"

#: Da quanto tempo il consolidamento deve essere fermo perche' si consideri
#: **saltato** e si recuperi al primo avvio utile.
#:
#: Non e' un numero scelto: §5.5 dice «ogni notte», quindi il periodo e' un
#: giorno. Piu' vecchio di un giorno vuol dire che una notte e' passata senza
#: che nessuno la attraversasse.
PERIODO_S = 24 * 3600.0


class Consolidatore:
    def __init__(
        self,
        store: MemoryStore,
        t2,
        su_advisory: Callable[[dict], Any] | None = None,
    ) -> None:
        self._store = store
        self._t2 = t2
        self._su_advisory = su_advisory

    def ultimo_run(self) -> float:
        p = self._store.radice / f"{SEGNAPOSTO}.txt"
        try:
            return float(p.read_text().strip())
        except (OSError, ValueError):
            return 0.0

    def saltato(self, adesso: float | None = None) -> bool:
        """Se una notte e' passata senza consolidamento.

        ⚠️ **Esiste perche' il timer da solo non basta.** `_consolida_di_notte`
        dormiva fino alle 04:00, e un `await asyncio.sleep()` non sopravvive a
        un riavvio del processo: riparte da zero. Misurato sul journal, il core
        si e' riavviato **27 volte in tre giorni**, e in sette giorni non c'e'
        un solo consolidamento eseguito — solo il timer armato.
        #
        Il risultato era visibile su disco: `topics/` e `initiatives/` a
        **zero file**. La meta' in uscita della memoria era vuota per un
        difetto di forma — **un'attesa invece di un recupero**.
        #
        Un orologio di parete e non `monotonic`: il timbro si legge fra un
        avvio e l'altro, e `monotonic` riparte a ogni riavvio, cioe' proprio
        nel caso che questa funzione esiste per coprire.
        """
        ora = time.time() if adesso is None else adesso
        # ⚠️ Un timbro nel FUTURO — orologio spostato all'indietro, fuso
        # cambiato — non e' «saltato», e **non serve una guardia per dirlo**:
        # la differenza diventa negativa e non puo' superare `PERIODO_S`.
        #
        # La guardia l'avevo scritta, e la bocciatura ha detto che toglierla non
        # rompeva niente. Un controllo che non puo' cambiare nessun esito non e'
        # prudenza: e' una riga che promette una protezione inesistente a chi la
        # legge.
        return (ora - self.ultimo_run()) > PERIODO_S

    def _segna_run(self) -> None:
        """Il timbro del GIRO, e adesso serve a una domanda sola.

        ⚠️ Rispondeva a due: «quand'e' stato l'ultimo giro?» — che e' la sua, e
        la usa `saltato()` come freno alla frequenza — e «fin dove abbiamo
        consolidato?», che gli era stata data in prestito da `esegui()`. Una
        cifra per due domande diverse regge finche' le due risposte coincidono,
        e qui non coincidevano: una sessione saltata restava indietro rispetto
        al timbro, e spariva.
        """
        (self._store.radice / f"{SEGNAPOSTO}.txt").write_text(str(time.time()))

    def _advisory(self, livello: str, motivo: str, **extra) -> None:
        msg = {"topic": "agent.advisory", "level": livello,
               "reason": f"consolidamento: {motivo}", **extra}
        # ⚠️ `**extra` anche nel log, e non e' simmetria estetica: il
        # `dettaglio` — cioe' PERCHE' una sessione non si e' consolidata —
        # andava solo sull'advisory, che vive sul socket. Con la scrivania non
        # collegata quel motivo spariva, e il 27 agosto e' sparito davvero:
        # «sessione 2026-08-27 non consolidata», e nessuno puo' piu' dire
        # perche'. Il journal e' la cosa che sopravvive.
        log.warning("consolidamento_advisory", motivo=motivo, **extra)
        if self._su_advisory:
            self._su_advisory(msg)

    async def esegui(self, oggi: str | None = None) -> dict[str, Any]:
        """Consolida le sessioni che non hanno ancora un riassunto.

        ⚠️ **Qui c'era una SOGLIA TEMPORALE, e ha mangiato una giornata.**
        `da = self.ultimo_run()` piu' `sessioni_dal(da)`: il timbro e' un
        orologio di parete scritto a fine ciclo, quindi ogni giro saliva sopra
        il `ts` delle sessioni che NON aveva consolidato — quella caduta sul
        ramo `not r.ok`, quella lasciata a meta' da un crash — e le rendeva
        invisibili per sempre.

        **Misurato sul disco vero il 29 agosto**: i 7 turni del 2026-08-27
        avevano `ts` fino a 1787853324, il timbro diceva 1787882411, e i turni
        visibili al giro successivo erano **zero**. In `topics/` c'era solo la
        sessione del 26.

        Adesso la frontiera non e' un numero ma un INSIEME DI NOMI: le sessioni
        senza una riga in `initiatives/`. Con quel cambio spariscono anche tutte
        le domande che il confronto fra `ts` portava con se' — `>=` o `>`,
        l'ordine in cui si lavorano le sessioni, il turno scritto mentre il
        consolidamento gira. Nessuna delle tre si pone piu'.

        ⚠️ **La sessione di OGGI si lascia stare**, ed e' il prezzo dichiarato:
        e' ancora aperta, e riassumerla adesso vorrebbe dire riassumerne meta'.
        Alle 04:00 non cambia niente — la giornata appena finita porta gia' il
        nome di ieri. Cambia per un turno detto dopo mezzanotte: aspetta un giro
        in piu'.

        `oggi` si passa solo dalle prove, come `adesso` in `saltato()`.
        """
        quando = time.strftime("%Y-%m-%d") if oggi is None else oggi
        fatte = self._store.sessioni_consolidate()
        da_fare = [s for s in self._store.sessioni()
                   if s not in fatte and s != quando]
        if not da_fare:
            log.info("consolidamento_niente_da_fare")
            self._segna_run()
            return {"eseguito": False, "motivo": "niente di nuovo", "topic": 0}

        scritti = 0
        letti = 0
        for sessione in da_fare:
            frammenti = self._store.turni_di(sessione)
            letti += len(frammenti)
            testo = "\n".join(
                f"- {f.get('utente','')} -> {f.get('jarvis','')}".strip()
                for f in frammenti if f.get("utente") or f.get("jarvis")
            )
            if not testo.strip():
                continue

            compito = (
                "Riassumi questi scambi in note durevoli, in italiano, in non piu' di "
                "dieci righe. Solo cio' che vale la pena ricordare fra un mese: "
                "preferenze, decisioni, fatti stabili. Ometti le chiacchiere.\n\n"
                + testo
            )
            try:
                r = await self._t2.esegui(compito, f"consolidamento-{sessione}")
            except QuotaEsaurita as exc:
                # R33: la quota e' finita. NON si finge che sia andato bene.
                self._advisory("warn", "quota esaurita, riprovo la prossima notte",
                               dettaglio=str(exc))
                return {"eseguito": False, "motivo": "quota", "topic": scritti}

            if not r.ok or not r.testo:
                self._advisory("warn", f"sessione {sessione} non consolidata",
                               dettaglio=r.errore or "risposta vuota")
                continue

            self._store.scrivi_topic(f"sessione {sessione}", r.testo)
            # Ogni scrittura notturna e' visibile al risveglio: e' cio' che
            # rende accettabile scrivere senza conferma.
            self._store.registra_iniziativa("consolidamento", {
                "sessione": sessione, "turni": len(frammenti),
                "costo_usd": r.costo_usd, "durata_s": r.durata_s,
            })
            scritti += 1

        self._segna_run()
        log.info("consolidamento_fatto", topic=scritti, turni=letti)
        return {"eseguito": True, "topic": scritti, "turni": letti}
