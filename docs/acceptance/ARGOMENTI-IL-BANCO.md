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
| H7 — posizione, e se vuoto tieni tutto | 0,274 | 0,850 |
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
in cui la regola sa di non sapere e risponde comunque: **−0,136 di precisione**
(0,274 contro 0,410, misurato). La lista vuota è innocua perché
`MotoreNews.un_giro()` senza argomenti non guarda affatto.

### Che cosa la regola nuova ha smesso di fare

> ⚠️ **Riscritto il 26 agosto.** La prima stesura diceva che il caso perso è «il
> sostantivo nudo o l'elenco». **Era il caso sbagliato**, e non per un dettaglio:
> quelli sono rari nel parlato, mentre il caso vero è comunissimo.

**La coordinazione dentro una frase normale.** In «sto leggendo di intelligenza
artificiale e semiconduttori» sopravvive **solo `intelligenza`**: `artificiale`
segue un sostantivo e `semiconduttori` segue una congiunzione, e nessuno dei due
segue una parola di `INTRODUCONO`. Cadono proprio i due termini più specifici
della frase. La regola vecchia ne dava quattro — `artificiale`, `intelligenza`,
`leggendo`, `semiconduttori` — cioè tre giusti e un gerundio.

E il sostantivo nudo, che resta perso ma conta meno: `estrai_locale("clima")`
dà la lista vuota, ed era l'input di tre test del motore che scrivevano
`ascolta("clima")` come scorciatoia, riscritti con frasi vere.

#### Il banco non può dire niente su questo, ed è misurato

**Zero frasi su 43 contengono una coordinazione.** Non «poche»: nessuna. Il
richiamo aggregato non la vede perché il fenomeno non c'è nel corpus, ed è la
conseguenza diretta della provenienza — 43 frasi nate per una proprietà
ortogonale non hanno nessuna ragione di contenere ciò che serve qui.

Il rilevatore è **controllato su nove prove** prima di fidarsi dello zero, perché
uno zero può venire da una regex rotta: cinque frasi con coordinazione che deve
accendere, e quattro con la copula `e'` — che dopo il taglio dell'apostrofo si
scrive come la congiunzione — che deve lasciare spente.

Lo zero è fissato come **tripwire** e non come nota: se un giorno il corpus ne
conterrà una, `test_il_banco_NON_misura_la_coordinazione` diventerà rosso e dirà
di riprendere la decisione col numero in mano.

#### E il rimedio più economico è un non-fatto

«In *di X e Y*, `e` propaga a Y ciò che `di` ha dato a X» **non cambia un solo
esito sul banco, e non recupera nemmeno quella frase**: la catena si è già rotta
su `artificiale`, che segue un sostantivo e non una congiunzione. Il caso perso
sono *due* casi — la coordinazione e il modificatore dopo la testa — e l'eredità
attraverso la congiunzione ne tocca uno solo.

L'unica regola che recupera la frase è tenere la catena aperta **anche
attraverso le parole piene**, cioè «dopo il primo articolo, tieni tutto». Quella
il banco la misura eccome, perché si accende su 13 frasi su 43:

| | precisione | richiamo |
|---|---|---|
| catena stretta (adottata) | **0,410** | 0,800 |
| catena larga | 0,365 | **0,950** |

Recupera tre attesi veri (`lavoro`, `scientifica`, `diesel`) e aggiunge dieci
falsi (`pesante`, `deciso`, `puntuale`, `paziente`, `stavolta`, `italiana`,
`importante`, `senti`, `esci`, `passi`). **Per la politica dichiarata prima di
misurare** — la precisione è il cancello, il richiamo si riporta perché §15
mette un tetto alle interruzioni e non un minimo — **non si adotta**. Resta
misurata in `catena_larga`, così la decisione è rivedibile con un numero invece
che con un ricordo.

E la conclusione è la stessa di prima, per la terza volta: ciò che distingue
`artificiale` (da tenere) da `pesante` (da buttare) non è la forma. Sono
entrambi aggettivi dopo la testa dentro un sintagma introdotto. **È semantica.**

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

## 3bis. Haiku supera la barra — misurato il 26 agosto, cinque giri

