# L'amnesia si annuncia — ADR-003 chiuso

**Rollback:** `c017a5b`
**Criterio:** ADR-003 azioni 1–4 · «uccidere T1 → riavvio, replay, annuncio;
ripetere N volte → `degraded_llm`».
**Esito: azioni 1, 2, 3 fatte e misurate. L'azione 4 end-to-end è DICHIARATA
NON ESEGUIBILE — e si dice perché.**

---

## 1. Il difetto, con le parole di chi l'ha scritto

`docs/STATO-DEI-PIANI.md` lo chiamava **il peggiore che restasse aperto**, e
ADR-003 lo definisce così:

> Il modo di fallire è il peggiore che questo sistema possa avere: **JARVIS
> continua a rispondere, con la stessa voce e la stessa persona, avendo perso
> la conversazione, e non lo dice.** Un errore rumoroso è recuperabile; questo
> no. Contraddice §16: *«nessuna soglia agisce senza annunciarlo»*.

`core/llm/supervisor.py` conosceva **una** classe su tre: `auth`. Le altre due
— `transient` e `repeated` — non esistevano, e con loro non esisteva né il
replay né l'annuncio. Era il percorso che si prende **ogni volta che T1 non
muore per scadenza OAuth**, cioè in tutti i casi tranne quello già coperto.

E `registra_riavvio()` — l'unica cosa che c'era — **non aveva un chiamante in
produzione**: contava e basta.

## 2. Le tre classi

| classe | quando | che cosa succede |
|---|---|---|
| `auth` | `authentication_failed`, `oauth_org_not_allowed` | `degraded_llm`, nessun riavvio, uscita **41** *(era già così)* |
| `transient` | OOM, crash, stream rotto | riavvio, **replay dei soli fatti fissati**, **annuncio** a `warn` |
| `repeated` | ≥ 3 riavvii in 10 minuti | `degraded_llm`, annuncio `critical`, ~~uscita **42**~~, stop |

> ⚠️ **CORRETTO il 28 agosto 2026, per decisione dell'utente.** L'uscita 42 non
> c'è più: per un guasto non-auth ripetuto **il core resta vivo** in
> `degraded_llm`. §5.6 e §16.1b dichiarano che lì frasi-comando, T0, file e
> telemetria continuano a funzionare, e uscire spegneva tre sottosistemi sani
> perché il quarto non partiva. Il freno del loop non era mai stato il codice
> d'uscita. Vedi `docs/SPEC.md` §16 e la rev 5.38.

### Perché una finestra e non un contatore

> Tre riavvii in dieci minuti sono un guasto; tre in tre giorni sono la vita
> normale di un processo.

Un contatore non sa dimenticare. `_quando` tiene gli **istanti**, e ciò che
esce dalla finestra sparisce. Il test `test_la_finestra_DIMENTICA` fa dieci
riavvii distanziati e verifica che lo stato resti `nominal`.

### Perché un orologio monotono

Qui la domanda è **quanto tempo è passato**, non che ora è, e l'ora di sistema
può saltare all'indietro. È la stessa distinzione appena applicata dall'altra
parte del sistema in `ui/src/desk/orologio.js`, dove `Date.now()` resta a
misurare le durate e l'ora viene dal core.

L'orologio arriva **per funzione**, così un test lo muove di dieci minuti senza
aspettarli: aspettare dieci minuti veri non è una prova, è un'attesa.

## 3. La frase, che è la sostanza

```
Signore, ho dovuto riavviare la sessione.
Ho conservato le Sue preferenze, non la conversazione.
```

Dice **due** cose e non una: che cosa è andato perso e che cosa è rimasto. Dire
solo «ho riavviato» lascerebbe all'utente il compito di indovinare che cosa
ricordo ancora — e un test lo pinna, perché una frase è codice quanto il resto.

Passa dal **TTS locale**: se T1 è morto, il percorso vocale non può dipendere da
lui. È la stessa proprietà che §5.6 già sfrutta per l'annuncio dell'auth.

**L'annuncio viene prima del replay**, e l'ordine è verificato: se il replay
fallisse, l'utente ha comunque sentito che la conversazione non c'è più.

## 4. Il replay: i fatti, mai i turni

ADR-003 azione 2, e l'**invariante 17** — «non duplicare la gestione del
contesto di T1» — decide la forma: `fatti_fissati` e `reinietta` arrivano **per
funzione**, non come oggetti. Il supervisore non sa che cosa sia un
`ContextPruner`; il contesto conversazionale resta di Claude Code, i fatti
fissati restano dell'utente.

