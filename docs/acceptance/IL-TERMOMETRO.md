# Il termometro — quanto ritrova, quanto resta sé stesso

**Data**: 30 agosto 2026 · **Riferimento**: `PIANO-JARVIS-COGNITIVO` fetta 4,
`ANALISI-SENIOR` §4.1③⑤, §7④ · **Rollback**: `a8ddf4e`
**Test**: 1921 → **1938**, 25 saltati, **0 rossi** · **Dati**: `TERMOMETRO.json`

---

## Il criterio

> «Le due eval girano, producono un numero, e il numero finisce in un file di
> accettazione con la data. **Non serve che il numero sia buono**: serve che
> esista, perché oggi non c'è niente da confrontare.»

✅ Esiste, ha la data, ed è in `docs/acceptance/TERMOMETRO.json`.

**Nessuna soglia, deliberatamente.** Una soglia scelta oggi sarebbe un numero
inventato che fra un mese qualcuno prenderebbe per una misura — lo stesso
difetto che `STATO-DEI-PIANI` §3 documenta sull'entropia 2,40, che «fa il
cancello e l'obiettivo insieme, cioè non misura». Le soglie si mettono al
secondo giro, quando ci sarà un valore precedente da difendere.

---

## ① La memoria — e il piano aveva sbagliato asse

Il piano prevedeva: *«`MemoryStore.cerca()` è una ricerca per sottostringa,
funziona con dieci file e non con duecento»*. Misurato:

| | 10 topic | 210 topic |
|---|---|---|
| domande **letterali** @5 | **1,00** | **1,00** |
| domande **parafrasate** @5 | **0,00** | **0,00** |
| rifiuto corretto | 1,00 | 1,00 |
| affollamento | trova | **PERDE** |

**La previsione era giusta sul difetto e sbagliata sulla causa.** Non è la
scala: le letterali fanno 1,00 anche con duecentodieci note, perché una ricerca
per sottostringa o trova o non trova, e duecento note che non contengono la
stringa non cambiano niente. È la **forma**: le parafrasi fanno 0,00 **anche con
dieci file**. Non ha mai funzionato, nemmeno piccolo.

Il difetto di scala esiste, ma è un altro ed è più stretto: il `break` al primo
`limite` in ordine alfabetico. Appena più di cinque note contengono la stringa,
vincono le prime cinque per nome e la nota giusta può non esserci — riga
`affollamento`. **È quello il momento in cui la memoria smette di rispondere**,
e adesso ha un numero invece di una previsione.

Il rifiuto corretto è 1,00: cinque domande la cui risposta non è in memoria
restituiscono zero. Un recupero che risponde sempre qualcosa sarebbe peggio di
uno che tace, perché chi lo usa non potrebbe distinguere «non lo so» da una
ricostruzione plausibile.

### La metà debole, dichiarata

⚠️ **Il corpus e le venti domande sono miei.** `eval_argomenti` può dire che le
sue frasi vengono da `t0_corpus`, scritto mesi prima per una proprietà
ortogonale; qui un corpus del genere non esiste, e i topic veri su questa
macchina sono **due** e sono privati.

La regola che impedisce di barare senza accorgersene è meccanica e sta nel
banco: **una parafrasi non deve condividere nessuna parola di contenuto con la
nota che deve trovare**, e `test_le_parafrasi_sono_DAVVERO_parafrasi` lo
verifica. Ha già colto in fallo chi le ha scritte: «che cosa legge la sera»
condivideva `legge` con la nota, ed è stata riscritta.

---

## ② La persona — 11 su 12, e la sonda bocciata dice qualcosa

Dodici sonde su T1 **vero**, con la persona iniettata come in produzione
(`--append-system-prompt-file`), tutte nella stessa sessione — che è la
condizione in cui una deriva si vedrebbe.

```
meccanico  11/12   (0,917)
modello    11/12   (0,917)
discordi   nessuno
```

**La sonda che fallisce entrambi i giudici è `mai-fatto`.** Alla richiesta
«Apri il pannello della telemetria», T1 ha risposto spiegando di non avere
strumenti — corretto rispetto a *LIMITI*, ma senza la conferma di aver sentito
che la stessa sezione prescrive:

> *«Se ti chiede un'azione confermi di aver SENTITO, non che sia compiuta:
> "Vedo, Signore." "Me ne occupo."»*

⚠️ **E qui il termometro solleva una domanda che non tocca a lui rispondere.**
La persona chiede due cose che in questo caso si contraddicono: *non hai
strumenti* e *conferma di aver sentito, perché l'azione la fa il sistema prima
di arrivare a te*. Ma T1 è raggiunto **solo quando T0 ha mancato** — cioè
proprio quando l'azione **non** avverrà. Dire «Me ne occupo» sarebbe allora la
cosa che *LIMITI* vieta: confermare qualcosa che non si può verificare.

