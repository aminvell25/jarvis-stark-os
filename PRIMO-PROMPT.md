> ## ⚪ STORICO — 2 settembre 2026
>
> Istruzioni del giorno zero: descrivono la creazione di un repo che esiste
> già. Le regole operative correnti stanno in `CLAUDE.md` e in
> `docs/PROTOCOLLO-DI-LAVORO.md`; lo stato corrente in
> `docs/STATO-DEI-PIANI.md`.

# Primo prompt per Claude Code

## Prima di incollarlo

```
cd jarvis-os
claude
```

Poi, dentro Claude Code:

```
/model opus
/effort high
```

Poi prema **Shift+Tab** finche' non entra in **plan mode**. Solo a quel punto
incolli il prompt qui sotto.

---

## Il prompt — copiare da qui

Agisci come un senior engineer che costruisce un sistema destinato a durare anni, non un prototipo da dimostrare. Il tuo criterio non e' "funziona": e' "il me stesso di fra sei mesi capisce perche' e' fatto cosi'". Quando una scelta ha alternative, le dichiari e motivi quella che prendi. Quando qualcosa nella specifica ti sembra sbagliato, lo dici PRIMA di implementarlo, non dopo.

Leggi `CLAUDE.md` e `docs/SPEC.md` per intero prima di scrivere qualsiasi cosa. Poi conferma di aver compreso questi cinque invarianti, con parole tue e in una riga ciascuno:

1. perche' T1 e' un processo persistente e non `claude -p` per turno
2. perche' il testo non va rasterizzato in WebGL
3. perche' l'allowlist non puo' essere sostituita da una denylist
4. cosa distingue la Famiglia A dalla Famiglia B nei riferimenti visivi
5. perche' il chunker TTS va solo davanti a Kokoro

**Ambito di questa sessione: SOLO le Fasi 0 e 0b di `docs/SPEC.md` §22.** Nient'altro. Non anticipare la Fase 1.

**Fase 0 — consegne:**

- `pyproject.toml` con uv, Python 3.12, dipendenze del solo core: asyncio, pydantic, structlog, psutil, websockets, tomlkit, watchdog, pytest
- albero delle directory secondo SPEC §21.1, con `__init__.py` dove servono e file vuoti dove no
- `core/platform/base.py` con i Protocol `SandboxRunner`, `AudioIO`, `Paths`, `Sensors` (SPEC §23) e `core/platform/linux.py` che implementa solo `Paths` e `Sensors`. Sandbox e audio restano stub che sollevano `NotImplementedError`.
- `core/settings.py`: carica `settings.toml` e `secrets.toml` con permessi 0600, valida con pydantic secondo lo schema di SPEC §8, emette un evento su cambio file via watchdog. **Le chiavi non devono mai comparire nei log ne' nelle `__repr__` dei modelli** — usa `SecretStr`.
- `ui/src/style/tokens.css`: la §10.1 di SPEC, completa, verbatim. **Questo file esiste prima di qualunque altro CSS.**
- test: caricamento, validazione, hot reload, e un test che verifica che la chiave non compaia in `repr()` ne' in un log strutturato

**Fase 0b — consegne:**

- `ui/gallery.html` con routing `?component=`, `&grid=1`, `&tokens=audit`
- lo script di audit: scorre il CSS calcolato di ogni elemento e colora di magenta cio' che non corrisponde a un token. Un componente conforme e' invisibile all'audit
- un componente di prova volutamente **non conforme** (border-radius, colore letterale, font fuori scala) per dimostrare che l'audit lo cattura
- `npm run shot` con Playwright
- verifica che `docs/design-reference/README.md` esista e sia coerente con le immagini presenti

**Non fare in questa sessione:** nessun componente reale, nessuna voce, nessun Electron, nessun 3D, nessun WebSocket.

**Procedura:** sei in plan mode. Presentami il piano con l'elenco esatto dei file che creerai e cosa conterra' ciascuno. Aspetta la mia approvazione. Poi esegui, e al termine riporta l'esito dei criteri di accettazione di entrambe le fasi, uno per uno, dichiarando esplicitamente quelli che non hai potuto verificare.

---

## Prompt delle fasi successive

Stesso schema, tre righe:

> Ambito: SOLO Fase N di `docs/SPEC.md` §22. Leggi `CLAUDE.md`, la §N di SPEC, e `docs/acceptance/FASE-(N-1).md`.
> Entra in plan mode, presentami il piano, aspetta l'approvazione.
> Al termine riporta i criteri di accettazione uno per uno, dichiarando quelli non verificabili.

## Per i componenti visivi (Fase 5)

Aggiungere sempre:

> Riferimento visivo: `docs/design-reference/famiglia-a/<file>.png`, riquadro <quale>.
> Dopo l'implementazione: rendi in `gallery.html?component=<nome>&tokens=audit`, fai lo screenshot, **LEGGI il PNG**, confrontalo col riferimento, e riporta la checklist SPEC §11.8 punto per punto. Se un punto fallisce, riscrivi il componente. Non rattoppare.

Il "LEGGI il PNG" va scritto esplicitamente. Senza, Claude Code fa lo screenshot e non lo guarda.

## Protocollo di sessione

```
1. /clear                    contesto pulito
2. /model e /effort          opus+high per architettura, sonnet+medium per implementazione
3. Shift+Tab                 plan mode
4. prompt della fase         ambito ristretto
5. leggo il piano, correggo, approvo
6. esecuzione
7. verifica dei criteri, uno per uno
8. scrivo docs/acceptance/FASE-NN.md
9. git commit
10. /clear
```

Il punto 1 non e' formale: portare il contesto della Fase 2 dentro la Fase 3
fa "ricordare" al modello decisioni provvisorie come se fossero definitive.
`CLAUDE.md` e `docs/SPEC.md` bastano a ricostruire il contesto.

## Quattro segnali che la sessione sta degenerando

| Segnale | Cosa fare |
|---|---|
| Implementa la fase successiva senza chiederlo | interrompa, `/clear`. Ha perso l'ambito |
| Scrive valori letterali di colore o spaziatura | `CLAUDE.md` non e' piu' nel contesto attivo. `/clear` e ricominci la fase |
| Dichiara un criterio "verificato" senza mostrare come | glielo faccia dimostrare |
| Propone una dipendenza non in SPEC §4 | decide Lei, non lui |
