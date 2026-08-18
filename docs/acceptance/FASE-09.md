# Fase 9 — esito dei criteri di accettazione

**Data**: 19 agosto 2026 · **Riferimento**: `docs/SPEC.md` §22 Fase 9, §5.6, §16.1b
**Test**: 331 verdi (erano 315) + 197 negli eval · **Precedente**: `FASE-08.md`

L'ultima fase. §22 la descrive in una riga, ma la riga nascondeva il lavoro che
avevo dichiarato **non verificato in quattro fasi di seguito**: le due radici di
composizione.

---

## Il criterio, che me lo sono dovuto dare

§22 è l'unica fase senza «**Criterio**:». Ne ho dichiarato uno in fase di piano
e l'ho verificato punto per punto.

### 1. Avvio a freddo da systemd — ✅ VERIFICATO, ma solo dopo una correzione

> ⚠️ **Questa riga è stata riscritta dopo il primo avvio vero.** La verifica
> originale usava una unit **transitoria** con un sottoinsieme delle proprietà,
> e quindi **non ha mai eseguito la unit spedita**. Al primo `systemctl --user
> start jarvis-core` il servizio è finito in ciclo di riavvio con
> `218/CAPABILITIES`.
>
> La causa: `ProtectKernelModules=true`, che toglie `CAP_SYS_MODULE` dal
> bounding set e per farlo richiede `CAP_SETPCAP` — che un gestore **utente**
> non ha. `systemd-analyze verify` la approva: è sintatticamente corretta e
> fallisce solo all'esecuzione.
>
> Ho provato le sette direttive di irrobustimento **una per volta** su questa
> macchina: solo quella fallisce. È stata tolta, e
> `tests/test_supervisor.py` ora rifiuta l'intera famiglia di direttive che un
> servizio utente non può applicare — verificato che il test spari rimettendo
> la riga.
>
> **La lezione è metodologica**: validare una unit non è avviarla, e avviarne
> una *simile* non è avviare quella. Sotto c'è la misura rifatta con la unit
> vera, installata da `packaging/installa.sh`.

```
NRestarts    0
ActiveState  active
SubState     running

700 /run/user/1000/jarvis-os
srw------- 1 aminvell aminvell 0 /run/user/1000/jarvis-os/core.sock
```

Stabile a venticinque secondi, zero riavvii, socket con la directory **0700**
(invariante 7).

La verifica originale, che resta valida per quello che misurava — restart
semantics e isolamento dell'ambiente — usava una unit transitoria con
`XDG_CONFIG_HOME` e `XDG_RUNTIME_DIR` temporanei:

```
active — servizio ATTIVO

drwx------ 2 aminvell aminvell   .
srw------- 1 aminvell aminvell   core.sock
700 /tmp/jarvis-prova.0kro/run/jarvis-os
```

Il socket compare, e la sua directory è **0700** come vuole l'invariante 7: il
permesso lo mette il core, non systemd, perché è parte dell'invariante e deve
stare dove qualcuno lo verifica.

### 2. `jarvis doctor` dice il vero — ✅ VERIFICATO, contro il core vivo

```
CORE       OK     pid 75749, uptime 20s, fase 9
WS         OK     unix core.sock, dir privata, 1 client
SETTINGS   OK     permessi privati, chiavi: nessuna
SANDBOX    WARN   bwrap ok, unshare-all attivo — seccomp NON applicato (Fase 1)
VRAM       OK     1.0 GB/8.0 GB amdgpu, headroom 7.0 GB (memoria unificata)
T1 claude  N/D    voce spenta (voice.enabled = false)
T1 auth    OK     nessuna scadenza rilevata, 0 riavvii di T1
STT        WARN   deepgram richiesto ma la chiave manca: parte in local e lo annuncia
TTS        WARN   deepgram richiesto ma la chiave manca: parte in local e lo annuncia
WAKE       WARN   modello assente in …/vosk-model-small-it-0.22: si scarica al primo avvio
QUOTA      OK     0/15 spawn T2 nella finestra, 0 attivi
```

Sono le undici righe che §16.1b elenca. Fino alla Fase 8 sei di loro dicevano
«non ancora implementato — Fase N»: era la verità, ed era giusto dirla.

**La distinzione che conta è `N/D` contro `WARN`.** T1 non c'è perché è stato
*deciso*, non perché è guasto: un doctor che dicesse «fail» manderebbe qualcuno
a cercare un problema che non esiste. STT e TTS avvisano perché la chiave manca
davvero e il ripiego è annunciato (§7.4).