La barra era stata dichiarata prima di misurare, e poi applicata **solo al
locale**. Haiku è stato collegato perché il locale non ci arriva, ma la sua
precisione su questo banco non era mai stata misurata: se stesse anche lui
sotto, il collegamento avrebbe comprato costo e latenza senza comprare la
proprietà.

**Cinque giri, 215 spawn, 11,3 USD nozionali, 6 minuti.** Le risposte grezze
sono in `docs/acceptance/HAIKU-RISPOSTE.json` e la metrica si **ricalcola da
lì** a ogni giro di test, col parser di produzione: non è un numero copiato.

| | precisione | richiamo |
|---|---|---|
| locale (il ripiego) | 0,410 | 0,800 |
| **haiku + filtro (produzione)** | **0,733 · 0,769 · 0,800 · 0,917 · 1,000** | 0,520 |
| haiku nudo, senza filtro | 0,138 · 0,164 · 0,222 · 0,239 · 0,480 | 0,520 |

**Esito: cinque giri su cinque sopra 2/3. Il peggiore ci sta di 0,066.** Per la
regola di decisione dichiarata prima: *P > 2/3 → haiku resta collegato e la
barra è soddisfatta da chi doveva soddisfarla*. Nessuna rilettura della scelta
fra catena stretta e larga.

### Le tre trappole, nominate

**① Haiku è stocastico, e l'ampiezza è più grande del divario.** Fra il giro
peggiore e il migliore ci sono **0,267**; la media (0,844) dista dalla barra
**0,177**. Per il criterio di §11.7 questo vuol dire che **la media non è un
valore dichiarabile**: con cinque giri non so dire *quanto* è precisa. So dire
da che parte sta, perché la decisione chiede un lato e non un valore, e cinque
giri su cinque stanno dalla stessa parte. **Non escludo che un sesto giro
scenda sotto**: servirebbe un FP in più del giro peggiore.

**② Non è haiku a passare la barra: è haiku più il filtro estrattivo.** Nudo sta
a **0,249 di media**, sotto la barra in tutti e cinque i giri e sotto il locale
in quattro su cinque. La ragione si legge nelle risposte grezze: invece della
riga vuota che il prompt chiede, il modello scrive prosa —

> `'(riga vuota)'` · `'Attendete, ho notato che il testo che mi hai passato è una…'` ·
> `'riga vuota\n\n(Il testo non parla di argomenti specifici del…'`

— e senza filtro quelle parole diventerebbero argomenti. Il filtro era nato per
l'invariante 2, contro un modello che *inventa*; si scopre che regge anche la
precisione. **Se un giorno il filtro venisse tolto per semplificare, la barra
cadrebbe con lui.**

⚠️ Una prima stesura del test asseriva «haiku nudo è sempre peggio del locale».
**Falso**, e l'ha detto il test: il giro migliore fa 0,480 contro 0,410. Vero è
che la media sta sotto e che nessun giro raggiunge la barra.

**③ La Sua premessa sul batch NON regge, e il difetto è mio.** Lei ha scritto
che in produzione haiku riceve «un batch di tutto ciò che è stato detto in
600 s». **Non è così.** `MotoreNews.ascolta(detto)` passa **una singola
battuta**, e il «batch» di `EstrattoreLLM` è un **limitatore di frequenza, non
un accumulatore**: dentro la finestra le altre battute vengono **scartate**, non
sommate. Verificato eseguendo — tre battute nella stessa finestra, una sola
arriva al modello.

Quindi la misura frase per frase **è** il percorso di produzione, e la trappola
③ non si applica a questo numero. Ma il difetto sotto è serio, ed è mio: a 60 s
si perdeva poco, e **portando il batch a 600 s l'ho reso dieci volte peggiore
senza accorgermene**. Oggi haiku vede una frase ogni dieci minuti e nove minuti
e mezzo di conversazione spariscono.

Non lo correggo in questo turno: accumulare cambia ciò che il modello riceve e
rifà questa misura, appena pagata su un percorso a frase singola. È fissato in
`TestIlBatchSCARTAinveceDiACCUMULARE`, che diventa rosso il giorno in cui il
comportamento cambia e dice di rifare la misura.

E vale la pena notare che con l'accumulazione haiku avrebbe **più** contesto di
adesso: questo 0,733 del giro peggiore è plausibilmente un **limite inferiore**.

