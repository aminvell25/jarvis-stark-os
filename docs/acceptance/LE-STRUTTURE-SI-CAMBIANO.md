# Le strutture dalla pagina — §26.7, il residuo chiuso

**Data**: 30 agosto 2026 · **Riferimento**: `docs/SPEC.md` §26.7,
`PIANO-JARVIS-COGNITIVO` fetta 6 · **Rollback**: `312bdad`
**Test**: 1979 → **2020**, 25 saltati, **0 rossi** · Densità rimisurata, conforme

---

## Il criterio

> «Aggiungere una frase di wake dalla pagina la fa riconoscere **a caldo**,
> senza riavviare il core, e i commenti del TOML sopravvivono.»

✅ Tutti e tre. Il ricarico a caldo esisteva già — `SettingsStore.subscribe` →
`Engine._ricarica_frasi` → `PhraseWake.set_frasi`, chiuso il 25 agosto — e
mancava la **strada di scrittura**. Adesso c'è, e i 105 commenti di
`config/settings.toml` sopravvivono a tre scritture di fila.

---

## ① La decisione: `fs.allowed_roots` esce dalle bloccate

Il piano diceva che va deciso **prima**. Deciso: **esce**, con la condizione che
il piano stesso poneva — *«la conferma deve mostrarle risolte e una per una»*.

```
$ pianifica imposta_valore  fs.allowed_roots  aggiungi  {valore: "…/altrove/../cartella-vera"}

  write      → …/config/settings.toml
  perimetro  → /tmp/…/cartella-vera        ← RISOLTO
               «JARVIS potra' leggere e scrivere qui dentro»
```

Chi approva legge la **cartella vera**, non la stringa che ha digitato: `~/../..`
e un symlink si scrivono uguali e arrivano altrove. La riga del perimetro è
un'operazione sua nel piano, non un dettaglio annegato in una stringa — e non
compare per le altre liste, perché una riga che c'è sempre si smette di leggere.

**La difesa che si perde** è «dalla pagina non si può nemmeno chiedere».
**Quella che resta** è l'invariante 3, che è la difesa che il progetto ha scelto
ovunque altro. Le altre cinque bloccate restano: decidono se un sottosistema
*esiste*, o sono un fatto che si può solo guardare.

---

## ② Un elemento per volta, e non è comodità: è il confine

Tre strati vietavano una struttura, tutti con la stessa ragione scritta.
`core/ws_server.py`:

> *«Un dizionario o una lista che arrivassero fin qui verrebbero scritti in
> `settings.toml` da tomlkit **senza passare da nessuno schema di sezione**, e
> sarebbe una strada per riscrivere una struttura — le radici consentite, per
> dire — con un messaggio che dichiara di cambiare uno scalare.»*

**Quella frase resta vera alla lettera**, e due proprietà la tengono:

**Il messaggio non porta mai l'elenco.** `ElementoMessage` porta un verbo e UN
record. Non esiste nessun messaggio con cui il renderer possa sostituire una
struttura — e il canale scalare non è stato allargato: `impostaValore` continua
a non poter portare un array, e un test lo pinna leggendo il sorgente.

**Il record passa da DUE schemi prima del disco.** Prima il tipo dichiarato
dell'elemento (`WakePhrase`), poi `Settings` intero. Niente raggiunge tomlkit
senza controllo.

E il ponte ha un tetto in tutti e tre i punti: 8 campi, 32 caratteri per nome,
512 per valore. I campi sono generici (`Object.entries`), quindi non c'è un
elenco da tenere allineato a mano — è l'unico modo di non ripetere l'errore che
il 30 agosto ha fatto cadere `nascosto` fra renderer e core.

---

## ③ Due sabotaggi non producevano rosso, e hanno scritto due test

Su nove sabotaggi, **due sono passati senza far cadere niente**. È il motivo per
cui si fanno.

**`nuovo = dict(elemento)`** — via la validazione del record. Verde. Un record
incompleto passava di lì e veniva fermato più avanti, dalla validazione di
`Settings` intero: il test dei rifiuti restava verde, e la validazione del
record risultava provata senza esserlo. La differenza che resta è il
**messaggio** — «l'elemento non è un `WakePhrase` valido: action Field
required» dice quale campo manca; l'altra direbbe che una lista in fondo al file
non è valida. Un rifiuto che non dice dove guardare è metà rifiuto. Adesso c'è
un test sul messaggio.

**Via la validazione di `Settings` intero.** Verde: il controllo del record
copriva tutti i casi che avevo scritto. Il caso che solo la validazione del
*file* può prendere: `allowed_roots` ha `min_length=1`, quindi svuotarlo passa
il controllo dell'elemento — che guarda una stringa — e rompe lo schema. Adesso
c'è un test che **non si può togliere l'ultima radice**.

| sabotaggio | rosso |
|---|---|
| `fs.allowed_roots` di nuovo bloccata | 2 test |
| niente riga del perimetro nel piano | 2 test |
| percorso non risolto | `test_il_piano_porta_la_cartella_VERA` |
| record non validato | `test_il_RECORD_e_validato_dal_suo_schema` ⬅ **nuovo** |
| scrive senza validare il file | `test_NON_si_puo_togliere_l_ultima_radice` ⬅ **nuovo** |
| `elemento: dict` permissivo | `test_lo_schema_e_stretto` |
| elenco delle liste scritto a mano | 2 test |
| due forme di argomenti insieme | `test_una_forma_sola_alla_volta` |
| ponte senza tetto sui campi | `test_il_ponte_copia_i_campi_UNO_PER_UNO` |

