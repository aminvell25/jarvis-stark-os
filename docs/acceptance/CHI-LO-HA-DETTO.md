# Chi l'ha detto — l'attribuzione al confine della memoria durabile

**Data**: 30 agosto 2026 · **Riferimento**: `PIANO-JARVIS-COGNITIVO` fetta 3,
`ANALISI-SENIOR` §4.1④, `PROTOCOLLO-DI-LAVORO` §8 · **Rollback**: `d878db8`
**Test**: 1901 → **1921**, 25 saltati, **0 rossi**

---

## Il criterio

> «Una sessione in cui JARVIS propone qualcosa e l'utente non obietta produce
> una riga `proposto-e-accettato`, e quella riga **non** entra in
> `_fatti-fissati.md`. Un test lo pinna.»

✅ `TestIlCriterioDellaFetta::test_il_giro_intero` — e il giro è quello vero:
turni su disco → consolidamento → topic con le sezioni → tentativo di fissare →
rifiuto → `fatti_fissati() == []`.

---

## ① La regola non mordeva dove il piano diceva

Il piano metteva la regola sul **consolidamento**. Misurato:
`Consolidatore.esegui()` scrive solo in `topics/` e **non ha mai toccato**
`_fatti-fissati.md`. L'unico che ci scrive è `MemoryStore.fissa()`, e il suo
unico chiamante è il tool **`pin_fact`** — che T1 può invocare.

Cioè: il criterio «quella riga non entra in `_fatti-fissati.md`» sarebbe già
stato vero **senza scrivere una riga di codice**, e la porta vera sarebbe
rimasta aperta. È lì che avviene il passaggio che PASB descrive: un'affermazione
che JARVIS ha prodotto diventa permanente perché un umano ha detto sì a una
finestra che non gli diceva da dove venisse.

Quindi la fetta ha **due** punti, non uno:

```
consolidamento   l'attribuzione si PRESERVA:  due riassunti, uno per corpus
pin_fact         l'attribuzione si USA:       fissa() rifiuta ciò che non è
                                              dichiarato, e la conferma MOSTRA
                                              la prova
```

---

## ② Come si deriva la classe, senza chiedere all'LLM

`PROTOCOLLO-DI-LAVORO` §6: l'LLM non è autorità per «se un'informazione in
memoria è vera». Quindi la classe non gliela si chiede.

**Nel consolidamento viene dalla costruzione.** Si riassume **due volte**, una
sul corpus di ciò che ha detto il Signore e una su ciò che ha detto JARVIS. La
sezione `dichiarato` può contenere solo il riassunto di frasi del Signore
*perché sono le uniche che il modello ha visto in quella chiamata*. È la stessa
idea della `fonte` indipendente di ADR-012: chiedere al modello di etichettare
da solo sarebbe chiedere a chi propone di certificare la propria proposta.

Verificato non a parole: `test_ogni_corpus_vede_SOLO_le_sue_frasi` mette
`PAROLADELSIGNORE` e `PAROLADIJARVIS` nei due campi e controlla che ciascuna
compaia in **un solo** prompt.

E al corpus di JARVIS si dice esplicitamente di chi sono:

> *«Queste sono frasi dette da JARVIS, cioè da te, e il Signore NON le ha
> confermate: non ha obiettato, che non è la stessa cosa.»*

Senza quella riga il modello le riassumerebbe come fatti stabiliti — che è la
cancellazione dell'attribuzione che PASB misura al 33,1 %.

**La terza sezione non passa da nessun modello.** `osservato` è l'elenco dei
tool che sono girati davvero, letto dal campo `azione` dei turni: è la sezione
più affidabile delle tre proprio perché è la meno interessante.

**In `pin_fact` viene da un confronto lessicale** con le parole vere del Signore
in quella sessione. ⚠️ È **debole**, e la soglia (0,6) è **scelta, non
misurata**: non esiste un corpus di fatti fissati su cui tararla — ce ne sono
meno di dieci su questa macchina.

Regge per l'**asimmetria**, ed è tutto il disegno:

| classe dedotta | conseguenza |
|---|---|
| `proposto` / `osservato` | `fissa()` **rifiuta**. Costa un fastidio: si apre il file a mano, che è la via che §5.5 già benedice |
| `dichiarato` | `fissa()` accetta — e resta comunque la conferma umana dell'invariante 3, che adesso **mostra la prova** |

La deduzione può solo **negare** da sola. Per concedere serve ancora un umano, e
a quell'umano si fa vedere la frase esatta su cui la deduzione si regge.
**Il sistema non decide: dichiara.**

---

## ③ Il giro vero, eseguito

