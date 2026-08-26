# Fuori dall'ambiente di JARVIS non si ascolta

**Data**: 26 agosto 2026 · **Riferimento**: `docs/SPEC.md` §18.3 (rev 5.31), §7.1
**Rollback**: `3e6367c` · **Test**: 1441 → **1457**

---

## La richiesta, e la riga di specifica che contraddiceva

> *«la wake e la comunicazione avviene anche fuori dalla schermata dell'app,
> deve funzionare solo quando si avvia l'app di JARVIS OS. Poi se l'app è
> avviata va bene anche se nascosta.»*

§18.3 diceva testualmente **«Il microfono è sempre attivo per il wake»**, ed era
vero: il core gira sotto systemd ventiquattro ore su ventiquattro, l'app no.

Non è uno dei trenta invarianti di `CLAUDE.md`, ed è una richiesta esplicita:
la riga è stata **emendata**, dichiarandolo. Il perimetro che ne risulta è più
**stretto** di prima, mai più largo.

---

## Il disegno, e le tre decisioni che lo reggono

**① Il segnale è la connessione, non la visibilità.** Una scrivania ridotta a
icona resta collegata al socket e JARVIS resta in ascolto — è ciò che serve a
un assistente a cui si parla senza guardarlo, ed è esattamente ciò che è stato
chiesto.

**② Conta solo chi si DICHIARA scrivania.** Il messaggio nuovo ha `ruolo` come
`Literal`, non come stringa: `ws_probe.py` si collega per diagnosi e **non
accende niente**. Se bastasse una connessione qualunque, qualunque cosa sapesse
aprire il socket potrebbe far ascoltare JARVIS — cioè una denylist travestita,
contro l'invariante 2.

**③ Il flusso si chiude DAVVERO.** Scartare i blocchi lasciando `pw-record`
vivo terrebbe accesa **la spia del microfono del sistema operativo**, e quella
spia è l'unica cosa che il Signore vede senza chiedere. Un microfono che non
ascolta ma tiene la spia accesa mente a chi la guarda.

E due dettagli che non sono dettagli:

- **Il valore iniziale non è un valore comodo.** La pipeline nasce con
  `ascolto_consentito = (scrivanie > 0)`: il core parte prima dell'app, e con
  un `True` di comodo il microfono si aprirebbe per un istante a ogni avvio.
- **`stop()` sveglia chi aspetta.** Senza, fermare una pipeline a microfono
  chiuso resterebbe appeso su `wait()` per sempre e la chiusura del core
  andrebbe in timeout.

Nello snapshot: **`sospeso: nessuna scrivania`**, e la riga sta **prima** del
battito del microfono. Un microfono chiuso apposta non è un microfono muto, e
chiamarlo «muto da 40 s» sarebbe un allarme per una cosa voluta — lo stesso
motivo per cui il battito non conta durante un turno.

---

## Il contratto del canale in salita si è opposto, e aveva ragione a fermarsi

`test_ws_contract.py` sorveglia una proprietà:

> ogni messaggio in salita è **o** una risposta con l'`id` di una domanda già
> posta, **o** una dichiarazione di stato che non nomina nessuna operazione.

`client.ruolo` è il secondo ramo, come `ui.layout`: dichiara «sono una
scrivania» e non nomina nessuna operazione. Che cosa farne — aprire il
microfono — è una **politica del core**, non una richiesta del client. La
proprietà non è stata indebolita: l'insieme è cresciuto di un membro che la
soddisfa.

---

## Verifica

### ✅ Le sette bocciature

| perturbazione | esito |
|---|---|
| il cancello non sospende più | **blocco** (uscita 143) |
| il flusso non si chiude alla revoca | 1 rosso |
| `stop()` non sveglia chi aspetta | 3 rossi |
| `ruolo` diventa una stringa qualunque | 2 rossi |
| nessuno conta le scrivanie | 1 rosso |
| la pipeline nasce sempre aperta | 1 rosso |
| la scrivania non si dichiara più | 2 rossi |

⚠️ La prima è **rossa per blocco, non per asserzione**: senza la sospensione
`run()` diventa un ciclo che riapre il flusso e affama il test. È un rosso, e
lo dico come è.

### ⚠️ Due difetti dei miei test, trovati dalle bocciature

**`len(aperture) == 1` non provava niente.** Prova che il flusso non si è
*riaperto*, non che si sia *chiuso* — e «`pw-record` termina» era proprio la
proprietà che avevo dichiarato. Adesso il finto conta le **chiusure**.

**E i test si appendevano invece di fallire.** Un'asserzione fallita lasciava
dietro un compito con un generatore infinito: la suite non falliva, si
bloccava. Adesso un contesto le spegne sempre, e verifica che `run()` esca.

### ✅ La suite

`1441 → 1457`, verde.

⚠️ **Un giro rosso non riprodotto.** Il primo giro completo ha dato 6 rossi in
`tests/test_layout.py::TestGestiVeri`. Il file passa da solo (84 verdi) e il
giro successivo è passato intero (1457). L'ordine dei test è casuale e in quel
momento avevo appena riavviato PipeWire e il core sotto ai test del browser.
Lo dichiaro come **interferenza osservata e non riprodotta**, non come «a
posto».

### ✅ Provato in produzione — e la prova è del sistema operativo

Core riavviato **senza** app:

```
00:23:33  ascolto_sospeso   perche='nessuna scrivania collegata'
          pgrep pw-record -> NESSUNO
          snapshot: "microfono": "sospeso: nessuna scrivania",  "clients": 1
```

Quel `clients: 1` è la sonda di diagnosi, collegata al socket, e il microfono è
rimasto chiuso: **la decisione ② provata dove conta**, non in un test.

Poi l'app:

```
00:23:48  scrivania_dichiarata          totale=1
00:23:48  ascolto_consentito
00:23:48  microfono_segue_la_scrivania  ascolta=True scrivanie=1
00:23:48  cattura_avviata               pid=887007
```

Che `pw-record` **non esista** è una proprietà osservabile dal sistema
operativo, non una promessa del codice: è la forma più forte in cui questa cosa
si possa dimostrare.

### ❌ NON verificato

- **La terza gamba: chiudere la finestra.** Che alla chiusura `pw-record`
  termini è provato nei test (`chiusure == 1`) ma non ancora osservato dal vivo
  — chiuderla adesso interromperebbe chi sta parlando con JARVIS. Resta da
  guardare la prima volta che la finestra si chiude.
