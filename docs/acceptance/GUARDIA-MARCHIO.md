# Turno 5 — la guardia, senza toccare il socket del core

> Il turno 4 ha misurato §25.13.5 in nove stati. Una misura fatta una volta è
> una fotografia: senza guardia, il prossimo che tocca il nucleo la invalida
> senza saperlo — ed è successo **due volte in un giorno**, a `b2f7360` e a
> `4611cb6`.

---

## Il problema, e perché non si risolve con un test che scatta

`densita.mjs --marchio` non era in `package.json` e nessun test lo toccava.
Ma un test che apre Electron rimetterebbe in suite il conflitto che il turno 1
ha documentato: **cinque file di test usano il socket del core vivo**, e uno
scatto in parallelo gli sposta il layout sotto. Misurato oggi: la suite intera
fallisce `TestIconeVere` circa una volta su due quando qualcosa tocca quel
socket.

## La forma scelta: cattura manuale, verifica automatica, **freschezza provata**

| dove | che cosa |
|---|---|
| `package.json` | `verifica:marchio` = cattura degli stati **poi** misura, in un comando |
| `densita.mjs --marchio-stati` | gira su ogni cartella **richiamando la funzione `marchio()` già esistente** — nessuna seconda implementazione della metrica |
| `docs/acceptance/MARCHIO-STATI.json` | l'esito: contrasto e luminanza per stato, il franco misurato, e **un'impronta dei sorgenti del nucleo** |
| `tests/test_nucleo.py` | legge quell'esito — **nessun browser, nessun socket** — e verifica quattro cose |

Le quattro:

1. l'esito **esiste**;
2. l'**impronta combacia** coi sorgenti attuali;
3. ogni **stato** sta dentro la forbice 3,0–5,0;
4. il **franco** è positivo.

### L'esito non sta in `shots/`, e non è un dettaglio

`shots/` è ignorato da git. Un test che si salta quando il file manca **è un
test che non c'è**: su un clone pulito non verificherebbe niente e nessuno se ne
accorgerebbe. L'esito è versionato in `docs/acceptance/`, che è anche il posto
giusto — è la metà leggibile-da-macchina di un documento di accettazione.

### L'impronta, e che cosa NON copre

SHA-256 dei primi 16 caratteri su tre file:

```
ui/src/desk/sfondo.js      il marchio, il campo, le regole di scope
ui/src/anim/rings.js       la geometria: raggi, spessori, quali fasce
ui/src/style/tokens.css    i colori di tutte e due
```

**Verificato che morda**: cambiato un byte in `tokens.css`, il test fallisce
nominando le due impronte e il comando da eseguire; ripristinato, torna verde.

⚠️ **Il limite è dichiarato nel codice e qui**: la guardia lega tre file. Una
modifica altrove che cambi il composito sotto il nome — `ui/src/style/app.css`,
per dire — **non la fa scattare**. Chi ne aggiunge uno lo mette in `FONTI`, in
`scripts/densita.mjs`, e il messaggio d'errore del test lo ricorda.

---

## Il franco, adesso misurato sui pixel

Il turno 4 asseriva il franco in `verifica:scrivania` usando la **semi-diagonale
del riquadro** del marchio: un limite superiore, perché gli angoli del riquadro
sono vuoti. La guardia lo misura sui **pixel di tratto veri**, su tutti gli
stati insieme:

```
l'inchiostro arriva a          r 64,1 px
la fascia più interna comincia a 73,4 px
franco                            9,3 px
```

Le due misure convivono e rispondono alla stessa domanda con due precisioni:
4,2 px conservativi in `verifica:scrivania` (che gira senza browser di misura),
9,3 px reali qui.

---

## L'esito

```
_variante-campo-void   3,43:1   lum 26,1   inchiostro r 64,1   (variante, non concorre)
ascolto                3,04:1   lum 35,6   inchiostro r 64,1   ✅
offline                3,04:1   lum 35,6                        ✅
onda                   3,04:1   lum 38,4                        ✅
riposo                 3,04:1   lum 35,6                        ✅
subagent               3,04:1   lum 35,6                        ✅
t0                     3,04:1   lum 38,4                        ✅
t1                     3,04:1   lum 35,6                        ✅
t2                     3,04:1   lum 35,6                        ✅
warn                   3,04:1   lum 35,6                        ✅

franco 9,3 px · impronta f278eb2c7de70e06
```

Le **varianti** — le cartelle che cominciano con `_` — si misurano e si
riportano ma **non concorrono al giudizio**: `_variante-campo-void` è una delle
uscite di §25.13 resa misurabile, e un esperimento che fallisse non deve
bocciare una build per una cosa che nessuno ha messo nel prodotto.

---

## Misure

**Densità invariata**: entropia 1,76, `L>60` 12,5 %, dev.std 22,6. Come il
turno 4, questo è un presidio e non cambia un pixel — è l'effetto atteso che §4
gli assegna.

Suite: **562 passed** (561 più la guardia).

---

## Che cosa NON è stato verificato

- **L'impronta copre tre file.** È il limite noto, dichiarato in due posti.
- **La cattura resta manuale.** Se qualcuno cambia il nucleo, committa e non
  esegue `npm run verifica:marchio`, la suite lo ferma — ma solo alla prossima
  esecuzione della suite, non al momento del commit. Un hook di pre-commit
  sarebbe il passo successivo, e non è stato fatto.
- **`critical`** continua a non essere fra gli stati catturati.
- **Il tetto di 5,0:1** non è mai stato esercitato: tutti gli stati stanno al
  pavimento della forbice, non al soffitto.