```
── pin_fact('Le stampanti 3D sono due')
   la conferma mostra : fissa un fatto permanente — risulta dichiarato
   e la prova         : [dichiarato] «ho due stampanti 3d in laboratorio» (100% delle parole)
   esito              : ok=True  [dichiarato]

── pin_fact("Il Signore dovrebbe dormire di piu'")
   la conferma mostra : RIFIUTATO: risulta proposto-e-accettato, non detto da Lei
   e la prova         : [proposto-e-accettato] «Le suggerisco di dormire di piu', Signore.» (67% delle parole)
   esito              : ok=False → un fatto «proposto-e-accettato» non diventa un fatto fissato

fatti fissati sul disco: ['Le stampanti 3D sono due']
```

La seconda riga è il caso PASB, intercettato: JARVIS aveva suggerito al Signore
di dormire di più, il Signore non aveva obiettato, e **il silenzio non è un
assenso**.

---

## ④ Gli otto sabotaggi, con l'esito

| sabotaggio | rosso |
|---|---|
| `fissa()` accetta qualunque attribuzione | `test_il_resto_NON_entra[×2]`, `test_il_rifiuto_dice_la_via_di_scampo`, `test_il_giro_intero` |
| `classifica` dice sempre `dichiarato` | i tre test della deduzione, e `test_il_giro_intero` |
| il consolidamento torna a un corpus solo | `test_ogni_corpus_vede_SOLO_le_sue_frasi` |
| al corpus di JARVIS non si dice che è suo | `test_al_corpus_di_jarvis_si_DICE_che_sono_sue` |
| le azioni entrano nel prompt | `test_le_AZIONI_non_passano_da_nessun_modello` |
| una metà caduta scrive metà topic | `test_una_meta_caduta_NON_scrive_meta_topic` |
| si guarda JARVIS prima del Signore | `test_nel_dubbio_il_fatto_e_DEL_SIGNORE` |
| una quarta `Attribuzione` | `test_sono_TRE_e_ognuna_ha_un_produttore` |

---

## ⑤ Un orfano scritto e tolto nello stesso turno

`scripts/orfani.py` ha trovato `attribuzione.sezioni()` — un lettore delle tre
sezioni — **un minuto dopo che l'avevo scritto**: «nessun riferimento, in nessun
posto». È la firma esatta della famiglia di §5.29, un pezzo scritto, provato e
mai congiunto.

Non serve, e la ragione è che le sezioni sono **markdown in un file**: una
persona che apre il topic le legge, e T1 le vede inline quando `recall` gli
restituisce il contenuto. Tolto. Un lettore programmatico servirà quando
qualcuno vorrà *misurare* la contaminazione — la fetta 4, `eval_memoria` — e
quel giorno si scrive con il suo chiamante accanto.

---

## ⑥ Che cosa NON è verificato — per nome

1. **La soglia 0,6 non è tarata su niente.** Non esiste un corpus di fatti
   fissati su cui misurarla: su questa macchina ce ne sono meno di dieci. È una
   scelta, e vale quanto vale perché un errore in eccesso lo intercetta la
   conferma umana e uno in difetto costa l'apertura di un file.
2. **Il confronto è lessicale, non semantico.** «Le stampanti sono due» e «ne ho
   un paio» sono la stessa cosa per una persona e due cose diverse per questo
   codice. Il secondo caso finisce in `osservato` e viene rifiutato: sbaglia
   **nella direzione che costa meno**, ma sbaglia.
3. **Solo la sessione di OGGI.** `pin_fact` guarda i turni del giorno corrente:
   un fatto che il Signore ha dichiarato ieri risulta `osservato` e viene
   rifiutato. È un falso negativo dichiarato, non un buco.
4. **Il consolidamento non è mai stato eseguito con un T2 vero in questa
   fetta.** Le prove usano un T2 finto che registra i prompt. Che i due riassunti
   *separino davvero* i contenuti dipende dal modello, e questo non è misurato:
   è misurato che i due prompt contengano corpora disgiunti, che è la parte
   sotto il nostro controllo.
5. **Costa il doppio.** Due chiamate T2 per sessione invece di una. Il costo
   reale non è misurato — `ADR-004` conta i secondi di voce, e il conto degli
   spawn T2 non è stato confrontato prima/dopo.

---

## ⑦ La tensione dichiarata di §5.5 resta

Il consolidamento continua a scrivere **senza conferma umana**, e resta
accettabile per le stesse tre ragioni di `FASE-04.md`: scrive solo dentro
`topics/`, non tocca i fatti fissati, e ogni scrittura finisce in `initiatives/`,
visibile al risveglio.

Questa fetta la rafforza in un punto: prima «non tocca i fatti fissati» era una
proprietà del *codice del consolidatore*; adesso è una proprietà di `fissa()`,
cioè vale per **chiunque** provi a passare di lì, consolidatore compreso.