Se non c'è niente da rimettere **non si chiama nessuno**: reiniettare una lista
vuota scriverebbe nel contesto nuovo una riga che non dice niente, e il budget
di §5.5 è di qualcuno.

## 5. Il secondo codice di uscita

> ⚠️ **QUESTA SEZIONE È SUPERATA — 28 agosto 2026.** Non c'è un secondo
> codice di uscita: il 42 è stato tolto, e per un guasto non-auth ripetuto il
> core **resta vivo** in `degraded_llm`. Due frasi qui sotto sono ora false:
> che `repeated` esca con 42, e che «senza il 42 systemd rilancerebbe
> comunque». La seconda lo era già in parte — **il freno del loop non è mai
> stato il codice d'uscita**: è `Supervisore.puo_riavviare` più la guardia di
> `ClaudeT1.ask()`, e sono freni dentro il processo, che funzionano anche col
> core avviato a mano fuori da systemd. Vedi `docs/SPEC.md` §16 e la rev 5.38.


`repeated` esce con **42**, non con 41. Due numeri perché le cause sono due e
chi legge i log deve poterle distinguere. Entrambi in
`RestartPreventExitStatus`: senza il 42, dopo tre cadute in dieci minuti
systemd rilancerebbe comunque e la classe `repeated` non fermerebbe niente.

Il test che verificava «la unit dice lo stesso numero del supervisore» adesso
verifica **entrambi**, ed è la stessa guardia di prima allargata: due costanti
uguali in due file diversi divergono al primo che le tocca.

## 6. Che cosa NON è stato fatto, e perché

**L'azione 4 di ADR-003 — «uccidere T1 con SIGKILL → riavvio, replay,
annuncio» — non è eseguibile oggi**, e non per mancanza di tempo:

- `core/engine.py` compone T1 **solo se le impostazioni lo dicono**, e in questa
  macchina non lo dicono: `self._t1 = None`;
- `reinietta` resta quindi `None`, perché un replay senza nessuno a cui parlare
  sarebbe una riga che finge di funzionare;
- e la voce **non è mai stata accesa col microfono vero** — è la voce ⑤ di
  `STATO-DEI-PIANI.md`, ancora aperta.

Quindi: la **macchina a stati** è completa e misurata da ventisei asserzioni;
il **cablaggio** al processo vero si chiude quando T1 gira. Il documento lo dice
invece di lasciar credere che il criterio sia verde — §11.7 regola 4, *non
misurabile* non conta come *soddisfatto*.

Ciò che è già cablato: `engine.py` passa `fatti_fissati` dal `ContextPruner`
vero, quindi il giorno in cui T1 parte manca **una sola** funzione.

## 7. Verifica

| | |
|---|---|
| `tests/test_supervisor.py` | **26 passed** (erano 16) |
| le prove bocciano? | tolto l'annuncio dal `transient`: 2 rossi |
| `uv run pytest -q` | **660 passed** |
| `core.engine` importa col `ContextPruner` cablato | sì |

## 8. Dichiarato aperto

- **Azione 4 end-to-end**: serve T1 in esecuzione. Vedi §6.
- **La soglia è 3 riavvii in 600 s**, e ADR-003 lo dice: «se in esercizio i
  riavvii `transient` risultassero rari, la soglia `repeated` va abbassata».
  Nessun esercizio, nessun dato: il numero è quello dell'ADR, non una misura.
> ### ⚠️ CHIUSO il 27 agosto 2026 — e il difetto era peggiore del dichiarato
>
> Questo documento diceva che l'azione 4 non era verificata perché serviva T1 in
> esecuzione. Il motivo vero era un altro: **`riavvia_dopo_guasto` non aveva un
> chiamante in produzione**, e `ask()` faceva `if not self.vivo: await
> self.start()` dentro il `try`.
>
> Cioè: T1 moriva, la chiamata successiva ne apriva uno **nuovo con la sessione
> vuota**, e JARVIS rispondeva con la stessa voce avendo perso la conversazione
> — senza dirlo. Il modo di fallire che questo ADR chiama «il peggiore che
> questo sistema possa avere» non era solo non verificato: **era la strada
> normale**.
>
> Trovato da `scripts/orfani.py`, rimesso nel repo lo stesso giorno.
>
> Adesso le due maniere di non essere vivo si distinguono: `_proc is None` —
> mai avviato o fermato di proposito — si avvia e basta; `returncode` non nullo
> passa da `riavvia_dopo_guasto`, che reinietta i **soli** fatti fissati e
> annuncia. E la chiamata sta **prima** di `_occupato = True`, o la rientranza
> di `ask()` dentro il riavvio solleverebbe «T1 è già impegnato».

- **`reinietta` è `None` in produzione.** È dichiarato nel codice e qui.