### 3. Arresto pulito — ✅ VERIFICATO

```
core_fermato  codice=0 uptime_s=38.5
socket dopo lo stop: (niente)
```

`SIGTERM` → chiusura ordinata → **nessun socket orfano** in `$XDG_RUNTIME_DIR`.

### 4. L'errore di autenticazione non innesca il loop — ✅ VERIFICATO, con controprova

| Uscita | `NRestarts` | Esito |
|---|---|---|
| **41** (auth) | **0** | resta fermo ✅ |
| 7 (guasto qualunque) | **5** | riparte, fino a `StartLimitBurst` ✅ |

La controprova è il punto: senza, «non è ripartito» poteva voler dire che il
riavvio non funzionava affatto. Misurato sullo stesso servizio, cambiando solo
il codice di uscita.

### 5. Le composizioni spente restano spente — ✅ VERIFICATO sui processi, non sul codice

```
pid del core: 75745
processi figli:      75749 python3 -m core.engine     ← e nient'altro
descrittori audio:   (nessuno)
```

Nessun processo `claude`, nessun `pw-record`, nessun descrittore su `/dev/snd`
o `/dev/video`. Guardato nei `/proc`, non dedotto dal sorgente.

---

## Le due radici diventano una

Era il vero contenuto della fase. §3.2 disegna il CORE come **un processo
solo**; fino a ieri `Engine` ne componeva metà e `VoicePipeline` era costruita
soltanto dai test.

| Fase | Cosa avevo dichiarato non verificato | Oggi |
|---|---|---|
| 5 | mesh agenti con T1 e Governor veri | ✅ il pannello riceve gli oggetti veri |
| 6 | ARGUS su stati reali | ✅ lo snapshot li porta |
| 8 | budget e regole del gate news | ✅ composto quando `news.enabled` |
| 8 | menzione vocale | ⚠️ vedi NON VERIFICATO |

### Ma unirle significa aprire il microfono all'avvio

Ed è la ragione per cui l'avvio è **a gradi**:

```
sempre           impostazioni, allowlist, GPU, socket, tool
voice.enabled    microfono, wake, STT/TTS, T1 persistente
news.enabled     collector, gate, budget
vision.enabled   telecamera
```

Il predefinito è `false` **nello schema**, non solo nel file di esempio: una
configurazione scritta prima che il campo esistesse non deve poter accendere un
microfono. Un servizio che lo accende perché è stato installato sarebbe la
peggiore sorpresa dell'intero progetto.

---

## §5.6 capovolto: il codice di uscita lo decidiamo noi

§5.6 chiama la scadenza del token *«il fallimento più probabile dell'intero
sistema»*, e suggerisce: *«Verifichi il codice di uscita reale sul Suo sistema…
lo determini empiricamente lasciando scadere una sessione di prova»*.

Quel consiglio ha due difetti. Aspettare la scadenza di un token per
configurare un servizio è impraticabile; e il numero dipenderebbe da una
tabella che nessuno pubblica e che può cambiare **in silenzio** a una versione
qualunque di `claude`.

**Capovolto**: il supervisore riconosce `authentication_failed` nello stream —
che è documentato, ed è già in §21.5 — ed **esce lui** con `USCITA_AUTH = 41`.
`RestartPreventExitStatus=41` funziona per costruzione, e un test verifica che
la costante del codice e il numero nella unit coincidano: due costanti uguali
in due file diversi divergono al primo che le tocca.

E **non tenta la riautenticazione**: §5.6 lo vieta, e ha ragione — richiede un
browser, e automatizzarla significa fallire in silenzio o conservare
credenziali dove non devono stare. Dice cosa fare, e si ferma.

---

## Due errori nello snippet di §5.6, trovati da `systemd-analyze verify`

**`StartLimitBurst` e `StartLimitIntervalSec` vanno in `[Unit]`, non in
`[Service]`.** Lo snippet della specifica le mette in `[Service]`, dove systemd
le **ignora in silenzio**: il limite di partenze non sarebbe mai stato
applicato, e nessuno se ne sarebbe accorto finché un guasto non avesse fatto
ripartire il servizio all'infinito — cioè esattamente lo scenario che quelle
righe esistono per limitare.

