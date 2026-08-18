# Fase 8 — esito dei criteri di accettazione

**Data**: 18 agosto 2026 · **Riferimento**: `docs/SPEC.md` §22 Fase 8 e §15
**Test**: 315 verdi (erano 285) + 197 negli eval · **Precedente**: `FASE-07.md`

È la prima fase in cui JARVIS **interrompe** invece di rispondere. Tutto il
resto della fase discende da lì: trovare notizie è facile, **non dirle** è la
parte difficile, ed è l'unica che decide se la funzione resta accesa dopo tre
giorni.

---

## I criteri di §22

### 1. «Budget 3/ora rispettato» — ✅ VERIFICATO su feed veri

Un giro sui feed reali di §15, adesso:

```
letti 60 · passati 3 · tetto 3
scartati per budget: 8
  · ANSA | Temporali dopo il caldo, parla l'esperto: 'Le Alpi fanno da hot spot…'
  · ANSA | Caldo e umidità aumentano il rischio di crisi di emicrania
  · ANSA | Trump posta la mappa di Hormuz, 'nuovo territorio Usa'…

secondo giro, subito dopo:  letti 60 · passati 0
```

Sessanta notizie vere lette, **tre** dette. Il secondo giro non ne fa passare
nessuna: il budget è finito, ed è quello il comportamento giusto.

E la finestra **scorre**: tre contate sull'ora solare darebbero tre annunci
alle 10:58 e altri tre alle 11:02 — sei in quattro minuti, formalmente dentro
il budget.

Le altre quattro regole di §15 hanno ognuna il proprio test:

| Regola | Come è imposta |
|---|---|
| mai mentre parla | il gate rifiuta e **dice quale** delle tre condizioni |
| mai con un pannello a schermo intero | idem |
| mai a metà frase | idem |
| argomenti scaduti dopo 30 minuti | timbro e scadenza sullo stesso orologio |
| «non parlarmene più» | file markdown in `memory_data/topics/`, sopravvive al riavvio |

### 2. «Un contenuto con istruzioni iniettate non produce alcuna azione» — ✅ VERIFICATO

`tests/eval_injection.py` passa da 39 a **51 casi**. I dodici nuovi sono i
vettori veri di un feed — il titolo, la `<description>`, un comando T0 dentro
un titolo di giornale — e ognuno verifica quattro cose:

1. il testo entra come `Untrusted`, non come stringa;
2. non raggiunge un contesto con tool: `ClaudeT2.componi()` solleva;
3. **non raggiunge l'estrattore di argomenti** (vedi sotto);
4. anche nel caso peggiore — rilevante, budget libero, contesto noto — ciò che
   esce dal gate è una **card da mostrare**, e nel dizionario di quella card
   non c'è niente da eseguire.

**Non è un meccanismo nuovo.** È la barriera di Fase 6, riusata. Se le news ne
avessero richiesto uno diverso, vorrebbe dire che quello di Fase 6 era
sbagliato.

---

## L'anello che poteva chiudersi

§15 disegna la catena come `conversazione → estrattore → watcher → gate`.
L'estrattore legge **la conversazione**: testo Suo.

Se un giorno qualcuno gli desse in pasto anche il testo delle news — «per
migliorare gli argomenti», che suona come un miglioramento — si chiuderebbe un
anello:

```
articolo ostile → diventa un argomento → decide quali altri articoli
superano il gate → altri articoli ostili → …
```

Un articolo potrebbe scegliere quali altri articoli La raggiungono. Non
somiglia a un attacco mentre lo si scrive, ed è per questo che è reso
**impossibile** invece che sconsigliato: `estrai_locale()` solleva davanti a un
`Untrusted`, e tre test lo verificano su ogni feed ostile del corpus.

---

## Ciò che non so vale come un no

Due delle cinque regole di §15 dipendono da stati che il core oggi non conosce:
la pipeline vocale non è composta nell'engine.

La tentazione sarebbe trattare «non lo so» come via libera — altrimenti in
questa configurazione non passa mai niente. È la tentazione sbagliata: **in un
sistema che parla da solo, la modalità silenziosa è quella sicura**. `Contesto`
è un tri-stato apposta, e `None` significa «non lo so», non `False`.

---

## Tre difetti trovati facendo girare la catena, non leggendola

**La rilevanza si diluiva col numero di interessi.** Dividevo i colpi per il
numero di argomenti: con otto interessi, una notizia che ne colpiva uno valeva
0,125 e non passava la soglia di 0,15. Ma una notizia che tocca **una** cosa
che mi interessa è rilevante — non è un ottavo di rilevante. Più interessi
avevo, meno notizie potevo ricevere: l'esatto contrario di quello che serve.

