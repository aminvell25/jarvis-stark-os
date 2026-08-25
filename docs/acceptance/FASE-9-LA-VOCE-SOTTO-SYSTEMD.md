# La voce accesa sotto systemd — e una unit vecchia di sei giorni

**Rollback:** `cbfdff1`
**Punto 1 dei NON VERIFICATI di Fase 9:** «La voce accesa da systemd.
`voice.enabled = true` aprirebbe il microfono e spawnerebbe `claude`: l'ho
verificato spento. Il giro completo resta da fare a chi decide di accenderla».
**Esito: CHIUSO. Il giro funziona per intero sotto la unit — e nel farlo ha
trovato che l'irrobustimento che il repository crede attivo, sulla macchina non
lo era tutto.**

---

## 1. Perché adesso e non prima

Fase 9 si è chiusa il 19 agosto con la voce spenta, ed era la scelta giusta: la
catena vocale non era mai stata accesa. Oggi lo è, e le sei correzioni di
stamattina l'hanno resa funzionante fino allo schermo. Restava una domanda
diversa: **funziona anche dentro la unit?**

Non è la stessa domanda. Sotto systemd cambiano il `PATH`, l'assenza di un
terminale, e sette direttive di irrobustimento — fra cui `PrivateTmp=true`,
`ProtectSystem=strict` e `NoNewPrivileges=true`.

## 2. Il sospetto che avevo, e che era sbagliato

`claude` e `uv` stanno in `~/.local/bin`, che una unit di sistema non ha nel
`PATH`. Misurato prima di provare:

```
systemctl --user show-environment | grep PATH
PATH=/home/aminvell/.local/bin:/usr/local/sbin:…
```

Il gestore **utente** eredita il `PATH` della sessione, e `~/.local/bin` c'è.
Il sospetto era ragionevole e falso, e l'ho verificato invece di costruirci
sopra una correzione.

## 3. Il giro, misurato

```
20:51:34  t1_avviato        modello=claude-haiku-4-5  pid=403025
20:51:35  wake_pronto       frasi=['jarvis','jarvis buonanotte','jarvis silenzio','papa e a casa']
20:51:35  grado_acceso      grado=voce  stt=vosk  tts=edge
20:51:35  cattura_avviata   pid=403578  rate=16000
20:51:35  primo_suono_ms    ms=526          <- la prima frase di ripiego ESCE
20:51:45  primo_suono_ms    ms=10219        <- la seconda
```

Quattro cose che potevano rompersi e non si sono rotte:

| | perché poteva rompersi |
|---|---|
| `claude` spawnato | `PATH` della unit |
| modello Vosk caricato | sta in `~/.local/share`, e `ProtectSystem=strict` |
| `pw-record` avviato | `PrivateTmp=true` — il socket di PipeWire vive in `$XDG_RUNTIME_DIR`, non in `/tmp`, e per questo passa |
| entrambi gli annunci **detti** | rete (EdgeTTS) e `pw-play` sotto `NoNewPrivileges` |

Dal socket, a unit avviata: `microfono: "aperto"`, `t1_vivo: true`.

E l'irrobustimento è **applicato**, non solo scritto — letto da systemd, non dal
file:

```
NoNewPrivileges=yes · PrivateTmp=yes · ProtectSystem=strict · ProtectHome=no
ProtectKernelTunables=yes · ProtectControlGroups=yes · RestrictSUIDSGID=yes
LockPersonality=yes · UMask=0077 · Restart=always
```

## 4. Il difetto che il giro ha trovato

Una riga sola era diversa:

```
il repository dice     RestartPreventExitStatus=41 42
systemd applicava      RestartPreventExitStatus=41
```

La copia installata in `~/.config/systemd/user/` era del **19 agosto** —
prima che ADR-003, il 25, introducesse il codice **42**: «riavvii ripetuti», T1
caduto tre volte in dieci minuti.

**La conseguenza è precisa.** Con `Restart=always` e il 42 non protetto,
systemd avrebbe riavviato il core proprio nel caso in cui il supervisore ha
appena stabilito che riavviarlo non aggiusta niente — in cerchio, fino a
`StartLimitBurst=5`. L'esatto contrario di ciò per cui quel numero esiste.

⚠️ **E c'era già un test su quella riga.** `tests/test_supervisor.py:125` legge
`RestartPreventExitStatus` e verifica che contenga `USCITA_RIPETUTI`. È verde,
ed era verde anche stamattina: **legge il file del repository**. Il repository
non è la macchina.

## 5. La correzione, e dove vive

Reinstallata (`packaging/installa.sh`), riavviata, verificato: `41 42`.

Ma la parte che dura è un'altra. Questa differenza **non è una proprietà del
codice** — è uno stato dell'installazione, e un test non la può possedere. Sta
nel `doctor`, che è il posto delle domande sulla macchina:

```
UNIT       FAIL   INSTALLATA VECCHIA: repo c981ea1e, installata 32ebb8c7 —
                  reinstalla con packaging/installa.sh
UNIT       OK     installata e allineata (c981ea1e)
```

Tre stati, e sono tre cose diverse: allineata (`ok`), vecchia (`fail`), non
installata (`warn` — chi non l'ha installata non ha un guasto, ha una scelta
che non ha fatto; il core gira benissimo lanciato a mano).

⚠️ **Vecchia è `fail`, non `warn`**, e c'è un test che lo impone: una unit
vecchia può disattivare in silenzio una difesa che il repository crede attiva.
È appena successo.

## 6. Verifica

| | |
|---|---|
| `uv run pytest -q` | **1072 passed** (erano 1068), zero rossi |
| `tests/test_doctor.py` | 17, di cui **4 nuove** sulla unit |
| unit avviata con la voce | T1 vivo, microfono aperto, due annunci detti |
| `systemctl --user show` | dieci direttive applicate, `41 42` |

**Ritirato:**

| ritirato | esito |
|---|---|
| il controllo dall'elenco del doctor | 1 rosso |
| «vecchia» declassata da `fail` a `warn` | 1 rosso |

## 7. Dichiarato aperto

1. **Nessuno ha ancora parlato al core avviato da systemd.** Il riconoscimento
   è provato oggi fuori dalla unit, e la unit fa girare lo stesso codice sullo
   stesso microfono — ma «stesso codice» è un ragionamento, non una misura.
   Il giro completo lo chiude una frase detta adesso.
2. **`enable --now` non l'ho fatto** (punto 4 dei NON VERIFICATI di Fase 9):
   abilitare l'avvio automatico al login è una decisione Sua, non un passo di
   verifica. La unit è installata e **disabilitata**.
3. **`seccomp` resta non applicato** dalla Fase 1, e il doctor lo dice.
4. **Le altre sei direttive sotto carico** (punto 6) restano verificate
   all'avvio e nei primi secondi, non mentre il core lavora davvero.
5. **La scadenza vera del token** (punto 2) resta simulata.