### I falsi positivi, elencati e non sommati

Sei distinti in cinque giri. **Tre su sei sono etichette discutibili**, cioè la
parte del numero che non regge da sola:

| | FP | discutibile? |
|---|---|---|
| 3/5 | `luce` da «spegni la luce quando esci» | **sì** — in contesto è un'istruzione di casa, ma «luce»/energia è una parola da notizia |
| 2/5 | `workspace` da «workspace non è una parola italiana» | **sì, molto** — la frase parla proprio di quella parola; la mia etichetta vuota è una scelta, non un fatto |
| 1/5 | `volume` da «volume alto di poesie» | **sì** — «volume» può essere un tomo; la frase è ambigua di proposito |
| 2/5 | `raccontami` da «raccontami una cosa interessante» | no — è un verbo |
| 1/5 | `occhio` da «chiudi un occhio stavolta» | no — modo di dire |
| 1/5 | `orecchie` da «apri bene le orecchie» | no — modo di dire |

Se le tre discutibili fossero rietichettate a favore di haiku, la precisione
salirebbe. **La misura è quindi un limite inferiore anche da questo lato**, ed è
la ragione per cui la regola di decisione guarda un lato e non un valore.

### Il richiamo, che è il prezzo

Haiku ha **meno** richiamo del locale: 0,520 contro 0,800. È molto più prudente.
Cinque attesi non li trova **mai** in cinque giri — `capitale`, `documentario`,
`inglese`, `progetto`, `scientifica` — e altri quattro li perde in quattro giri
su cinque (`chiavi`, `divulgazione`, `email`, `video`). Legge «cose del mondo di
cui si potrebbero leggere notizie» in senso stretto, e scarta ciò che è solo un
sostantivo concreto.

Per la politica dichiarata — la precisione è il cancello, §15 mette un tetto
alle interruzioni e non un minimo — è la direzione giusta. **Ma non è gratis, e
va scritto**: un argomento perso è una notizia che non arriva mai.

---

## 3ter. Lo scarto è chiuso — e nella stessa riga c'era un secondo difetto

> ⚠️ **La formula della cadenza non è stata toccata.** È giusta. Il difetto era
> a valle: i 600 s hanno moltiplicato per dieci una perdita che a 60 s si vedeva
> appena.

### I due difetti stavano nella stessa condizione

```python
if ora - self._ultimo < self._batch_s and self._argomenti:
```

**① Scartava invece di accumulare.** Dentro la finestra le battute dopo la
prima non arrivavano mai al modello, e non venivano rimandate: sparivano.

**② `and self._argomenti` spegneva il limitatore** nel caso più comune. Se
l'estrazione non trovava argomenti — 28 frasi su 43 del corpus, e sul percorso
a frase singola **162 spawn su 215 danno lista vuota** — la condizione era
falsa e **ogni battuta faceva uno spawn**. Misurato: dieci battute in dieci
secondi, **dieci spawn**, contro un tetto di 15 all'ora.

I due si nascondevano a vicenda: chi guardava lo scarto vedeva «una battuta per
finestra» e concludeva che il limitatore funzionava. La cura è la stessa per
entrambi — il cancello è **da quanto non si chiede** (`_ultimo`), non **se si è
trovato qualcosa** (`_argomenti`).

### La misura richiesta: battute che raggiungono il modello

Undici battute in una conversazione che attraversa la finestra:

| | al modello | perse per sempre |
|---|---|---|
| prima | **2 / 11** | **9** |
| dopo | **11 / 11** | **0** |

Calcolata ricostruendo il comportamento vecchio dentro il test, non citandolo.

### ① Che forma di accumulo — la seconda, e che cosa si perde a non prenderla

Presa la **forma 2**: la prima battuta parte subito, le successive si accumulano
per la fine finestra. Costa la riga `self._ultimo == 0.0`.

Conserva una proprietà che oggi c'è: dopo un silenzio, la prima cosa detta
diventa argomento **adesso**. Con la forma 1 — accumulare tutto — riaccendendo
JARVIS e dicendo «mi preoccupa il clima» non ci sarebbe nessun argomento per
dieci minuti.

