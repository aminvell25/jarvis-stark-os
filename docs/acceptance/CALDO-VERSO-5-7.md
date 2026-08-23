# Il caldo verso 5,70 % — quattro tentativi, e il numero che dipende dall'utente

> Richiesta: portare il caldo dal 3,2 % verso il **5,70 %** del riferimento.
> Misurati quattro assetti. Nessuno arriva a 5,70 **oggi**, e la ragione non è
> il colore.

---

## Prima: dove sta il caldo, nei due

Mappa a griglia 12×8, percentuale di pixel caldi (`r > b + 15`, L > 30) per
cella:

**Riferimento — 5,70 % in tutto, e SPARSO:**

```
  0.1    0    0    0    0    0    0    0  9.3  4.8    0    0
  0.7    0 18.7   30    0 20.9 21.6 29.9 33.1  5.2    8  1.8
  0.2  1.1 21.4 38.2  1.2    0 11.8 24.4   10    0  0.8  0.1
 14.8 14.1  1.2  0.4  2.1    0    0    0    0  4.8  2.5  0.8
 25.2 24.1 10.1    0    3    0    0 20.4  3.2  4.4 10.7  7.6
```

**Noi, prima — 3,1 % in un blocco solo, saturo:**

```
  0.4  0.1    0  0.2 10.8   38 38.2 15.6  0.2  0.1  0.4  0.1
    0    0    0    0   18 69.1 70.2 28.5  0.1    0  0.2  0.1
    0    0    0    0  0.3    0    0    0    0    0  0.4    0
```

Il riferimento tiene **molte celle al 10–38 %**; noi **due celle al 70 %**. Non
è una differenza di tinta: è che i suoi oggetti caldi sono tanti e sparsi, i
nostri uno solo.

---

## I quattro assetti misurati

| assetto | caldo | dev.std | L>60 | disco | verdetto |
|---|---|---|---|---|---|
| solo `cartella` [5,0,3,1] | 3,1 % | 30,0 | 21,0 % | 0,0 % | punto di partenza |
| `cartella` a 2 righe [5,0,3,2] | **7,6 %** | 35,9 | 24,9 % | **33,1 %** | ❌ fuori tetto, e un terzo di disco |
| `cartella` 2×2 [5,0,2,2] | 5,0 % | 32,5 | 22,3 % | 26,3 % | ❌ **232 px < min-width 264** (R99) |
| **+ `file` a righe manila** | **3,8 %** | 31,2 | 24,2 % | **0,0 %** | ✅ tenuto |
| *(+ `file` a corpo manila)* | *7,9 %* | *37,1* | *28,1 %* | *0,5 %* | ❌ fuori tetto |

Due assetti sono caduti su una **regola**, non su un gusto: il 2×2 dà al
pannello cartella 232 px contro una `min-width` dichiarata di 264 — è R99, «una
cella troppo stretta non stringe il pannello, lo fa debordare» — e i nomi dei
file si troncano. Il 3×2 copre un terzo del nucleo e sfonda il tetto di 6 %.

---

## Che cosa è stato tenuto, e perché

**Il file manager entra nella scena, sotto le news, con le righe manila.**

Le news si stringono a una riga. Misurato: quel pannello occupava il **12,3 %
dello schermo** mostrando il proprio stato vuoto, perché il `Watcher` è
costruito e non gira — `news.card` non esce mai. Dodici punti di schermo per due
righe di testo sono il posto più caro della scrivania.

Il file manager ci mette file veri da `fs.list`, e il suo caldo è manila per la
stessa ragione della cartella: §26.5 chiama `--manila` il colore di «cartelle e
**contenitori**», e un elenco di file dentro una radice è un contenitore.

### ⚠️ Ma il caldo segue il CONTENUTO, non il riquadro

Col corpo intero a manila questo pannello portava il caldo a **7,9 %**, sopra il
tetto — e la maggior parte di quella superficie era **vuota**: la radice
mostrata ha una voce sola.

Una superficie calda grande quanto il riquadro dice *«qui c'è un contenitore»*;
una calda quanto le sue righe dice anche **quanto contiene**. Un contenitore
vuoto resta un contenitore — §26.5, «zero è uno stato esplicito» — e lo dice il
conteggio nel piede, non una macchia di colore.

**Conseguenza da dichiarare: il 3,8 % di oggi dipende da quanti file ci sono.**
La radice mostrata ne ha uno. Con cinque o sei righe il caldo arriva da solo a
5,70 %, e con venti lo supera. Il numero non è basso perché manca colore: è
basso perché quella cartella è quasi vuota, ed è giusto che lo dica.

---

## Le misure

| | prima | **dopo** | soglia | riferimento |
|---|---|---|---|---|
| caldo | 3,1 % | **3,8 %** | 3–6 ✅ | 5,70 % |
| dev.std | 30,0 | **31,2** | 32 | 55,7 |
| `L>60` | 21,0 % | **24,2 %** | 25 % | 42,1 % |
| entropia | 2,08 | **2,17** | 2,40 | 3,32 |
| `L>120` | 3,9 % | **4,6 %** | — | 17,4 % |
| disco coperto | 0,0 % | **0,0 %** | — | — |

Audit `files` **0/0**, suite **568 passed**.

⚠️ L'audit ha bocciato ventiquattro volte un `margin-top: 0.5px`: veniva da
`--line-hair` usato come spaziatura. È una **larghezza di linea**, e §11.8 vuole
le spaziature multiple di 4 o dalla scala `--s-*` — mezzo pixel di margine non
appartiene a nessuna scala. Diventato un filetto, che è ciò per cui quel token
esiste.

---

## Che cosa NON è stato fatto

- **5,70 % oggi non si raggiunge** con un assetto che rispetti insieme il tetto
  del 6 %, le `min-width` dichiarate e il centro libero di §25. I due assetti
  che ci arrivavano cadono su una regola ciascuno.
- **Le news restano nella scena** a una riga: mostrano uno stato vuoto vero, e
  toglierle sarebbe una decisione sulla scena, non sul caldo.
- **Il caldo del riferimento è sparso** su tutta l'immagine; il nostro sta in
  due punti. Pareggiare la distribuzione vuole più oggetti caldi — cioè più
  contenuto, o le cartelle libere di §26.5 che sono stato dell'utente.
