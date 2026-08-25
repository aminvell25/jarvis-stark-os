# Stato dei piani — 24 agosto 2026

> **Perché questo documento esiste.** Il progetto ha otto documenti di piano
> scritti fra il 18 e il 22 agosto. Quattro sono chiusi, due sono in gran parte
> fatti, e **quattro voci sono state superate dal modello nuovo** — due delle
> quali sono la stima più grossa dell'intero progetto.
>
> Chi riapre uno di quei documenti senza questo davanti pianifica su numeri
> morti. **Da qui in poi i piani vecchi sono cronologia; l'esito sta qui.**
>
> Verificato contro il repo al commit `d094369`, non dedotto dai documenti.

---

## 1. Il quadro

| documento | esito |
|---|---|
| `PIANO-CORE-E-DENSITA.md` | ✅ **chiuso** — otto turni su otto |
| `PERIMETRO-E-DECISIONI.md` — ADR-005, ADR-006 | ✅ chiusi, ogni azione spuntata |
| `VALUTAZIONE-ARCHITETTURALE.md` — ADR-001, 002, 008, 009 | ✅ chiusi |
| `ANALISI-REPO-E-TECNOLOGIE.md` | ✅ 8 adozioni su 10 |
| `SPEC-26-AMBIENTE-UNICO.md` | ⚠️ 8 passi su 10 |
| `DIVARIO-PREMIUM.md` | ⚠️ 8 su 10 — due chiuse **come impossibili** |
| `SPEC-25-STRATO-DI-PRESENZA.md` | ⚠️ costruita, per una strada diversa da quella scritta |
| ADR-003 · ADR-004 · ADR-007 | ❌ **aperti** |

---

## 2. Che cosa manca davvero — cinque voci

Ordinate per gravità, non per costo.

### ① ADR-003 è fatto a metà — ed è il difetto peggiore che resta

`core/llm/supervisor.py` esiste e riconosce **solo `auth`**: `AUTH_ERRORS`,
`auth_expired`. Le classi `transient` e `repeated` che ADR-003 prescrive **non
ci sono**.

Quindi il modo di fallire che quel documento definisce *«il peggiore che questo
sistema possa avere»* è aperto tale e quale: T1 muore per OOM, crash o stream
desincronizzato, `Restart=always` lo rilancia, la sessione riparte **vuota**, e
**JARVIS continua a rispondere con la stessa voce avendo perso la conversazione,
senza dirlo.** Contraddice §16, «nessuna soglia agisce senza annunciarlo».

Non è teorico: è il percorso che si prende ogni volta che T1 non muore per
scadenza OAuth.

### ② ADR-007 — MCP: zero righe

Nessun `core/mcp/`, nessun `registry.promuovi_mcp()`, nessuno dei due eval
richiesti. È l'ADR che il suo stesso documento chiama *«il singolo
moltiplicatore di capacità più grande disponibile dentro il perimetro scelto»*.

### ③ ADR-004 — il solo costo reale non è misurato

`core/llm/governor.py` scrive `conso/`, ma **nessun conteggio di secondi
Deepgram per provider**. Il sistema conta con precisione i token
dell'abbonamento — che sono già pagati — e non conta l'unica cosa che gli costa.

### ④ §26.7 — la pagina impostazioni non esiste

`ui/src/panels/settings.js` è **0 byte**, esattamente come alla Fase 0. E
`tomlkit`, in dipendenze dalla Fase 0 «per lettura E scrittura», è ancora usato
solo per `parse`.

Conseguenza: il criterio 7 di §26.9 — *«cambiare la dimensione delle icone
riscrive `settings.toml` conservando i commenti»* — **non è verificabile per
costruzione**, non «non verificato».

### ⑤ La voce non è mai stata accesa col microfono vero

Il codice è composto nell'engine dalla Fase 9. `voice.enabled = false`.
`PERIMETRO` lo conta mezza giornata ed è l'unica voce della sua roadmap che
non dipende da nient'altro.

---

## 3. Che cosa il modello nuovo ha superato — quattro voci

**Non sono lavoro rimandato. Sono lavoro che non va più fatto**, e due di esse
sono la stima più grossa del progetto.

### ① I quattro workspace → una scrivania sola (ADR-010, 19 ago)

Travolge due cose scritte prima:

- **`DIVARIO-PREMIUM` §0** misura `ws-01…ws-04`. Quegli scatti non si
  rigenerano più. La **colonna del riferimento resta il bersaglio**; le nostre
  no. Lo stato corrente sta in `PIANO-CORE-E-DENSITA` §9.
- **`ANALISI-REPO` voce 8**, «workspace con colore e dominio»: il campo `ws` è
  diventato `categoria` e **non governa più la visibilità**. L'idea presa da
  `krrish612` sopravvive come modo di ordinare il catalogo, non come pagina.

### ② «Il giro §11.7 sui 18 componenti» → i componenti a schermo sono SEI