E una seconda ragione che vale più della latenza: con la forma 2 la produzione
ha **due ingressi**, e la misura di ieri su frasi singole **continua a
descriverne uno**. Con la forma 1 gli 11,3 USD sarebbero stati tutti da buttare.

**Il prezzo della forma 2, dichiarato**: due percorsi da misurare invece di uno,
e un modello che vede due distribuzioni di ingresso diverse.

### ② Il tetto della coda, e che cosa succede al superamento

⚠️ **Non è derivabile dai nostri numeri**, e lo dico come per il pavimento dei
60 s: viene da fuori. Il parlato conversazionale sta intorno alle **150 parole
al minuto**, una parola italiana con lo spazio intorno ai **7 caratteri**. Quei
due numeri non li misura questo progetto.

Ciò che è nostro è la **moltiplicazione**: il tetto è quanto si può dire in una
finestra intera parlando senza fermarsi, quindi **segue il batch** invece di
essere una costante. 600 s → 10 500 caratteri; 150 s → 2 625. Ha un test che
verifica che cambi.

**Al superamento non si scarta niente: si manda in anticipo, e si scrive nei
log** (`coda_argomenti_piena`). Scartare la più vecchia o la più nuova sarebbe
lo stesso difetto in un posto nuovo, silenzioso come quello appena corretto.

Il costo è uno spawn in più, ed è limitato: riempire il tetto richiede una
finestra intera di parlato ininterrotto, quindi al peggio il ritmo raddoppia —
**12 spawn l'ora contro i 15** di `MAX_PER_WINDOW`. Non è fortuna: è il tetto a
essere definito come «una finestra di parlato». Ha un test.

### ③ La misura di haiku sul percorso nuovo — rifatta, non dichiarata superata

45 spawn, gruppi contigui da 5, **2,21 USD** (un quinto del percorso a frase
singola). L'atteso di un gruppo è l'**unione** degli attesi delle sue frasi:
nessuna etichetta nuova.

| percorso | precisione | richiamo | nudo |
|---|---|---|---|
| frase singola (prima battuta) | 0,733 · 0,769 · 0,800 · 0,917 · 1,000 | 0,520 | 0,249 |
| **gruppi da 5 (fine finestra)** | **0,833 · 0,889 · 0,900 · 0,909 · 1,000** | 0,450 | 0,526 |

**Cinque su cinque sopra la barra, e con più margine di prima**: 0,833 contro
0,733 nel giro peggiore. Più contesto, più precisione — la direzione che ci si
aspettava, misurata invece che sperata.

Il filtro estrattivo **conta meno ma conta ancora**: con più contesto il modello
scrive meno prosa e il nudo sale da 0,249 a 0,526 — sempre sotto la barra.

Il richiamo scende ancora (0,450): haiku su un gruppo sceglie i temi dominanti e
lascia cadere quelli di passaggio. Coerente con la politica, e non gratis.

### ④ L'effetto collaterale sulla lista — misurato, e non morde

**Il tetto di `MAX_ARGOMENTI = 8` non scatta mai**: il gruppo più ricco produce
6 argomenti. C'è un test che diventa rosso il giorno in cui morde.

**Il TTL non cambia comportamento**, perché `_argomenti` viene **sostituito** a
ogni estrazione: i 30 minuti si applicano solo se si smette di parlare, prima
come dopo.

E la relevance a valle **non presume una lista corta**: `rilevanza_per_parole`
non divide per il numero di argomenti — era la prima versione e fu corretta —
e satura a tre colpi. Una lista più lunga può solo aiutare.

**Il numero che spiega il pannello vuoto**: la lista di argomenti era vuota in
**162 spawn su 215 (75 %)** sul percorso a frase singola; a gruppi lo è in
**17 su 45 (38 %)**. Una lista vuota vuol dire che `un_giro()` non guarda i feed
affatto.

### Il gate NON è stato rimisurato in questo turno

È deliberato, e su Sua indicazione: prima si chiude lo scarto, o l'effetto
verrebbe attribuito a haiku. I due restringimenti si sommavano — una battuta
sola al modello, e quella passata da un estrattore al 52 % di richiamo — e
nessuno dei due allarmava da solo.

### Le bocciature