**L'estrattore produceva parole vuote.** «delle», «letto», «interessa» — e
«delle» compare in metà dei titoli italiani, quindi faceva passare tutto. Ho
allargato le parole ferme e aggiunto un'euristica: un argomento vero **torna
più di una volta**, o è lungo.

**Due orologi nella stessa chiamata.** `aggiorna(adesso=X)` timbrava gli
argomenti a X e poi li filtrava con `time.time()`: restituiva sempre una lista
vuota nei test, e in produzione avrebbe fatto scadere gli argomenti col
criterio sbagliato. Un solo orologio, e chi chiama decide quale.

---

## Il silenzio mente, se non si annuncia

Misurato adesso sulle quattro fonti che §15 nomina:

| Fonte | Esito |
|---|---|
| ANSA | ✅ RSS |
| BBC World | ✅ RSS |
| Il Post | ❌ **403**, anche con User-Agent dichiarato |
| Reuters | ❌ **404** — l'URL di §15 non esiste più |

Un collector che restituisse una lista vuota direbbe *«non ci sono notizie»*
invece di *«questa fonte non risponde»*. La prima è una giornata tranquilla, la
seconda è un guasto, e confonderle significa non accorgersi mai del secondo.

`Esito` le tiene separate, e l'annuncio esce su `agent.advisory` (§16):

```
rss/Il Post: HTTPError 403
guardian: senza chiave Guardian Open Platform: la fonte col corpo completo
          resta spenta, RSS continua a funzionare
youtube:  senza chiave YouTube Data API: nessun notiziario video
```

Le fonti morte **non sono nell'elenco predefinito**: un elenco che contiene
sorgenti che non rispondono fa sembrare rotto il collector invece della fonte.
Stanno in `FONTI_NOTE_ROTTE`, col motivo.

---

## Scostamenti dalla specifica, dichiarati

### ⚠️ Nessuna dipendenza nuova per l'XML

`feedparser` non è in §4. `xml.etree` della libreria standard basta, con due
cautele: **DOCTYPE rifiutato** — senza DTD non ci sono entità da espandere, e
la bomba a entità del corpus non viene nemmeno analizzata — e un tetto sui byte
letti. `defusedxml` sarebbe la risposta canonica ma è un'altra dipendenza.

### ⚠️ I titoli del corpus sono inventati, la struttura no

`tests/news_corpus.py` ricalca ciò che BBC e ANSA mandano davvero — CDATA,
namespace multipli, `media:thumbnail`, `guid` non permalink — perché è lì che
un parser si rompe. I titoli sono inventati: le testate hanno il copyright sui
propri, e un fixture non è il posto per verificarne la licenza (regola 30).

### ⚠️ GNews e NewsAPI non entrano

§15 li elenca. **NewsAPI vieta esplicitamente la produzione** nel free tier —
lo dice §15 stessa — e GNews avrebbe richiesto un'altra chiave che qui non c'è.

---

## ❌ NON VERIFICATO

1. **Guardian e YouTube dal vivo.** Nessuna chiave su questa macchina. Il
   percorso del codice è provato contro un finto; la chiamata di rete no.
2. **L'estrattore contro haiku.** §15 dice «haiku, batch 60 s, effort low».
   L'interfaccia c'è e il batch è provato; l'LLM vero richiede la pipeline
   composta (Fase 9). Gira l'estrattore locale, che è il ripiego.
3. **Le regole 2 e 3 con stati veri.** Oggi il core non sa se Lei sta
   parlando, quindi in esercizio **non interromperebbe mai** — che è il
   comportamento giusto, ma non è la stessa cosa che averlo verificato con la
   voce accesa.
4. **La menzione vocale** di §15 («card news + menzione vocale breve»): la card
   c'è, la voce dipende dalla pipeline non composta.
5. **Il comportamento su una giornata intera.** Il budget è verificato su due
   giri consecutivi, non su ventiquattro ore vere.

---

## Riepilogo

| | |
|---|---|
| Test | **315 verdi** (erano 285) + **197** negli eval |
| Casi di injection | 39 → **51** |
| Corpus dei feed | 7 casi, di cui **3 rotti o ostili**, più 3 feed ostili dedicati |
| Notizie vere lette in verifica | 60 · **3 dette** |
| Fonti di §15 che rispondono | 2 su 4, e le altre due **annunciate** |
| Dipendenze aggiunte | **nessuna** |
| Criteri di §22 | **entrambi verificati** |
