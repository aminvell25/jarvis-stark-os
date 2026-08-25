# Gli argomenti — il banco, la regola misurata, e haiku collegato perché la misura lo chiedeva

**Data**: 26 agosto 2026 · **Riferimento**: `docs/SPEC.md` §15 · **Rollback**: `e09b956`
**Test**: 1172 verdi (erano 1103) · **Misura**: `docs/acceptance/ARGOMENTI-CORPUS.json`

---

## 0. La mia diagnosi era falsa, e il modo in cui l'avevo fatta lo era di più

Ieri ho scritto che l'estrattore locale sbaglia «una frase su tre» perché tiene
un verbo e perde i sostantivi. Lei l'ha verificata eseguendo, ed è falsa.

Il meccanismo vero:

```python
notevoli = {p: n for p, n in conteggi.items()
            if n >= MIN_OCCORRENZE or len(p) >= MIN_LUNGHEZZA_SINGOLA} or conteggi
```

Su **una frase sola** ogni conteggio vale 1, quindi `n >= 2` è falso per tutti e
l'`or` collassa a «è lunga». `clima` (5) e `governo` (7) cadevano per la
lunghezza, non per la categoria grammaticale; `pensando` (8) passava per la
stessa ragione. Non due su tre: **tre su tre decisi dalla lunghezza**, e due
volte la lunghezza ha indovinato. E il ripiego `or conteggi` non scattava
perché qualcosa qualificava — quella sbagliata.

Il difetto peggiore però non era il meccanismo: era il **metodo**. Tre frasi
contate a mano, i successi contati, i falsi positivi invisibili. Da qui il
banco.

---

## 1. Il banco — `tests/eval_argomenti.py`

### Da dove vengono le frasi

**Non le ho scritte per questo banco.** Sono le 43 frasi conversazionali di
`tests/t0_corpus.py`, **importate e non copiate**, scritte per una proprietà
ortogonale — che il parser T0 le lasci andare a T1 — e quindi impossibili da
avere scelto perché questa regola le passasse. È la garanzia più forte contro
il sovradattamento che potessi darmi da solo.

⚠️ **Resta una metà debole, e la dichiaro**: le **etichette** sono mie. Chi ha
riparato la regola ha scritto la verità di riferimento. Le due regole che ho
seguito — un argomento è «una cosa di cui si potrebbero leggere notizie», e
solo parole che compaiono nella frase — le rendono controllabili, non neutre.
**Se vuole dettarLe Lei, il banco è pronto a riceverle**: il corpus è
importato, quindi basta aggiungere frasi e attese e la misura si rifà da sola.

### Il prezzo di quella provenienza

**28 frasi su 43 non hanno nessun argomento**, perché venti di loro sono modi di
dire scelti per somigliare a comandi. È una fetta **avversaria** della lingua,
non un campione: la precisione misurata qui è un **limite inferiore**, non la
precisione che si vedrebbe parlando del mondo.

### La metrica

Precisione e richiamo **micro-mediati**. Una frase ad attesa vuota contribuisce
solo alla precisione, ed è lì che un falso positivo diventa visibile invece di
nascondersi dietro i successi.

Verità di riferimento a **token singoli**, non a locuzioni: «divulgazione
scientifica» sono due argomenti, perché il gate confronta parole con parole.

E `Misura.precisione` vale **0,0** quando non c'è nessuna proposta, non 1,0:
non avere occasioni di sbagliare non è precisione. Ha un test suo.

---

## 2. Le ipotesi, e quale ha vinto misurando

Il «prima» non è citato: la **regola vecchia gira davvero**, sullo stesso
corpus, dentro lo stesso giro di test (`regola_vecchia` in
`tests/eval_argomenti.py`). Così il confronto non può invecchiare.

| ipotesi | precisione | richiamo |
|---|---|---|
| **regola di prima** — `n>=2 or len>=8` | **0,171** | 0,700 |
| H3 — solo frequenza, ripiego `or conteggi` scoperto | 0,173 | 0,950 |
| H1 — salta il filtro sotto N token candidati (N = 2…8) | 0,157–0,173 | 0,700–0,950 |
| H8 — solo l'apostrofo che separa | 0,177 | 0,700 |
| H7 — posizione, e se vuoto tieni tutto | 0,266 | 0,850 |
| **H6 — posizione + apostrofo (adottata)** | **0,410** | **0,800** |

**H1 non ha un pianoro: non ha nemmeno un picco.** Nessun valore della soglia
sposta la precisione fuori dalla banda 0,157–0,173. La risposta alla domanda
«da dove si deriva la soglia» è che **quella soglia non esiste**, e l'ho
misurata invece di sceglierla male.

### La regola adottata: la posizione, non la lunghezza