---

## ④ Un difetto commesso mentre si chiudeva quello che descrive

`ui/src/panels/settings.js` dichiarava il residuo così: *«le STRUTTURE non
compaiono fra le modificabili: `imposta_valore` sa scrivere una foglia, e
fingere il contrario darebbe **un errore a metà scrittura invece di un
rifiuto**»*.

La prima stesura di `chiavi_lista` era un elenco scritto a mano, e ci avevo
messo **`protocolli`**. `ProtocolloSettings.args` è un `dict`, e
`ElementoMessage.elemento` è un `dict[str, str]`: la pagina l'avrebbe offerto e
il ponte l'avrebbe rifiutato a metà. **Esattamente il difetto che questa fetta
chiude, commesso mentre la si chiudeva.**

L'ha trovato un test, non una rilettura. E la cura non è stata togliere quella
riga: il filtro adesso è **derivato** — una lista si offre solo se il suo
elemento è piatto, uno scalare o un record di soli scalari — il che toglie la
classe intera di errore e esclude anche `ui.scene` e `mcp.servers` senza
nominarle.

⚠️ **Il residuo che resta**: tre liste su cinque non sono modificabili dalla
pagina — `ui.scene`, `mcp.servers`, `protocolli` — perché i loro record non
sono piatti. Il criterio ② della rev 1 diceva «*ogni* impostazione», e oggi è
«ogni foglia scalare **e ogni lista piatta**». È lavoro dichiarato, non fatto.

---

## ⑤ Ciclo §11.7, e checklist §11.8

Tre giri di `npm run shot -- settings`, guardando lo scatto ogni volta. Il ciclo
ha trovato **tre** difetti che il codice non mostrava:

1. **La sezione non compariva affatto.** Appendevo a `sezioni` con
   `appendChild`, e il `replaceChildren` in fondo alla funzione la cancellava:
   il piede contava «2 strutture» e a schermo non c'era niente.
2. **I campi si leggevano al contrario.** `Object.keys().sort()` dava
   «action=listen say=jarvis», cioè la conseguenza prima della causa.
   `WakePhrase` dichiara `say` e poi `action`, ed è l'ordine in cui una persona
   la pensa.
3. **«AGGIUNGI» usciva tagliato** dal proprio bordo: «AGGIUNG|I».
   `.pnl-set__tasto` è tarato su etichette corte. La cura non è allargare il
   tasto: è la parola giusta. **«metti» e «togli»** sono la coppia, hanno la
   stessa lunghezza, e la simmetria si legge prima di leggerle.

```
GEOMETRIA
✓ border-radius 0 · taglio a 45° · spaziature multiple di 4 · pesi di linea
                                     invariati: nessuna regola CSS nuova

COLORE
✓ tutti da tokens.css                l'audit dice **0 regole con letterali**
✓ caldo < 10% · tinte ≤ 3 · zero gradienti · ZERO glow · ombre nere
                                     invariati

TIPOGRAFIA
✓ sei gradini · mono per i valori · caps con letter-spacing · nulla sotto 8.5px
                                     le righe nuove riusano le classi esistenti

CONTENUTO
✓ dati VERI                          da `config/settings.toml`, per la stessa
                                     `chiavi_lista()` che alimenta la pagina viva
✓ etichetta + ID + piede             SET_N07 · ver 1 · «35 modificabili ·
                                     2 strutture · 5 nel file»
✓ almeno un valore mono              tutti
✓ densità                            rimisurata: conforme

MOVIMENTO
✓ nessuna animazione aggiunta        zero animazione ambientale, solo anime.js

TECNOLOGIA
✓ testo nel DOM                      invariato
```

⚠️ **Una nota, non un ✗**: la riga di aggiunta di `voice.wake.phrases` va a
capo — due campi più il tasto non stanno in 460 px — e il tasto finisce sulla
riga sotto. Non è tagliato e non esce dal pannello: è un a capo, e in un
pannello largo quanto la sua cella non succede.

---

## ⑥ Che cosa NON è verificato — per nome

1. **Tre liste su cinque restano fuori** — `ui.scene`, `mcp.servers`,
   `protocolli` — perché i loro record non sono piatti. Il residuo §26.7 si
   restringe, non si chiude.
2. **Il giro non è stato provato dal vivo con Electron.** Il ciclo §11.7 è
   passato dalla galleria (che ha lo stesso CSP dell'app, e un test lo impone),
   e il percorso renderer→preload→main→socket→core è verificato **leggendo il
   sorgente** dei tre salti, non attraversandolo. ⚠️ È lo stesso confine su cui
   la fetta 5 ha trovato quattro difetti che i test Python non vedevano.
3. **Il ricarico a caldo è provato con `store.reload()` a mano**, non con
   l'inotify vero: il test non aspetta il watchdog. La giunzione
   scrittura→ascoltatore è misurata; la latenza dell'evento no.
4. **Nessuna prova con la voce.** «Aggiungere una frase dalla pagina» è
   verificato; che la frase nuova svegli JARVIS **detta a un microfono** no —
   e resta il `NON VERIFICATO` che la fetta 1 porta dall'inizio.
