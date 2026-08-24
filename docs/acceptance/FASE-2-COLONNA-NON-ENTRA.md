# Fase 2 — la colonna laterale non entra, e il conto lo dice in due minuti

**Data:** 24 agosto 2026 · **Rollback:** `4a273ca` · **Codice scritto: zero**

`DIVARIO-PREMIUM.md` §8, impatto MEDIO, mai ripreso. Il piano la metteva seconda
e chiedeva di misurare **prima** di scrivere il componente. La misura basta.

## L'aritmetica

Griglia 12 colonne da 128 px, 4 righe da 196. Disco del nucleo: centro (768,
422), raggio 163, cioè x 605–931 e y 259–585.

```
colonne occupate dal disco   4 5 6 7
righe   occupate dal disco   1 2
```

Quindi i pannelli vivono in **cols 0–4 e 8–11: nove colonne**, ed è esattamente
quello che la scena `avvio` usa — telemetria 5, cartella 3, agenti 4, con la
riga bassa a completare.

Una banda fissa da 2 colonne a sinistra lascia **cols 2–4 e 8–11: sette**.

**`telemetria` da sola ne dichiara cinque** (`min-width` 550 px = 4,3 colonne).
Cinque non stanno in tre, e in quattro nemmeno: è **R99** — una cella troppo
stretta non stringe il pannello, lo fa debordare, e la Fase 0 lo ha appena
misurato su cinque pannelli.

Spostando `telemetria` verso destra per far posto:

| banda | telemetria finisce a | disco coperto |
|---|---|---|
| 1 colonna | x 128–768 | **163 px** su 326 |
| 2 colonne | x 256–896 | **291 px** |
| 3 colonne | x 384–1024 | **326 px** — tutto |

Oggi il disco è **coperto allo 0,5 %**. Una colonna da 1 sola casella ne
coprirebbe metà.

## La conclusione, e non è un rinvio per prudenza

**Una colonna fissa, `telemetria` a cinque colonne e il centro libero non
coesistono su una griglia da 12 a 1536 px.** Non è una difficoltà: è una somma.
Chi la vuole deve rinunciare a una delle tre, e sono tutte e tre decisioni
scritte:

| rinunciare a | dove è dichiarato | costo |
|---|---|---|
| il centro libero | §25.1, §25.7 «posizione fissa»; la scena costò **tre tentativi misurati** | il nucleo torna dietro i pannelli, che è l'uscita che §25 aveva scartato |
| `telemetria` a 5 colonne | `moduli.js`, `min-width` 550 px | deborda — R99, misurato dalla Fase 0 |
| un pannello della scena | la scena ne ha sei | è una ricomposizione, non una colonna |

## Che cosa NON ho fatto, e perché

Non ho scritto il componente. Sarebbe stato un pannello corretto in una scena
che non lo può contenere, e me ne sarei accorto al primo scatto invece che al
primo conto. Il piano chiedeva venti minuti di misura prima del codice: ne sono
bastati due, perché la geometria è dichiarata e non serviva renderla.

⚠️ **E la colonna resta una cosa giusta.** Il README misura le tre immagini di
famiglia-a e le ha tutte; è *«ciò che dà all'insieme l'aria di un sistema
operativo invece che di un cruscotto»*. Il dato c'è già — `fs.list` e
`source.tree` sono due topic pubblicati. Manca lo **spazio**, e lo spazio è una
decisione sul pavimento, non un componente.

**Fase 2 dichiarata NON FATTIBILE nella scena `avvio` di oggi**, con la somma
che lo mostra. Riapribile appena una delle tre voci qui sopra cade.