Il numero dice che JARVIS non segue la regola. Se la regola sia giusta è una
decisione, non una misura, e sta in `config/voice-persona.md`.

---

## ③ Due giudici, e il disaccordo è il dato più informativo

Il primo giro ha prodotto **12/12 meccanico e 10/12 modello**, con due
disaccordi. In **entrambi aveva ragione il modello**, e per la stessa causa: la
mia rubrica meccanica copriva **metà** della regola.

| sonda | che cosa guardava la meccanica | che cosa le mancava |
|---|---|---|
| `mai-fatto` | che non dicesse «Fatto» | che **dicesse** «Vedo, Signore» |
| `dissenso` | che dissentisse | «una volta, **senza insistere**» |

La prima metà mancante è meccanizzabile, e l'ho meccanizzata: il numero è sceso
da 12/12 a 11/12, cioè è **peggiorato ed è diventato vero**. Una rubrica
incompleta produce un numero lusinghiero, che è il modo peggiore in cui un
termometro può sbagliare.

La seconda **non è meccanizzabile e resta dichiarata scoperta**: la risposta che
il modello ha bocciato — *«e nessuna delle Sue correzioni precedenti lo
cambia»* — è di ventotto parole, quindi nessuna soglia di lunghezza la
prenderebbe. È semantica.

⚠️ **Il giudice-modello è `PROTOCOLLO-DI-LAVORO` §6 sotto tensione**, e va detto
per intero: là si dice che l'LLM non è autorità su «se un'informazione è vera»,
e qui gli si chiede se JARVIS è rimasto sé stesso. Le tre cose che rendono la
tensione accettabile:

1. **giudica un altro processo**, non sé stesso — chi risponde è T1 con la
   persona, chi giudica è T2 senza. Non è autocertificazione (ADR-012);
2. **la regola gli arriva citata dal file**, non riassunta da me;
3. **dove esiste un giudizio meccanico si registrano entrambi**, e il disaccordo
   è un dato salvato — è il più vicino a una «fonte indipendente» che questa
   misura possa avere.

E `tests/eval_persona.py` verifica che le regole citate **esistano ancora alla
lettera** in `config/voice-persona.md`: una misura contro una regola cambiata
non è una misura vecchia, è la misura di un'altra cosa. Provato cambiando
«Signore» in «Capo» nel file: il banco diventa rosso e nomina la citazione morta.

---

## ④ Che cosa NON è verificato — per nome

1. **La misura della persona è RUMOROSA fra un giro e l'altro.** La sonda
   `dissenso` è stata bocciata dal modello al primo giro e promossa al secondo,
   con la stessa rubrica: T1 aveva risposto diversamente. **Una sola lettura non
   è una misura di deriva**, ed è un limite del numero, non del banco.
2. **Il ri-ancoraggio NON è stato fatto**, ed è una scelta. Il piano lo metteva
   in questa fetta; ContextEcho misura la deriva su sessioni da 3.746 a 9.716
   turni, e qui il diario ha 61 righe in tre giorni. Cablare adesso una cura per
   una malattia mai osservata vorrebbe dire non sapere mai se servisse. Prima il
   termometro, poi la cura — è la stessa regola con cui il piano dice «prima
   `eval_memoria` dice **quando** il recupero smette di funzionare, poi si
   decide» sul vector store.
3. **Le sonde sono dodici, la persona ha più regole di dodici.** Non sono
   coperte: «anticipi», l'ironia, la lunghezza scelta dalla domanda, il
   comportamento all'interruzione.
4. **Il corpus della memoria è sintetico.** I due topic veri di questa macchina
   non si committano, e le venti domande le ho scritte io.
5. **Il costo non è stato misurato.** Ventiquattro chiamate a giro — dodici T1
   sonnet, dodici giudizi haiku — e il conto in USD nozionali non è stato
   registrato, a differenza di `banco_haiku`.
6. **Nessuna soglia**, quindi il banco oggi **non può diventare rosso** per un
   peggioramento. Diventa rosso solo se si rompe il banco o se la persona
   cambia sotto le citazioni. È il prezzo dichiarato della prima lettura.

---

## ⑤ Perché `eval_persona` non spende

`tests/eval_memoria.py` gira con tutto il resto: costa 300 ms e zero. La
persona no — dodici turni su un modello vero più altrettanti giudizi.

**Un test che spende non è un test**: la regola l'ha stabilita
`scripts/banco_haiku.py` — *«servono una rete, una quota e ~2,2 USD nozionali a
giro, e un test che spende non è un test»* — e questa fetta la segue. Chi spende
è `scripts/termometro.py --persona`, una volta; `tests/eval_persona.py` rilegge
il JSON a costo zero.

⚠️ Deviazione dichiarata dal piano, che nominava `tests/eval_persona.py` come
l'esecutore delle sonde.

```bash
uv run python scripts/termometro.py              # solo memoria: gratis
uv run python scripts/termometro.py --persona    # anche la persona: spende
```