Misurato in `d3d8978`. È la voce **numero 3 di `DIVARIO`** (4–5 giorni,
dichiarata *«l'80 % del divario visivo»*) e il **passo 7 di `SPEC-26`**.

**La stima più cara di tutti e due i piani, costruita su un numero sbagliato di
tre volte.** La mossa più redditizia fra i sei è stata misurata — l'emisfero
illuminato del globo da `--fill-1` a `--fill-2` — e vale **+0,07 di entropia su
+0,21 necessari**. Un terzo, da un componente solo. Quello è il lavoro vero;
«diciotto componenti» non lo è mai stato.

### ③ Il modulo Media (`DIVARIO` §6) non è rimandato: è **impossibile**

Le tre radici consentite contengono **zero file immagine**, contati. E le
miniature dei nostri stessi scatti peggiorano dev.std e `L>60` — sono la nostra
palette, copiarla non articola niente.

Costruirlo significherebbe inventare contenuto, cioè **invariante 23**.
Va riaperto solo se e quando su quel disco ci sono immagini vere.

### ④ `SPEC-25` è stata realizzata per una strada diversa da quella che descrive

| §25 dice | la realtà |
|---|---|
| §25.2: tre strati `--z-presenza` / `--z-pannelli` / `--z-modale` | esiste `--z-insegna: 1` dentro `#scrivania`. Modello diverso |
| §25.12 passo 4: `desk/presenza.js` | **mai esistito**. Lo strato di presenza è `desk/sfondo.js` |
| §25.9 criterio 0: «≥ 75 % dell'inchiostro del nucleo» | sostituito dalla misura di **occlusione** del turno 1 |
| §25.10 `test_luminanza_nucleo`: «mai `--cy-500`» | **oggi direbbe il falso**: §25.5 lo ammette sull'anello attivo, uno per volta |

L'esito è quello che §25 chiedeva — un nucleo solo, che persiste, che si muove
solo con una causa. La strada no.

### ⑤ Fuori elenco: la colonna laterale è stata **rifiutata**, non rimandata

`DIVARIO` §8 la elenca ancora come lavoro da fare. `2e6d640` l'ha misurata e
scartata: *«NON ENTRA — è una somma»*.

---

## 4. Che cosa resta aperto sulla densità

Un criterio solo, e la strada per chiuderlo è nota.

| criterio | valore | soglia | |
|---|---|---|---|
| deviazione standard | 34,0 | 32 | ✅ |
| `L>60` riempito | 25,3 % | 25 % | ✅ margine sottile |
| caldo | 3,8 % | 3–6 % | ✅ |
| barra | 63,7 % | 25 % | ✅ |
| marchio §25.13.5, nove stati | 3,04:1 | 3,0–5,0 | ✅ |
| **entropia** | **2,21** | **2,40** | ❌ |

⚠️ **La soglia 2,40 non è il riferimento.** `SOGLIE` in `densita.mjs` dichiara
la propria provenienza: *«a metà strada fra la nostra rev 5.7 e il più povero
dei due riferimenti»*. `famiglia-a/01` misura **H 3,32 · dev 55,7**. Passare
2,40 significa passare la barra che il progetto si è dato, restando **0,92 bit**
sotto il bersaglio su cui `DIVARIO` è costruito. Le due frasi vanno dette
insieme.

### Il buco nel protocollo di misura, e va chiuso per primo

Il protocollo §5 di `PIANO-CORE-E-DENSITA` fissa finestra, pannelli, scena e
istante. **Non fissa i dati vivi.** L'area sotto la curva della CPU nel pannello
telemetria *è* superficie misurata: quando la CPU passa dal 3,6 % all'1,7 %, o
la barra da `NOMINAL` a `DEGRADED`, la densità si muove da sola.

Quattro misure contaminate in due giorni per questa causa. L'A/B a tre scatti
per lato con `git stash` in mezzo protegge **dentro** una sessione, non **fra**
sessioni.

**Finché non c'è una fixture che congeli i valori vivi durante `--scrivania`,
nessun delta sotto ±1 punto di `L>60` o ±0,05 di entropia è distinguibile dal
rumore**, e ogni confronto fra sessioni è nullo per regola.

---

## 5. Ordine di lavoro che ne esce

| # | Cosa | Perché qui |
|---|---|---|
| 1 | **Fixture dei dati vivi** nel protocollo §5 | senza, i turni dopo misurano rumore |
| 2 | **ADR-003 completo** — classi `transient` e `repeated`, replay dei soli fatti fissati, annuncio via TTS locale | è il difetto peggiore aperto, e non dipende da nient'altro |
| 3 | Accendere la voce col microfono vero | mezza giornata, il codice c'è dalla Fase 9 |
| 4 | L'emisfero del globo `--fill-1` → `--fill-2` | +0,07 su +0,21, misurato |
| 5 | **ADR-004** — secondi Deepgram in `conso/` | il solo costo reale |
| 6 | **§26.7** pagina impostazioni + scrittura `tomlkit` | sblocca il criterio 7 di §26.9 |
| 7 | **ADR-007** MCP | il moltiplicatore, dopo che la casa è in ordine |

Fuori elenco perché **non si fanno**: il giro sui 18 componenti (sono sei), il
modulo Media (zero immagini), la colonna laterale (rifiutata), i quattro
workspace (aboliti).
