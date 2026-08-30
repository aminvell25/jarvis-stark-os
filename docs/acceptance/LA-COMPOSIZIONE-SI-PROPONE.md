# L'LLM propone, il compositore dispone — ADR-013, fetta 5

**Data**: 30 agosto 2026 · **Riferimento**: `docs/DECISIONI-COGNITIVE.md` ADR-013,
`CLAUDE.md` invariante 33 · **Rollback**: `c669e57`
**Test**: 1938 → **1979**, 25 saltati, **0 rossi** · Densità rimisurata, conforme

---

## Il criterio, punto per punto

| # | criterio | esito |
|---|---|---|
| 1 | un intent valido produce un `Layout` che li mostra, e la scrivania ci arriva | ✅ **dal vivo**, con Electron e core veri |
| 2 | un nome inesistente non muove un pixel e produce un advisory | ✅ |
| 3 | un pannello mosso a mano resta dov'era | ✅ |
| 4 | il `Layout` porta `superficie` e `traccia_id`, e il diario ha la riga | ✅ una riga sola |
| 5 | l'utente può tornare alla composizione precedente | ✅ `ripristina()` |
| 6 | ciclo §11.7 eseguito, checklist §11.8 riportata | ✅ vedi §④ |
| 7 | `uv run pytest -q` verde | ✅ 1979 passati |

---

## ① Due correzioni ad ADR-013, misurate prima di scrivere

**Il «registry dei pannelli» non esiste nel core.** L'elenco dei diciannove
pannelli sta in `ui/src/desk/moduli.js`, e `core/settings.py:276` prende la
decisione **opposta**, per iscritto:

> *«`id` non viene validato contro i moduli esistenti. Il core non conosce
> `moduli.js` e non deve: è interfaccia. Un id sconosciuto lo IGNORA il
> renderer — un ambiente che non parte perché una scena nomina una finestra che
> non c'è più sarebbe rotto dal proprio passato.»*

L'allowlist è quindi **i pannelli dichiarati nelle scene di `settings.toml`**:
una lista chiusa che il core possiede davvero, senza duplicare niente.
⚠️ Il prezzo, dichiarato: un pannello che esiste in `moduli.js` ma non compare
in nessuna scena non è componibile.

**`componi` non restituisce un `Layout`.** La regola 4 vuole che un rifiuto
porti con sé il motivo, e un `Layout` da solo non può. Restituirne uno vuoto
sarebbe peggio: chi chiama non distinguerebbe «composto a vuoto» da
«rifiutato». Torna una `Composizione`, e `layout is None` significa
*non si muove nulla*.

---

## ② Quattro difetti che solo il confine ha mostrato

§11.7 passo 0 regola 2: *«ciò che attraversa un confine si prova attraversando
quel confine. Il layout tocca renderer, preload, ponte, socket, core e disco.»*
Questa fetta è la dimostrazione di perché quella regola esiste: **41 test Python
erano verdi e sullo schermo non cambiava niente.**

**① `ui/src/app.js` applicava `ui.layout` una volta sola.** `if (ripristinato)
return` — il guardiano del ripristino d'avvio scartava in silenzio la
composizione che arrivava dopo. Il core la mandava, il disco la aveva, lo
schermo no. Distinto adesso con `layout.superficie`, che un layout manuale non
ha.

**② `nascondiTutto()` non riferiva niente al core.** Cambiava `v.nascosto` e
chiamava `annuncia()`, che parla alla scrivania. Il file del layout restava con
tutti visibili, e la composizione veniva rifiutata «per mancanza di spazio»
contro pannelli che nessuno vedeva.

**③ Lo stesso elenco di campi è copiato a mano in TRE punti.**
`ui/src/desk/scrivania.js` lo produce, `app/preload.js` lo ricopia,
`app/main.js` lo ricopia ancora. Ho aggiunto `nascosto` ai primi due e l'ho
dimenticato nel terzo: il renderer mandava sei `true`, il core riceveva sei
`false`. **Nessun test lo vedeva**, perché ognuna delle tre copie era corretta
da sola. È una fragilità che resta.

**④ `ripristina()` riapriva i pannelli nascosti.** Dopo la composizione i sei
di prima tornavano visibili sopra i tre nuovi — cinque sovrapposizioni misurate.
Adesso il ripristino rispetta `nascosto`.

---

## ③ Il giro vero, misurato

Due frasi, dette una dopo l'altra, che una persona direbbe davvero:

```
«nascondi tutto»  →  «componi la superficie diagnostica»
```

```
[prova] 'componi la superficie diagnostica' -> {'ok': True, ...}

visibili : ['telemetria', 'agenti', 'anelli']
   telemetria   x=    0 y=  32 550x388
   agenti       x=  512 y=  32 512x388
   anelli       x= 1024 y=  32 384x388
fuori area: nessuno
```

`scripts/prova_superficie.py` + `scripts/prova-superficie.mjs`, con Electron e
core veri. La composizione attraversa grammatica → `esegui_t0` → compilatore →
disco → socket → renderer.

⚠️ **Il lanciatore esiste perché non c'è un canale di testo.** La composizione
la chiede una frase, e dal di fuori del processo non c'è modo di mandarne una:
`ws_server` accetta cinque messaggi e nessuno è un testo — l'assenza è una
decisione presa (ADR-011). Il lanciatore fa dall'interno ciò che farebbe la
voce, ed è l'analogo di ciò che `prova-scena.mjs` fa dall'altra parte del
confine.

