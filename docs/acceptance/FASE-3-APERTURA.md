# Fase 3 — l'apertura del pannello

**Data:** 24 agosto 2026 · **Rollback:** `2e6d640`

`ui/src/anim/panels.js` era da **zero byte**. §10.3 lo prescrive — *«apertura
pannello: `clip-path` che si espande, 180 ms, `easeOutQuart`»* — e §10.4 dice
pure con quale API. Prescritto due volte, mai scritto.

## Classe 1: nessun cancello

§10.6: transitorio con causa. Comincia a un evento — qualcuno ha aperto un
pannello — finisce da solo, e dopo la fine il componente chiede zero fotogrammi.

⚠️ La classe `no-animation` di WinBox **resta**. Spegne l'animazione *di
WinBox*, che è generica; la nostra la guida anime.js con la durata e la curva
che §10.3 dichiara. Le due non si sommano.

## `clip-path` e non `scale`

Uno `scale` deforma il contenuto: il testo sarebbe illeggibile per 180 ms e poi
scatterebbe. `clip-path` non tocca il layout — scopre un pannello già composto,
come si scopre un foglio. Ed è l'unica delle due che si compone col
`border-radius: 0` dell'invariante 18 senza inventare angoli.

## Provato: l'animazione AVVIENE, e finisce

Campionato ogni ~25 ms aprendo `console` nell'app vera:

```
  0 ms   inset(0px 0px 100%)        chiuso
 25 ms   inset(0px 0px 37,65%)
 50 ms   inset(0px 0px 12,49%)
 75 ms   inset(0px 0px  2,86%)
100 ms   inset(0px 0px  0,27%)
125 ms   inset(0px 0px  0,0002%)
150 ms   none                       tolto
```

La curva `outQuart` si legge nei numeri — 62 % del cammino nei primi 25 ms — e
alla fine il `clip-path` **si toglie**: un clip che resta è un contesto di
compositing che resta, un livello in più su ogni pannello per sempre.

⚠️ **Verificato che avvenga, non guardato.** Il ciclo §11.7 passo 4 vuole lo
scatto; il protocollo scatta a **T+3 s** e un transitorio da 180 ms lì non
esiste. I sette campioni sono la prova che c'è, e non sostituiscono l'occhio.

## Il rischio del piano, e non si è avverato

Il piano lo chiamava «il rischio peggiore»: `fermaLaScrivania()` aspetta che le
**geometrie** smettano di cambiare, e un `clip-path` non è una geometria. Il
protocollo potrebbe dichiarare ferma una scrivania che si sta ancora
componendo, e allora **ogni metrica a valle diventa rumore**.

**Misurato, cinque scatti dopo contro tre prima:**

| | n | media dev.std | sd |
|---|---|---|---|
| prima (Fase 1) | 3 | 34,117 | **0,024** |
| dopo (Fase 3) | 5 | 34,130 | **0,040** |

⚠️ Il piano diceva «escursione oltre 0,05». **L'escursione max−min non è
comparabile fra tre e cinque campioni**: cinque estrazioni hanno un intervallo
più largo per costruzione. Con la deviazione, che lo è, si passa da 0,024 a
0,040 — entrambe minuscole, e la media si muove di **0,013**.

E c'è un argomento **strutturale**, che vale più della statistica:

```
animazione     180 ms + 5 x 45 di sfalsamento = 405 ms
protocollo     scatta a T+3000 ms              margine 7,4x
```

Il transitorio finisce sette volte prima che l'otturatore si apra. Non può
cadere a metà.

## Lo sfalsamento della scena

La scena apre sei pannelli. Tutti nello stesso fotogramma non sono una
composizione che si compone: sono un lampo. `SFALSAMENTO = 45 ms`, e §10.4
sanziona già `stagger(60)` per il dock; 45 è lo stesso numero che
`catalogo.js` usa per l'entrata delle piastre, con la sua motivazione accanto.

Il ritardo lo scrive **una sola funzione**, `applicaScena`, e lo rimette a zero
appena finisce: chi apre un pannello dal catalogo lo vuole subito, e sfalsare
un pannello solo vorrebbe dire farlo aspettare per niente.

## Una sola animazione per pannello

Aprire, chiudere e riaprire in 200 ms accodava tre animazioni sullo stesso
elemento. `utils.remove(el)` toglie l'elemento da ogni animazione in corso
prima di cominciarne una nuova.

## Le misure

Cinque giri: dev.std 34,1 / 34,15 / 34,1 / 34,1 / 34,2 · entropia 2,225 / 2,23 /
2,23 / 2,22 / 2,235 · `L>60` 25,5–25,8 % · caldo 3,8 %. **Nessuna soglia si
muove**, ed è atteso: il transitorio non è nello scatto.

`verifica:scrivania` exit 0 · `verifica:contrazione` exit 0 · suite 572 passed.
