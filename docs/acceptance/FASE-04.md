# Fase 4 — esito dei criteri di accettazione

**Data**: 18 agosto 2026 · **Riferimento**: `docs/SPEC.md` §22 Fase 4
**Test**: 218 verdi (erano 184) · **Precedente**: `FASE-03.md`

---

## Il criterio di §22

### 1. «Operazione lunga in T2 mentre T1 risponde» — ✅ VERIFICATO

Uno spawn T2 reale — *elenca i file di `core/llm/` e descrivili* — mentre T1
rispondeva a tre turni:

| | |
|---|---|
| T2 | **17,31 s**, 22 eventi, `ok=True`, risposta corretta |
| T1 turno 1 | 4160 ms |
| T1 turno 2 | 1932 ms |
| T1 turno 3 | 2313 ms |
| **T1 mediana sotto carico** | **2313 ms** |
| T1 vivo alla fine | ✅ |

**Sotto carico T1 è andato meglio** dei 3,2–4,4 s misurati senza carico in
Fase 3 — la varianza è quella della rete, non del carico locale. Il Governor ha
tracciato: 1 spawn usato, 14 restanti.

### 2. «Su rate limit T2 si sospende, T1 sopravvive» — ⚠️ VERIFICATO PER SIMULAZIONE

Provocare un rate limit vero avrebbe richiesto di martellare l'abbonamento.
Iniettato l'evento `system`/`api_retry` con `error=rate_limit` che §5.4
descrive:

- T2 si sospende, e i nuovi spawn vengono rifiutati con motivo e tempo di attesa
- viene emesso `agent.advisory` di livello `warn`
- **l'advisory dichiara `t1_operativo: true`** — chi lo legge deve sapere che la
  conversazione continua, non dedurlo

**Non verificato**: il comportamento contro il servizio vero quando il limite
scatta davvero.

---

## Tre difetti trovati usando il codice, non leggendolo

### ① Il barge-in avrebbe bloccato T1 per sempre

`ClaudeT1.ask()` prendeva un `asyncio.Lock` **dentro un generatore asincrono**.
Il lock resta preso finché il generatore non viene chiuso — e il barge-in
**abbandona lo stream a metà**. Dopo la prima interruzione, ogni turno
successivo sarebbe rimasto in attesa di un lock che nessuno avrebbe rilasciato.

Sostituito con un flag rilasciato in `finally`: l'abbandono lo libera subito, e
una chiamata davvero concorrente fallisce rumorosamente invece di incastrarsi.

### ② E anche risolto il lock, il turno dopo il barge-in tornava vuoto

Seconda metà dello stesso guasto, più insidiosa. Il modello **continua a
generare** dopo l'abbandono, e i suoi eventi restano su `stdout`: il turno
successivo li leggeva come propri e trovava subito un `result` che non gli
apparteneva.

Misurato: dopo un barge-in, il turno seguente restituiva la stringa vuota. Ora
si **drena in sottofondo** fino alla fine del turno abbandonato prima di
liberare. Verificato: dopo il barge-in, *«Tre, Signore.»*

### ③ La persona di T1 con percorso relativo falliva in silenzio

`ClaudeT1` passava il percorso di `voice-persona.md` così come lo riceveva, ma
il sottoprocesso gira da `voice-cwd`: un percorso relativo non esiste lì dentro,
Claude Code usciva subito e `ask()` restituiva il vuoto **senza spiegare
perché**. Ora `persona` e `cwd` si risolvono in assoluto alla costruzione.

Tutti e tre sarebbero stati invisibili a una lettura del codice.

---

## Scostamenti dalla specifica, dichiarati