Si tiene una parola se è **introdotta da un articolo o da una preposizione** —
«il bagno», «di musica», «un motore». `INTRODUCONO` è una **allowlist** di
parole-funzione, esattamente come `FERME` è una lista di parole vuote:
nessuna denylist di desinenze verbali, che sarebbe un elenco di sconfitte già
subite (invariante 2).

E un secondo difetto trovato dal banco, non previsto: **l'apostrofo stava dentro
la classe di caratteri**. `un'email` era *una* parola di otto lettere — lunga
abbastanza da passare la vecchia soglia — e l'argomento vero, `email`, non
esisteva. Allo stesso modo `perche'` sfuggiva a `FERME`, che contiene `perche`
e `perché` ma non la forma con l'apostrofo.

### Il ripiego «tienili tutti» è stato tolto, e costava

`or conteggi` sembra prudenza — meglio qualcosa che niente — ed è invece il caso
in cui la regola sa di non sapere e risponde comunque: **−0,155 di precisione**
(0,266 contro 0,410, misurato). La lista vuota è innocua perché
`MotoreNews.un_giro()` senza argomenti non guarda affatto.

### Che cosa la regola nuova ha smesso di fare

**Un sostantivo nudo non produce niente**: `estrai_locale("clima") == []`.
Senza articolo davanti non c'è la posizione su cui decide. Non è teorico — era
l'input di tre test del motore, che scrivevano `ascolta("clima")` come
scorciatoia e sono stati riscritti con frasi vere. Nel parlato un sostantivo
nudo è raro, ma **parlando per elenchi** — «clima, governo, inflazione» — non si
aggancia niente. Ha due test suoi, perché un limite scritto è meglio di un
limite scoperto fra sei mesi.

---

## 3. La barra per haiku era dichiarata prima, e la misura non l'ha raggiunta

**Dichiarata prima di misurare**, e dedotta invece che scelta: un argomento
falso fa interrompere JARVIS sulla cosa sbagliata, e con 3 interruzioni all'ora
una precisione `P` ne lascia `3(1−P)` fuori tema. Perché ne resti meno di una:

    3 (1 − P) < 1   →   P > 2/3 ≈ 0,667

Il richiamo lo riporto e **non lo uso come cancello** — §15 mette un tetto alle
interruzioni, non un minimo — ma un test verifica che il richiamo **non sia
sceso**, perché il modo più facile di alzare la precisione è smettere di
rispondere.

**Misura: 0,410 contro una barra di 0,667. Haiku è collegato.**

E non per un pelo, né per un difetto limabile. Gli errori residui sono tutti
sintagmi regolari — «la luce», «la fantasia», «le orecchie», «un occhio» —
articolo più sostantivo, identici nella forma a «il bagno». **La differenza è
semantica**, e nessuna regola di forma la vede. È il confine della classe di
soluzioni, e ha un test che lo fissa.

⚠️ Un test guarda anche la **decisione**, non solo il numero: se un giorno la
regola locale supererà 0,667 da sola, `test_il_locale_NON_arriva_alla_barra`
diventerà rosso, e la risposta giusta sarà **togliere lo spawn**, non alzare la
soglia.

---

## 4. Il batch, dedotto invece che copiato

§15 dice «batch 60s», ma quel numero è anteriore al Governor: 60 s vorrebbero
dire fino a **60 spawn all'ora** contro un tetto di **15** (`MAX_PER_WINDOW`),
quindi tre estrazioni su quattro rifiutate e cadute sul ripiego. Non sarebbe
haiku con un ripiego: sarebbe il locale con qualche haiku.

Il batch **non ha ragione di essere più corto del periodo dei giri** — gli
argomenti si aggiornerebbero più spesso di quanto qualcuno li legga — **né più
lungo** — un giro girerebbe su una conversazione già finita. Quindi

    batch = periodo dei giri = 600 s con 3/ora → 6 estrazioni/ora dentro un tetto di 15

**Nessun numero nuovo**: lo stesso, passato una volta sola, e in una riga sola
(`EstrattoreLLM(chiedi, batch_s=self._periodo)`). Segue l'impostazione: con
12/ora diventa 150 s, e c'è un test.

⚠️ **Un caso limite dichiarato**: con `max_interruptions_per_hour = 60` il
pavimento dell'educazione riporta il periodo a 60 s, cioè proprio i 60 spawn
all'ora che nella quota non stanno. Lì l'unico esito possibile è il ripiego
annunciato. Non lo correggo — è un'impostazione fuori scala — ma va saputo, e
un test lo fissa al caso normale.

---

## 5. La risposta del modello è filtrata con la stessa arma dell'invariante 2

**Solo parole che Lei ha davvero detto.** Non è pignoleria di formato: senza
quel vincolo il modello può proporre un argomento che nel testo non c'è — per
associazione, o perché ha risposto in prosa — e quell'argomento andrebbe poi a
scegliere quali notizie La raggiungono. Il vocabolario ammesso è ciò che è stato
pronunciato: **una allowlist che si costruisce da sola**.

