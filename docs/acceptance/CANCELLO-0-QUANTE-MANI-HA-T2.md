# Cancello 0 — quante mani ha già JARVIS

**Data**: 27 agosto 2026 · **Riferimento**: `docs/SPEC.md` §5.5, §5.3
**Rollback**: `2745cb2` · **Test**: 1470 → **1477**

---

## Perché è il primo passo

Il piano è dare più controllo a JARVIS. Prima di allargare un perimetro bisogna
sapere quanto è largo adesso, e sul perimetro di T2 il repository dice una cosa
che nessuno aveva verificato.

`core/llm/claude_t2.py:43` commenta `TOOL_CONSENTITI` con:

> *«Ristretti ma reali. **Nessun tool di scrittura distruttiva**: cancellare
> passa dall'allowlist del core, che chiede conferma.»*

Vero per *distruttivo*. Ma la stringa è `Read,Edit,Bash(git *),Glob,Grep`, e
`Edit` **scrive**.

---

## La misura

Copia scratch con lo **stesso** `.claude/settings.json` del progetto e la
**stessa** riga di comando che `ClaudeT2.argv()` costruisce — `--model sonnet`,
`--allowedTools "Read,Edit,Bash(git *),Glob,Grep"`, `--permission-mode dontAsk`.

| tool tentato | esito |
|---|---|
| `Write` | **negato** — *«Permission to use Write has been denied because Claude Code is running in don't ask mode»* |
| `Bash` generico (`printf`, `ls`, `cat`) | **negato** |
| `Read` | riuscito |
| **`Edit`** | **riuscito** — `base.txt` modificato |
| **`Bash(git add -A && git commit)`** | **riuscito** — commit creato |

**Due conclusioni, e vanno tenute separate.**

✅ **`--allowedTools` regge.** Il `permissions.allow` di `settings.json` — che
contiene `Write`, `Bash(npm install *)`, `Bash(mkdir *)` — **non lo allarga**.
Il sospetto che le due sorgenti si componessero in modo permissivo era
infondato, e su questo il commento aveva ragione.

⚠️ **Ma `Edit` e `Bash(git *)` sono dentro l'allowlist, e girano senza che
nessuno confermi.** Uno spawn T2 può modificare un file e committarlo.

---

## Dove morde: il consolidamento notturno

`_t2_meta` — l'istanza con quei tool — è quella che il **consolidamento delle
04:00** riceveva. Cioè: un modello con `Edit` e `git commit`, sul repository
vero, di notte, con nessuno davanti.

A tenerlo dentro `topics/` era **il testo del prompt**. Un confine imposto da
una frase invece che da un meccanismo — la forma di difetto che questo progetto
rifiuta ovunque.

**E §5.5 lo diceva già**, `docs/SPEC.md:403`:

> *«Usa un processo T2 dedicato con `--allowedTools ""`: legge e scrive solo
> tramite i tool memoria dell'allowlist, **mai direttamente**.»*

L'implementazione passava `_t2_meta`. Non è una scelta di compromesso: è uno
scostamento dalla specifica, nella direzione pericolosa, mai dichiarato.

## La correzione

Un T2 **suo**, `tool=""`, `max_turns=1`.

E non gli serve nient'altro: `Consolidatore.esegui()` passa gli scambi **dentro
il compito** e scrive con `MemoryStore.scrivi_topic`. Il modello non ha mai
avuto bisogno di leggere né scrivere un file.

`max_turns=1` non è un numero scelto: **con zero tool non c'è niente su cui
iterare**, e un secondo turno non potrebbe fare nulla di diverso dal primo.

⚠️ **`_t2_meta` conserva le sue mani**, e deve: `brief_me` e `needs_attention`
guardano `git log` e `docs/acceptance/`, e senza `Read` non potrebbero. Il
difetto era il consolidamento, non T2.

---

## Verifica

### ✅ Le due bocciature

| perturbazione | esito |
|---|---|
| il consolidamento torna a `_t2_meta` | 1 rosso |
| il T2 dedicato riprende i tool di default | 2 rossi |

I due test sono la stessa proprietà da due lati: chi svuotasse `TOOL_CONSENTITI`
invece di passare `tool=""` farebbe passare il secondo e cadere il primo.

### ✅ La suite

`1470 → 1477`, verde.

Un test esistente è stato aggiornato: `test_anche_i_DUE_T2` contava tre istanze
che passano `su_evento` al supervisore, e adesso sono quattro. Il numero non è
decorativo — un T2 costruito senza `su_evento` renderebbe il supervisore cieco
sui suoi guasti, e §5.6 tornerebbe ad avere due proprietari.

### ❌ NON verificato

- **Che il consolidamento notturno funzioni ancora** con zero tool. Il modello
  non ne aveva bisogno — è dimostrato leggendo `esegui()` — ma nessuna notte è
  mai stata attraversata, quindi **non è mai stato eseguito con un modello
  vero**, né prima né dopo. È il turno 1.
- **`cwd = RADICE` anche per il consolidamento.** Con zero tool non è un
  problema di sicurezza, ma carica `CLAUDE.md` nel contesto di un compito che
  riassume conversazioni. T1 ha una directory dedicata e vuota per esattamente
  questa ragione. Osservato, non corretto: fuori dal cancello.