---

## ④ Checklist §11.8, punto per punto

Guardata sullo scatto `superficie.png`, non dedotta dal codice.

```
GEOMETRIA
✓ border-radius 0 ovunque            i tre pannelli sono rettangoli netti
✓ taglio a 45° su 1–2 vertici        invariato: la cornice è quella di §26.2,
                                     `componi` non disegna, colloca
✓ spaziature multiple di 4           x = 0 / 512 / 1024, y = 32, h = 388
✓ pesi di linea hair/base/bold       invariati

COLORE
✓ tutti da tokens.css                nessun colore introdotto: zero CSS scritto
✓ accento caldo < 10%                invariato
✓ tinte ≤ 3                          invariato
✓ zero gradienti fuori ricetta       invariato
✓ ZERO alone / bloom / glow          invariato
✓ ombre nere e solo dove coprono     invariato

TIPOGRAFIA
✓ sei gradini · mono per i numeri · caps con letter-spacing · nulla sotto 8.5px
                                     invariati: nessun testo nuovo

CONTENUTO
✓ dati VERI                          cpu 3.1 %, ram 33.9 %, temp 43.6 °C dal
                                     core vero; mesh a 8 nodi reali
✓ etichetta + ID/versione + piede     A01·ver 1, MSH_D04·ver 1, RNG_A01·ver 1
✓ almeno un valore mono              tutti
✗ la densità regge il confronto      **vedi il difetto qui sotto**

MOVIMENTO
✓ ogni animazione ha un evento       l'apertura di §10.3, causata dalla frase
✓ zero animazione ambientale         densità rimisurata: 0 pixel su 1.294.848
                                     cambiano in 250 ms
✓ solo anime.js                      invariato

TECNOLOGIA
✓ testo nel DOM · Line2 · uPlot      invariati
```

**Il ✗, per esteso.** `telemetria` è larga **550 px** dove la griglia le
assegnava **512**: il modulo ha una larghezza minima maggiore della cella, e
WinBox lo allarga. `agenti` comincia a 512 e ne copre 38 — sullo scatto si vede
il valore «LIBERA 14.9» tagliato e le barre dei processi troncate.

Il core **non può evitarlo**: le larghezze minime dei moduli stanno in
`moduli.js`, cioè dall'altra parte dello stesso confine che ha già impedito di
avere un registry dei pannelli. Dichiarato come residuo, non aggiustato con un
numero scelto a occhio.

---

## ⑤ Che cosa NON è verificato — per nome

1. **La sovrapposizione di 38 px** fra un pannello composto e il suo vicino,
   quando la larghezza minima del modulo supera la cella. Misurata, non risolta:
   servirebbe che il core conoscesse i minimi dei moduli.
2. **Comporre sopra una composizione quasi sempre rifiuta.**
   `GeometriaPannello` non porta una provenienza *per pannello*, quindi
   `componi` non distingue un pannello che l'utente ha mosso da uno che una
   composizione precedente ha messo lì. Nel dubbio non si tocca. Si torna
   indietro con `ripristina()` e si compone l'altra superficie.
3. **`ripristina()` vale una volta sola.** Uno slot, non una storia: il file
   precedente resta dov'è, quindi ripristinare due volte di fila non torna
   indietro di due passi.
4. **`nascosto` finisce sul disco e non sopravvive al riavvio nel modo giusto**:
   `ripristina()` lo riapplica, quindi un pannello nascosto alla chiusura resta
   nascosto al riavvio. §26.10 chiamava `Alt+H` uno stato *transitorio*; adesso
   è ricordato. È un cambiamento di comportamento, dichiarato qui e non deciso
   di nascosto.
5. **Il `settings.toml` di questa macchina non dichiara nessuna scena**, quindi
   in produzione l'allowlist sarebbe **vuota** e ogni composizione verrebbe
   rifiutata. `componi` lo dice con un messaggio che manda dalla parte giusta —
   «nessuna scena dichiarata in settings.toml» — invece di «pannelli
   sconosciuti». La prova gira sulla configurazione **spedita col progetto**,
   che le scene le ha.
6. **Nessun LLM genera intent**, ed è ADR-013 che lo vuole: le tre superfici
   sono scritte a mano. Chi li genererà, e con quale grammatica, sarà un ADR
   suo — «e oggi non si può scrivere onestamente».

---

## ⑥ I nove sabotaggi

| sabotaggio | rosso |
|---|---|
| `componi` non tiene i pannelli manuali | `test_un_pannello_mosso_a_mano_resta_dov_era` |
| niente allowlist | 3 test della regola 2 |
| `LayoutIntent` accetta geometria | 5 test della regola 3 |
| un rifiuto torna un `Layout` vuoto | 6 test |
| niente `superficie`/`traccia_id` | 4 test, fra cui il giro intero |
| `componi_e_salva` non mette da parte | `test_la_composizione_precedente_si_rimette` |
| una seconda riga di diario | `test_e_il_diario_ha_la_riga_con_la_STESSA_traccia` |
| la grammatica perde l'ancora «superficie» | 8 test, fra cui i falsi positivi |
| l'allowlist vuota resta muta | `test_il_motivo_manda_dalla_parte_GIUSTA` |