| # | Cosa | Decisione |
|---|---|---|
| **R31** | Il `classify()` di §21.5 riscrive con parole chiave ciò che il parser T0 già fa | Il router **chiede a `parse()`**. Due classificatori divergerebbero al primo comando aggiunto, e quello di §21.5 non ha corpus. Un test verifica che le parole chiave non rientrino dalla finestra |
| **R32** | ADR-004 diceva che `conso/` misura l'LLM (già pagato) e non Deepgram (il costo vero) | **Il quadro è cambiato**: nessuna chiave Deepgram, `edge-tts` gratuito, **nessun costo ricorrente**. `conso/` misura ciò che vincola: gli **spawn nella finestra**. `total_cost_usd` si registra perché lo stream lo riporta, ma non è su quello che si decide |
| **R33** | Il consolidamento notturno saltato non diceva nulla | Emette `agent.advisory`. Era la correzione minore #5 della valutazione architetturale |
| **R34** | §5.5 mostra un `build_context()` | **Non implementato per T1**: sarebbe il secondo gestore di contesto di cui §5.5 stessa avverte (invariante 17). Un test verifica che il metodo non esista |
| **R36** | LangGraph, deciso da Lei | Entrato. Costo misurato: **62 pacchetti** contro i 39 di prima, e ha **retrocesso `websockets` da 17.0.1 a 15.0.1** — innocuo, `unix_serve` esiste ancora e i test passano. `LANGSMITH_TRACING=false` esplicito: `langsmith` non deve poter chiamare casa da un sistema il cui §18.3 è attento a cosa lascia la macchina |
| **R37** | `core/tools/memory.py` e `core/memory/{store,pruner}.py` non sono in §21.1 | Aggiunti e dichiarati |

### ⚠️ La tensione fra §5.5 e l'invariante 3

§5.5 vuole che il consolidamento notturno scriva **tramite l'allowlist**, ma
l'invariante 3 vuole conferma umana per ogni `side_effect=True` — e **alle 04:00
non c'è nessuno che confermi**.

Sciolta restringendo il raggio, non aggirando la regola:

- scrive **solo** dentro `topics/`
- **non tocca mai i fatti fissati**, che sono dell'utente (§5.5)
- ogni scrittura notturna finisce in `initiatives/`, **visibile al risveglio**

È un compromesso dichiarato, non una scappatoia. Se un giorno il consolidamento
dovesse toccare altro, la conferma andrà ripensata, non allargata.

---

## Le garanzie strutturali di questa fase

| Garanzia | Dove è imposta |
|---|---|
| ogni spawn T2 passa dal Governor (inv. 16) | `ClaudeT2.stream` apre con `governor.spawn()` |
| **fail-closed**: senza Governor, niente T2 | il costruttore lo esige |
| due richieste simultanee non sfondano la finestra | il conteggio si incrementa **prima** dell'attesa sul semaforo |
| T1 non passa mai dal Governor | il Governor non ha alcun percorso per T1 |
| il router non ha un secondo classificatore | test su `tokenize`, che guarda il codice e non la prosa |

---

## ❌ NON VERIFICATO

1. **Il rate limit vero.** Simulato, per non consumare la Sua quota.
2. **Il consolidamento notturno contro un T2 reale.** Verificato con un T2
   finto: la logica, l'advisory su quota e l'intoccabilità dei fatti fissati.
   Non è mai girato alle 04:00 con Claude Code vero.
3. **Lo scheduler delle 04:00.** §5.5 dice «gira via scheduler»; lo scheduler
   è Fase 9 (systemd). Oggi `Consolidatore.esegui()` va invocato.
4. **`--resume` di T2.** Il session id si legge e si conserva, ma riprendere
   una sessione non è stato provato.

## Riepilogo

| | |
|---|---|
| Test | **218 verdi** (erano 184) |
| Criteri §22 Fase 4 | **1 su 2 pieno** · 1 verificato per simulazione |
| Difetti trovati usando il codice | **3**, tutti in `ClaudeT1`, tutti invisibili a una lettura |
| Costo di LangGraph, misurato | 39 → **62 pacchetti**, e una retrocessione di `websockets` |
