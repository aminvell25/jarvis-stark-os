# Piano — da scrivania a JARVIS

**Scritto il 25 agosto 2026**, verificato contro il repo al commit `c017a5b`,
non dedotto dai documenti.

> **Perché esiste.** `docs/STATO-DEI-PIANI.md` chiude il conto dei piani vecchi
> e lascia **cinque voci**. Questo le ordina, dice quale blocca quale, e dichiara
> due cose che la richiesta chiedeva e che **non si possono fare**.

---

## 0. Due vincoli, dichiarati prima di cominciare

### ① Nessuna libreria di animazione nuova

La richiesta diceva «usa pure librerie di alto grado per animazione e scene
cinematografiche… anime.js ma puoi usare pure altre librerie che ritieni più
di livello». **Non lo farò senza una Sua conferma esplicita**, e la ragione non
è prudenza:

- **Invariante 9**: «Un solo motore di animazione: anime.js v4. Niente GSAP.»
- **Invariante 10**: «Un solo motore 3D: three.js. Niente Babylon.»
- `CLAUDE.md`, *Non fare senza chiedere*: «Aggiungere dipendenze non elencate.»
- `docs/ANALISI-REPO-E-TECNOLOGIE.md` elenca GSAP, Lottie, Qt/QML, Unreal,
  React e Vue fra le tecnologie **valutate e scartate**, con la ragione accanto,
  e dice: «Non riproporle.»

Il cinematografico si fa **dentro** questi due motori. anime.js v4 ha timeline,
stagger, spring, motion path e draggable; three.js ha tutto ciò che §11 chiede.
Quello che manca oggi non è un motore: è **una ragione per animare** — §10.6
ammette tre classi di moto e vieta l'ambientale, e la scrivania a riposo non ha
stati che accadano.

Se vuole comunque una libreria in più, me lo dica e la valuto: la strada è un
ADR che emendi gli invarianti 9 o 10, non un `npm install`.

### ② «Implementa tutte le fasi» non è un turno

Le fasi 3–9 della SPEC valgono **circa quattordici settimane** di stima
dichiarata. Quello che si può fare bene è **una voce per volta, chiusa e
misurata**, che è il ritmo che ha portato entropia, dock, ritaglio e orologi da
aperti a chiusi. Questo piano è quell'ordine.

---

## 1. Che cosa manca davvero

Da `STATO-DEI-PIANI.md`, verificato: cinque voci.

| | voce | perché conta | blocca |
|---|---|---|---|
| ① | **ADR-003 completo** — classi `transient` e `repeated` | «il modo di fallire peggiore che questo sistema possa avere»: JARVIS risponde con la stessa voce avendo perso la conversazione, **senza dirlo** | Fase 3, Fase 4 |
| ② | **§26.7 — pagina impostazioni** | oggi si configura solo scrivendo TOML a mano | nulla |
| ③ | **ADR-004 — `conso/` misura anche Deepgram** | l'unico costo reale non è misurato | nulla |
| ④ | **ADR-007 — MCP** | zero righe | Fase 6 |
| ⑤ | **La voce col microfono vero** | mai accesa | Fase 3 |

## 2. L'ordine, e perché è questo

**① per primo**, e non è una scelta di gusto: è l'unica voce che rende JARVIS
**onesto sul proprio stato**, ed è ciò che distingue un assistente cognitivo da
un pappagallo con una bella interfaccia. Un JARVIS che ha perso la memoria e lo
dice è più avanzato di uno che non se ne accorge. Non dipende da niente.

**⑤ per secondo**: è l'unica voce che non si può *dedurre*. Tre settimane di
Fase 3 sono scritte contro un microfono che non è mai stato acceso, e il primo
minuto col microfono vero riscrive metà di quelle stime. Va fatto **presto e
piccolo**: accendere, misurare la latenza di T0, dichiarare.

**② per terzo**: superficie nuova, nessuna dipendenza, e toglie l'unico punto
in cui l'utente deve modificare un file a mano.

**③ e ④** dopo: ③ è misura, ④ è una superficie nuova che `PERIMETRO-E-DECISIONI`
dice esplicitamente di fare **dopo** ADR-003.

## 3. Il criterio, per ciascuna

Una voce è chiusa solo quando i quattro punti della *definizione di fatto*
sono verdi — test, criterio §22 verificato e scritto in `docs/acceptance/`,
ciclo §11.7 per ogni componente visivo, commit.

| | criterio di accettazione |
|---|---|
| ① | uccidere T1 → riavvio, **replay dei soli fatti fissati**, annuncio via TTS locale; ripeterlo N volte nella finestra → `degraded_llm` e stop, e systemd non rilancia |
| ⑤ | *«papà è a casa»* eseguito **offline** con la latenza mediana misurata su cento frasi, non stimata |
| ② | ogni impostazione di `settings.toml` modificabile dalla pagina, e il file resta la verità |
| ③ | `conso/` mostra il costo Deepgram accanto a quello Claude, dalla stessa fonte |
| ④ | un server MCP registrato passa dall'allowlist e non aggiunge una seconda strada al filesystem |

## 4. Che cosa NON entra in questo piano

- **Il modulo Media** (`DIVARIO-PREMIUM` §6): chiuso **come impossibile**, non
  rimandato.
- **La colonna laterale**: rifiutata, non rimandata.
- **I quattro workspace**: superati da ADR-010, una scrivania sola.
- **Scene cinematografiche ambientali**: §10.6 vieta l'animazione senza causa, e
  la deroga esiste solo dentro un pannello con una sorgente viva che si può
  spegnere. Il cinema qui è **la densità**, non il moto — ed è la ragione per
  cui entropia, dock e tabelle sono stati il lavoro degli ultimi due giorni.