- **Rimesso lo scarto** (`and self._argomenti` + `_coda.pop()`): **4 test
  rossi**, fra cui la misura delle battute e il limitatore.
- **Tolto il tetto della coda**: 1 test rosso, quello dell'invio anticipato.
- **La tripwire di ieri ha bocciato da sola** appena la correzione è entrata,
  col messaggio giusto: «il batch ACCUMULA, il difetto è corretto — rifai la
  misura di HAIKU-RISPOSTE.json». È stata rimossa e sostituita dai test del
  comportamento nuovo.
- Le perturbazioni annullate con **copie in scratch**, mai con `git checkout`,
  che da ieri è nei `deny`.

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

### ✅ Due numeri erano invecchiati, e li ha trovati un test

`topics.py` citava **0,421** di precisione mentre il valore vero è **0,410**: il
421 veniva da una misura fatta prima che `INTRODUCONO` prendesse le forme elise
(`dell`, `nell`, `quest`). Non era sbagliato quando fu scritto — è rimasto
indietro.

Ho scritto una guardia invece di correggere a mano, e la guardia ne ha trovato
**un secondo che non avevo visto**: il prezzo del ripiego, citato **0,155**,
vero **0,136**. Stessa causa.

`TestINumeriCITATI` confronta ogni cifra citata in `topics.py` e `engine.py` con
le **cinque quantità che il banco calcola**. Provato che boccia: rimesso 0,421,
il test diventa rosso e stampa quali sono i valori veri.

### ✅ Le due guardie di haiku bocciano — e una NON bocciava

**① Ritirato il filtro estrattivo da `_dalla_risposta`** (produzione): cinque
test diventano rossi, fra cui `test_ogni_giro_sta_SOPRA_la_barra`. È la prova
che la misura di haiku passa dal **parser vero** e non da una copia, e che
coglierebbe proprio la regressione che conta.

**② `TestIlBatchSCARTAinveceDiACCUMULARE` non discriminava.** La prima stesura
chiamava tre volte con l'orologio fermo e verificava che una sola battuta
arrivasse al modello — ma quello lo garantisce il **limitatore di frequenza**,
che c'è in entrambi i casi. Facendo accumulare `aggiorna` per prova, il test
restava **verde**.

> **Terza occorrenza in questo arco** di «criterio vero per il motivo
> sbagliato» (§11.7 regola 4): prima `count(CHIUSURA) == 1` sulla busta
> contraffatta, poi `"perche" not in ...`, adesso questa. Tutte e tre trovate
> **eseguendo la bocciatura**, nessuna rileggendo.

Riscritto facendo **superare** la finestra all'orologio: adesso, con
l'accumulazione messa per prova, diventa rosso e dice di rifare la misura di
haiku.

### ✅ `git checkout` è passato nei `deny`

Ieri `git checkout tests/eval_argomenti.py` ha buttato via lavoro non
committato. L'allowlist negava `rm -rf`, `sudo`, `curl` — il distruttore
famoso — e non quello che ha morso davvero. Su lavoro non committato
`git checkout <file>` è irreversibile esattamente come un `rm`, e con lui
`git restore` e `git reset --hard`. Tutti e tre in `deny`, accanto a `rm -rf`,
che è la famiglia a cui appartengono.

Costo accettato: anche `git checkout -b` viene negato. In un progetto che sta
su `master` con un turno = un commit, è un costo piccolo.

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
  singole — che è l'input vero di `ascolta()`, e adesso si sa **perché**: il
  batch scarta invece di accumulare, quindi una conversazione lunga non arriva
  mai all'estrattore. La frequenza come ordinamento non è misurata da nessuna
  parte, e oggi non ha nemmeno occasione di servire.
- **Haiku su un batch accumulato.** È il percorso che ci sarà dopo la
  correzione del difetto, e questa misura non lo descrive. Con più contesto
  dovrebbe andare meglio: 0,733 è plausibilmente un limite inferiore, ma
  «plausibilmente» non è una misura.
- **Un sesto giro di haiku.** Cinque su cinque sopra la barra; l'ampiezza fra i
  giri è più grande del divario dalla media, quindi non escludo che un sesto
  scenda sotto. Servirebbe un falso positivo in più del giro peggiore.
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