Ed è anche ciò che rende innocua una risposta mal formata: «Mi dispiace, non
riesco a individuare argomenti precisi» non contiene nessuna parola del testo,
quindi non produce nessun argomento. Ha un test.

Lo spawn ha `tool=""`: non c'è niente da azionare in un compito che trasforma
testo in parole, e zero tool è anche la condizione dell'invariante 5.

---

## 6. Verifica — che cosa è stato misurato e che cosa no

### ✅ Il banco boccia se si ritira la correzione

Rimessa la clausola `or len(p) >= 8` e l'apostrofo dentro il token: **9 test su
63 diventano rossi**, fra cui `test_la_precisione_e_MIGLIORE_di_prima`.

⚠️ Alla prima prova ne diventavano rossi **8**, e il nono —
`test_perche_con_l_apostrofo_sfuggiva_a_FERME` — restava verde: asseriva
`"perche" not in ...`, e con la vecchia regola il token era `perche'`, con
l'apostrofo, quindi la parola senza non c'era comunque. **Un criterio vero per
assenza del fenomeno** (§11.7 regola 4), trovato solo perché la prova di
bocciatura è stata eseguita invece che data per scontata. Riscritto sull'insieme
intero.

### ✅ Un'estrazione vera con haiku, sul percorso composto

Un solo spawn reale, non simulato:

```
frase   : «Mi preoccupa il clima e quello che sta facendo il governo
           sull'energia, e poi c'è la guerra»
spawn   : ok=True · durata 11,12 s · modello haiku · costo dichiarato 0,0300 USD
risposta: 'clima, governo, energia, guerra'
argomenti dopo il filtro estrattivo: ['clima', 'governo', 'energia', 'guerra']
```

Gli 11 s **non stanno sul percorso della voce**: `_voce_su_turno` lancia
`ascolta()` come task e non lo attende.

### ✅ Un giro vero contro i feed veri — ed è qui che si vede che cosa era rotto

Stessi feed, stesso minuto, stesso gate. Cambiano solo gli argomenti:

| argomenti | letti | passati |
|---|---|---|
| **prima** — `['preoccupa', "sull'energia"]` | 57 | **0** |
| **dopo** — `['clima', 'energia', 'governo', 'guerra']` | 57 | **2** (rilevanza 0,333) |

Card di esempio: *«Putin boccia il piano di Zelensky, a Mosca il capo della
Cia»*, fonte ANSA, `origine_non_fidata: news:ANSA`.

Non era una perdita di qualità: **la funzione non produceva nulla**, in
silenzio. E `sull'energia` non avrebbe potuto agganciare nessun articolo
comunque, perché quella parola non esiste in nessun titolo.

### ✅ La suite intera

`TMPDIR=/tmp/jt uv run pytest -q` → **1172 passed**, zero rossi (erano 1103).

### ✅ La giunzione è verificata misurando, non leggendo

Il difetto ricorrente di questi giorni è «due pezzi scritti, provati, mai
uniti» — sette volte in due giorni. `TestIlMODELLOeCOLLEGATO` verifica che il
motore **chiami** il finto modello, che il compito arrivi formattato e non nudo,
e che un modello che cade ripieghi sul locale. Solo l'ultimo controllo — che la
radice di composizione passi lo spawn — è una lettura del sorgente, perché
costruire l'engine intero in un test costerebbe più di ciò che prova.

### ❌ NON verificato

- **Il percorso dal microfono.** L'estrazione è stata provata con una frase
  scritta, non detta a voce. La catena `voce → _voce_su_turno → ascolta` ha i
  suoi test, ma non l'ho percorsa parlando in questo turno.
- **Il comportamento su conversazione lunga.** Il banco è fatto di frasi
  singole, che è l'input vero di `ascolta()`. La frequenza come ordinamento su
  un testo di molte battute non è misurata da nessuna parte.
- **Il costo su una giornata.** Uno spawn è costato 0,0300 USD dichiarati; a 6
  l'ora sarebbero ~0,18 USD/ora di costo nozionale su abbonamento. Non ho
  osservato una giornata vera.
- **Il ripiego a quota esaurita, sul serio.** È provato con un finto che
  solleva. Il Governor non è mai arrivato a rifiutare davvero in questo turno.

---

## 7. Una Sua premessa che non reggeva

> `tests/test_news_motore.py:53` … Il 15 viene quasi certamente dai 15 spawn
> T2/ora del Governor.

Il nome corretto era `test_col_tetto_di_§15_fa_dieci_minuti`: il 15 era **§15**,
la sezione. L'ho perso io con un `sed` che toglieva il `§`, che Python non
accetta in un identificatore. La Sua conclusione resta giusta — quel numero lì
confonde, e sembrava proprio il tetto degli spawn — e il test adesso si chiama
`test_col_tetto_di_TRE_fa_dieci_minuti`, con una riga che dice da dove veniva.