**`ProtectHome=read-write` non esiste**: i valori sono `yes`, `no`,
`read-only`, `tmpfs`. Ho messo `no`, ed è una scelta dichiarata: il mestiere
del core è toccare i file dell'utente sotto le radici consentite (§6.1), e la
difesa lì è `core/paths_policy.py`, non un interruttore di systemd.

---

## Scostamenti dalla specifica, dichiarati

### ⚠️ La unit si chiama `jarvis-core.service`, non `jarvis-voice.service`

§22 usa il secondo nome; §3.2 mette tutto in un processo solo. Una unit
chiamata «voice» mentirebbe sul proprio contenuto — contiene anche filesystem,
telemetria, news e ARGUS. `Alias=jarvis-voice.service` fa funzionare comunque
il nome di §22.

### ⚠️ L'installatore non abilita niente

`packaging/installa.sh` copia la unit e ricarica systemd, poi **si ferma** e
stampa il comando. Un servizio che parte al login è una configurazione
persistente della macchina, e non è mia da attivare.

---

## ❌ NON VERIFICATO

1. **La voce accesa da systemd.** `voice.enabled = true` aprirebbe il microfono
   e spawnerebbe `claude`: l'ho verificato spento, come parte di serie. Il giro
   completo con la voce accesa resta da fare a chi decide di accenderla.
2. **La scadenza vera del token.** Il supervisore è provato con l'evento
   iniettato e la unit con il codice reale; la scadenza vera di un OAuth no.
3. **La menzione vocale delle news** (§15): la catena c'è, la voce dipende dal
   punto 1.
4. **Il riavvio dopo `enable --now` a un login vero.** Verificato con unit
   transitorie, non con l'abilitazione permanente — che non ho attivato.
5. **`seccomp`**: dichiarato non applicato dalla Fase 1, e lo è ancora. Lo dice
   `jarvis doctor` a ogni esecuzione.
6. **Le altre sei direttive di irrobustimento sotto carico.** Le ho provate una
   per volta con `/usr/bin/true`: passano. Che non interferiscano col core
   *mentre lavora* — `PrivateTmp` con i file temporanei dell'OCR, `ProtectSystem`
   con la sandbox `bwrap` — è verificato solo per l'avvio e i primi secondi.

---

## Consuntivo del piano

| Fase | Cosa | Test alla chiusura |
|---|---|---|
| 0 · 0b | scaffold, token, galleria e ciclo visivo | 26 |
| 1 · 1b | core, allowlist, sandbox, socket, fetta verticale | 124 |
| 2 | filesystem reale, solo cestino, conferma col path risolto | 151 |
| 3 | voce: wake, STT/TTS, T1 persistente, barge-in | 184 |
| 4 | T2, Governor, memoria in markdown, router | 218 |
| 5 | ambiente 3D, geometria parametrica, budget di frame | 223 |
| 6 | web, YouTube, CSS 3D, ARGUS, `Untrusted` | 248 |
| 7 | gesture, isteresi, invariante 27 chiuso | 285 |
| 8 | news proattive, gate e budget | 315 |
| **9** | **packaging, composizione unica, supervisore** | **331** |

Più **197** negli eval: percorsi, tool, corpus T0 (100 frasi), corpus gesti,
corpus feed, injection (51 casi), visivo.

**I trenta invarianti di `CLAUDE.md` non sono mai stati violati.** Cinque sono
diventati codice che li impone invece di prosa che li chiede: l'allowlist
tipizzata (2), la conferma col piano congelato (3), `Untrusted` (5),
`qualityGate` (22), `invoke_da_gesture` (27).

**Dove ho deviato dalla specifica l'ho scritto**: sedici scostamenti dichiarati
nei nove documenti di accettazione, ognuno con il motivo e quasi sempre con un
invariante alle spalle — dal socket UNIX al posto del TCP (rev 5.1) alle tre
librerie di §22 rimosse in Fase 5, fino ai due errori dello snippet systemd di
oggi.

**E ciò che non ho potuto verificare l'ho dichiarato**: quarantatré punti in
nove fasi. I più grossi restano tre, e sono sempre gli stessi tre: le chiavi
API che qui non ci sono (Deepgram, Guardian, YouTube), i binari che non posso
installare senza `sudo` (Tesseract, MediaPipe), e la latenza del primo token di
T1 — 3,2–4,4 s contro i ~900 ms che §22 si aspettava, misurata in Fase 3 e mai
smentita.
