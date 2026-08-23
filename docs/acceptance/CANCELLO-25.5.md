# Cancello di governance — §25.5 sale di un gradino

> **Zero codice.** Come il turno 0 di `docs/PIANO-CORE-E-DENSITA.md`: le regole
> di uscita del piano vietano di emendare una regola dentro un turno di
> implementazione, quindi l'emendamento arriva prima e da solo.
>
> Decisione del proprietario, 23 agosto 2026: *«alza §25.5 e riempi anche il
> campo interno»*.

---

## Che cosa la motiva, misurato

Il profilo radiale di `docs/design-reference/famiglia-a/12-logo-anelli-concentrici.png`
— il riferimento che **§25.1 assegna a questo componente** — su un disco di
raggio 120:

| r/R | media L | max L | che cos'è |
|---|---|---|---|
| 0,125–0,475 | **43,3** | 254 | campo scuro interno |
| 0,483–0,742 | **116** | 247 | banda chiara |
| 0,750–0,875 | **45,2** | 243 | banda scura |
| 0,883–0,983 | **91,6** | 249 | banda esterna |

Il tetto precedente era **L ≤ 48 sul tratto a riposo**. Le bande chiare del
riferimento stanno a media 92–125: **il riferimento era irriproducibile per
costruzione**, non per come lo si costruiva.

E il risultato si vedeva. Misurato sul nostro nucleo prima dell'emendamento:
ogni anello fra media 25,6 e 35,5, ogni picco a 47,7–48,5. Un disegno tecnico,
non un oggetto — quello che il proprietario ha chiamato «effetto wireframe».

---

## Che cosa cambia, e che cosa NON cambia

| Elemento | Prima | Dopo |
|---|---|---|
| **Riempimento** del nucleo | *non nominato* | **L ≤ 48** (`--cy-900`) |
| Tratto, riposo | L ≤ 48 (`--cy-900`) | **`--cy-700`, L 100** |
| Tratto, anello attivo | `--cy-700`, L 100 | **`--cy-500`, L 181** |
| `--cy-500` | vietato | ammesso **solo sull'anello attivo, uno per volta** |
| `--cy-100` | vietato | **vietato** |
| Testo del pannello | L 224 | **L 224** |
| Riempimento del pannello sopra | L ≥ 31 | **L ≥ 31** |
| «un solo anello per volta» | regola | **regola** |
| Nessun filter, drop-shadow, bloom | invariante 19 | **invariante 19** |

**La scala non è stata abolita: è stata traslata.** Ogni elemento del nucleo
sale al token successivo e le distanze restano identiche. Il vincolo che §25.5
esiste per tenere — *il nucleo non compete col dato* — è retto da ciò che **non
sale**: il testo dei pannelli resta a L 224, `--cy-100` resta vietato, e un
anello acceso resta uno.

### La riga nuova: il riempimento

La stesura precedente non nominava il riempimento del nucleo perché il nucleo
non ne aveva — era fatto di soli tratti. Il riferimento invece è fatto di
**superfici**. Senza una riga che le governi, la prima superficie che qualcuno
aggiunge non ha un tetto, e il tetto del tratto non la copre: sono due cose
diverse, e una superficie pesa molto più di un tratto perché ha area.

---

## Che cosa questo permette, e che cosa costa

**Permette** di riprodurre la struttura del riferimento: campi scuri pieni a
L ≤ 48, dettaglio a L 100, anello che lavora a L 181. Restano fuori i suoi
picchi a L 243–254, che nel riferimento sono **bloom** — e l'invariante 19 li
vieta indipendentemente da §25.5.

**Costa** tre cose, e vanno verificate misurando, non date per buone:

1. **Il marchio.** È a `--cy-700` (§25.13.2 regola 4) e adesso ci sta anche il
   tratto degli anelli a riposo: il nome smette di essere il pezzo più chiaro
   del nucleo. §25.13.5 chiede al marchio un contrasto fra 3,0:1 e 5,0:1 contro
   il composito sottostante — va **rimisurato**, e se cade fuori è §25.13 a
   dover essere riletta, non §25.5 a essere riaggiustata.
2. **La densità.** La metrica di §11.8 conta i pixel sopra L 60. Il nucleo a
   riposo passa da L 48 a L 100: **comincia a contare**. È la tensione 1 di
   Parte 3 di `docs/PIANO-CORE-E-DENSITA.md` — «il nucleo resta un costo senza
   resa metrica» — che si scioglie da sola. Va misurata: se `L>60` sale, il
   guadagno è vero; se non sale, il nucleo è troppo piccolo perché conti, e
   allora lo dice il numero.
3. **Il precedente.** «Il nucleo non usa mai `--cy-500`» era una frase secca, e
   adesso ha una condizione attaccata. Le condizioni si erodono. Il presidio è
   che la condizione sia **meccanizzata**: `tests/test_nucleo.py` conta gli usi,
   e la verifica in finestra vera conta gli anelli accesi insieme.

---

## Costo del ritorno

Piccolo e contato. Tre valori in `ui/src/desk/sfondo.js` — il tratto a riposo,
il tratto acceso, il riempimento — più la tabella di §25.5 e due asserzioni in
`tests/test_nucleo.py`. Nessun componente fuori dallo strato di presenza cambia:
il pannello di §10.3 disegna la stessa geometria e non è toccato, perché il suo
colore l'ha sempre dichiarato per conto proprio.

Quello che **non** torna indietro da solo è il precedente della condizione su
`--cy-500`. Se un giorno §25.5 tornasse al tetto vecchio, quella riga va tolta
esplicitamente, o resta scritta un'eccezione a una regola che non esiste più.

---

## Che cosa il turno di implementazione deve portarsi dietro

Tre cose, e ognuna è verificabile:

1. **Il riempimento sta sotto L 48.** Non è il tetto del tratto: è la riga nuova
   della tabella, e vale per una superficie che ha area.
2. **Un anello acceso per volta.** Già verificato in finestra vera dal blocco
   `nucleo` di `npm run verifica:scrivania`; adesso quella verifica è ciò che
   tiene in piedi la condizione su `--cy-500`, non più solo una conferma.
3. **§25.13.5 rimisurato**, e l'esito scritto qualunque sia. Il marchio è
   l'elemento che questo emendamento mette più in difficoltà.
