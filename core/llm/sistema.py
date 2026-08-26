"""La cornice con cui il CORE parla a T1 — §7.4, e la meta' mancante del barge-in.

## Il difetto

Il barge-in di §7.4 esiste e funziona: due gate, cinque blocchi consecutivi e
una soglia dedicata, tarati su novanta secondi di eco misurata
(`docs/acceptance/BARGE-IN-DUE-GATE.md`). Quando il Signore parla sopra JARVIS,
JARVIS tace.

Ma **la sessione di T1 non lo sa**. `ClaudeT1._drena()` consuma cio' che resta
della generazione abbandonata e lo scarta: dal punto di vista del modello quella
risposta e' stata **detta per intero**. Al turno dopo JARVIS puo' dire «come Le
dicevo» riferendosi a una spiegazione che nessuno ha udito, e la memoria su
disco (`sessions/`, che registra `testo_detto`) e la sessione del modello
tengono **due versioni diverse della stessa conversazione**.

§7.4 lo nomina. Una meta' era chiusa — `text_spoken` finisce in memoria —
e l'altra era aperta.

## Perche' una CORNICE e non una frase

La nota va nel turno successivo, che e' un messaggio `user`: il formato
`stream-json` di §5.2 non ha un ruolo «system» a meta' conversazione. Quindi la
nota viaggia dentro il turno del Signore, e **il rischio e' che il modello
creda che l'abbia detta lui** — che sarebbe peggio di non dirgliela affatto.

Tre proprieta', e nessuna e' cortesia:

1. **Dichiarata**: la prima riga dice in italiano che non sono parole del
   Signore. Un tag da solo non basta: un modello che non ha mai visto quel tag
   lo tratterebbe come testo.
2. **Non falsificabile**: `core/llm/untrusted.py` neutralizza
   `<sistema_jarvis>` dentro il contenuto non fidato, esattamente come
   neutralizza la propria chiusura. Un titolo di giornale non puo' prendere la
   voce del core.
3. **Assente quando non serve**: senza interruzione non c'e' nota. Una cornice
   a ogni turno diventa rumore, e il rumore si ignora.
"""

from __future__ import annotations

from core.llm.untrusted import APERTURA_SISTEMA, CHIUSURA_SISTEMA


def nota_di_interruzione(udito: str, misurato: bool) -> str:
    """La cornice da anteporre al turno dopo un'interruzione.

    `misurato` distingue **due cose diverse**, e la distinzione va detta al
    modello invece che nascosta:

    - `True` — il provider ha riportato `text_spoken`, cioe' cio' che ha
      **davvero pronunciato** prima di essere zittito. E' una misura.
    - `False` — il provider non lo riporta (e' il caso del TTS locale), e cio'
      che sappiamo e' il testo **mandato al sintetizzatore**. E' un limite
      superiore: qualcosa era ancora in coda quando la voce si e' spenta.

    Dire «ha udito» nel secondo caso sarebbe un'affermazione piu' forte del
    dato.
    """
    udito = (udito or "").strip()
    if udito:
        quanto = (f"Il Signore ha udito soltanto questo: «{udito}»"
                  if misurato else
                  f"Di quella risposta gli e' arrivato al piu' questo, e forse "
                  f"meno: «{udito}»")
    else:
        quanto = "Non e' arrivata a udirne nulla."
    return (
        f"{APERTURA_SISTEMA}\n"
        "Nota del sistema, non parole del Signore.\n"
        "La tua risposta precedente e' stata interrotta: Le ha parlato sopra e "
        "la voce si e' fermata.\n"
        f"{quanto}\n"
        "Non dare per udito il resto, e non riprendere da dove eri: rispondi a "
        "cio' che ha appena detto.\n"
        f"{CHIUSURA_SISTEMA}"
    )
