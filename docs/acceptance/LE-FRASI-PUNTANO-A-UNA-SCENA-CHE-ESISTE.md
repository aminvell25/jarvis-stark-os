# Le frasi puntano su `avvio` — e adesso c'è chi controlla che la scena esista

**Rollback:** `423e13d`
**Richiesta:** «Punta le frasi su avvio».
**Esito: fatto, nei due file. E c'è una guardia nuova che boccia se una frase
nomina una scena non dichiarata — la stessa specie di silenzio si è già presa
due turni.**

---

## 1. La modifica

`config/settings.toml` (il modello nel repo) e
`~/.config/jarvis-os/settings.toml` (quello vivo), tenuti allineati:

```diff
 say = "papa e a casa"
-action = "scene:welcome_home"
+action = "scene:avvio"          # la sola scena DICHIARATA in moduli.js

 say = "jarvis buonanotte"
-action = "scene:goodnight"
+action = "scene:avvio"          # idem: una scena che non esiste non fa niente
```

Le due frasi fanno adesso la stessa cosa. È il prezzo dichiarato della scelta
1 di `LA-VOCE-PARLAVA-A-NESSUNO.md`: si vede subito qualcosa, e le due scene
restano da progettare quando le vorrà.

Verificato sul core riavviato:

```
frase 'jarvis'               azione 'listen'
frase 'papa e a casa'        azione 'scene:avvio'
frase 'jarvis buonanotte'    azione 'scene:avvio'
frase 'jarvis silenzio'      azione 'mute'
```

## 2. La guardia, che è la parte che dura

`tests/test_voce_arriva_alla_scrivania.py::TestOgniScenaNominataESISTE` legge i
due lati del contratto e li confronta:

* le azioni `scene:<nome>` in `config/settings.toml`;
* i nomi in `export const SCENE = [...]` di `ui/src/desk/moduli.js`.

Se una frase nomina una scena che non esiste, il test dice quali sono le due
liste e che cosa manca. Nessuno dei due lati era in torto quando il silenzio è
successo: il torto era che **non si parlavano**, e non c'era niente a
guardarli insieme.

⚠️ **L'ha già presa una volta, per caso e per davvero.** Durante questo stesso
turno un `git checkout` ha riportato indietro `config/settings.toml` alla
versione committata — che nominava ancora `welcome_home` — e la guardia è
diventata rossa nel giro della suite successiva. Non è una prova costruita:
è successo.

## 3. Un test che fissava un valore invece di una proprietà

`test_legge_le_frasi_wake` asseriva

```python
assert frasi["papa e a casa"] == "scene:welcome_home"
```

ed è diventato rosso per una **modifica legittima della configurazione**, non
per una regressione. Un test che fissa il contenuto di `settings.toml` è un
test che rende rosso il cambiare idea — lo stesso difetto della riga 113 di
`lettura.js`, fissata per numero e rotta da un import.

Adesso fissa la forma: le quattro frasi ci sono, `jarvis` è `listen`, l'azione
di «papà è a casa» è **una** scena, e nessuna azione è vuota. Che la scena
esista lo sorveglia §2, che è il posto giusto — lì c'è l'altro lato.

Provato che boccia ancora: rinominata una frase nel modello, **rosso**.

## 4. Verifica

| | |
|---|---|
| `uv run pytest -q` | **741 passed** (erano 740) |
| core riavviato | pid 212984, quattro frasi caricate, azioni corrette |
| sorgenti UI toccate | **nessuna** |

## 5. Dichiarato aperto

1. **Non ho verificato dal vivo che la scena si applichi sullo schermo.**
   Servono insieme la scrivania aperta (`npm run app`) e una frase detta da
   Lei. Provata la forma del messaggio e l'esistenza della scena; il tragitto
   fino al pixel no.
2. **`PhraseWake.set_frasi()` non ha nessun chiamante**, quindi cambiare una
   frase richiede un **riavvio del core**: la ricarica a caldo di
   `settings.toml` funziona e non arriva al wake. È la quarta volta oggi che
   compare questa specie di difetto — scritto, provato, mai congiunto.
   **Non l'ho collegato**, e la ragione è concreta: `set_frasi` ricostruisce
   il `KaldiRecognizer` mentre `feed()` gira nel ciclo, e chiamarlo dal thread
   che sorveglia il file sarebbe una corsa su `self._rec`. Va fatto
   marshallando sul loop, ed è un lavoro con una domanda di concorrenza
   dentro, non due righe.
3. **`mute` resta senza destinazione**, come da `LA-VOCE-PARLAVA-A-NESSUNO.md`.
4. **Le due scene `welcome_home` e `goodnight` restano da progettare**, se le
   vorrà: è la scelta 2 che aveva davanti.
