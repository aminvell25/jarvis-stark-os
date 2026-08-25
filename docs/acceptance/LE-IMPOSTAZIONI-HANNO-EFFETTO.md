# Due impostazioni che non facevano niente

**Rollback:** `4fb16fd`
**Che cosa chiude:** la metà mancante del criterio 7 di §26.9 — «l'effetto si
vede **senza riavviare**» — e il punto «cambiare una frase richiede un riavvio
del core» di `LE-FRASI-PUNTANO-A-UNA-SCENA-CHE-ESISTE.md`.
**Esito: entrambe collegate e misurate dal vivo, sul core avviato da systemd.**

---

## 1. Due proprietari, e il secondo era morto

`ui.grid_px` esisteva nello schema **dalla Fase 0** e non lo leggeva nessuno,
mentre `tokens.css` dichiarava `--grid: 110px`. Coincidevano — entrambi 110 —
e per questo nessuno se n'era accorto: al primo cambio si sarebbero separati
in silenzio. La pagina impostazioni avrebbe scritto 128 nel file, il core lo
avrebbe riletto a caldo, e sullo schermo non sarebbe cambiato niente.

`PhraseWake.set_frasi()` esisteva **dalla Fase 3** e non aveva un solo
chiamante. La ricarica a caldo di `settings.toml` funzionava e al wake non
arrivava: cambiare una frase voleva dire riavviare.

È la stessa specie, per la sesta e settima volta in due giorni.

## 2. La scala: `tokens.css` resta il predefinito

`app.js` sovrascrive `--grid` e `--gap` su `:root` da `state.snapshot`. Non si
riscrive `tokens.css`, che è legato a §10.1 byte a byte — una custom property
esiste esattamente per essere sovrascritta.

⚠️ **Non tocca la geometria dei pannelli**: `scrivania.js` calcola le celle da
`area.larghezza / COLONNE`, non da `--grid`. Quel token è la scala della
**cornice** — tessere del catalogo, minimi di `cornice.js` — ed è quella che
§26.7 chiama «la dimensione delle icone».

⚠️ E un valore non valido lascia il predefinito: `NaNpx` su `--grid`
spegnerebbe mezza interfaccia senza un errore da leggere. Assente non è zero.

### Il test ha trovato un difetto nel mio stesso codice

`test_il_valore_arriva_NELLO_SNAPSHOT` è diventato rosso subito: `gap_px`
**non era nello snapshot**. Avevo collegato il renderer a un valore che il core
non mandava — una metà collegata e l'altra no, di nuovo, dentro la correzione
che serviva a togliere quel difetto.

## 3. Le frasi: si rimbalza sul loop

`SettingsStore.reload()` gira sul **thread di watchdog**, e `set_frasi()`
ricostruisce il `KaldiRecognizer` che `feed()` sta usando: chiamarlo di là
sarebbe una corsa su `self._rec` — il riconoscitore sostituito a metà di un
blocco, senza che niente sollevi. `call_soon_threadsafe` lo fa eseguire fra due
giri del loop, mai dentro uno.

Un `settings.toml` con una frase storta non spegne il microfono: si registra e
ciò che c'era continua a valere. E lo spegnimento **si disiscrive**, o un
cambio in arrivo troverebbe un riconoscitore che non c'è più.

## 4. La misura, sul core di systemd

```
grid_px    110 → 132 → 110      settings_ricaricate, snapshot aggiornato
frase      buonanotte → buonasera
           settings_ricaricate
           wake_frasi_ricaricate    frasi=[…, 'jarvis buonasera', …]
           frasi_ricaricate_a_caldo frasi=[…, 'jarvis buonasera', …]
```

Nessun riavvio. Il file è stato ripristinato e verificato identico al backup.

⚠️ **Ciò che NON è misurato**: i pixel. Che il renderer applichi il token è
provato dai test sul sorgente e dal valore che arriva nello snapshot; che la
tessera del catalogo diventi più grande lo vede solo chi ha la scrivania
aperta.

## 5. Tre volte ho misurato la cosa sbagliata, e lo scrivo

Inseguendo un fantasma su questa stessa funzione:

1. **`pgrep` ha contato il mio stesso comando** — la riga di bash contiene la
   stringa cercata. Terza volta oggi.
2. **Ho letto `MainPID`** e ho concluso «zero descrittori inotify, il watcher
   non gira». `MainPID` è il wrapper `uv run`; il Python è suo figlio, e ha la
   sua watch sulla directory giusta.
3. **Il primo `sed` sulla frase non ha trovato la riga**, e per qualche minuto
   ho creduto che la funzione fosse rotta mentre era il mio impianto di prova a
   non fare niente.

Nessuna delle tre era una proprietà del sistema. Tutte e tre mi hanno fatto
scrivere una diagnosi sbagliata prima di rifare la misura.

## 6. E otto rossi che non erano rossi

Dopo il riavvio della macchina la suite dava **8 falliti e 20 errori**. Non era
una regressione: `/tmp` viene svuotato al riavvio, e tutta la sessione stava
passando `TMPDIR=/tmp/jt` — una directory che non esisteva più. Ricreata:
**1080 passed**.

Riproducibile due volte prima di capirlo, il che è il motivo per cui l'ho
riprodotto invece di rieseguire e sperare.

## 7. Verifica

| | |
|---|---|
| `uv run pytest -q` | **1080 passed** (erano 1072), zero rossi |
| `tests/test_grado_voce.py` | 22, di cui **4 nuove** sulle frasi a caldo |
| `tests/test_scrivania.py` | 24, di cui **4 nuove** sulla scala |
| dal vivo, sotto systemd | `grid_px` e una frase, senza riavvio |
| densità | rimisurata, `DENSITA' CONFORME` |

**Ritirato:**

| ritirato | esito |
|---|---|
| l'iscrizione a `state.snapshot` in `app.js` | 1 rosso |
| `gap_px` dallo snapshot del core | 1 rosso |
| `call_soon_threadsafe` dal listener | 1 rosso |

## 8. Dichiarato aperto

1. **I pixel non sono misurati** (§4). Serve la scrivania aperta.
2. **`mute` resta senza destinazione**, e le scene `welcome_home` e
   `goodnight` restano da progettare.
3. **Il `Watcher` delle news non ha ancora un driver**, e con lui restano
   aperti il punto 3 dei NON VERIFICATI di Fase 9 (la menzione vocale) e
   `giri_fatti: 0` nello snapshot.
4. **Restano di Fase 9**: la scadenza vera del token (2), `enable --now` a un
   login vero (4), `seccomp` (5), le direttive sotto carico (6).
