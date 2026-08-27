# I protocolli dichiarati — JARVIS non improvvisa

**Data**: 27 agosto 2026 · **Riferimento**: `docs/SPEC.md` §5.5, §7.6
**Rollback**: `67e2d0f` · **Test**: 1648 → **1676**

---

## Da dove viene la forma

Il Signore ha chiesto un JARVIS che **agisca**, e che non sia pericoloso. La
risposta non è un compromesso: è come lo fa il film.

Nei due film JARVIS non improvvisa **mai** un'azione che tocchi il mondo. Le due
volte in cui lo fa — *House Party Protocol*, *Clean Slate Protocol* — esegue un
comando che Tony aveva scritto **mesi prima** e che richiama per nome. Fuori da
un protocollo, riferisce e chiede.

È la stessa forma dell'allowlist che questo progetto usa dappertutto: un
protocollo non è una libertà, è una **dichiarazione**. Chi la scrive è l'utente,
in `settings.toml`, versionato e correggibile con un editor.

E che cosa fa un protocollo è la forma della **tossicità del sangue di Iron Man
2**: JARVIS sorveglia una cosa e parla quando si muove, non a ogni giro.

---

## ⚠️ Il difetto che ha cambiato il disegno a metà

Il primo disegno filtrava i tool su `side_effect`. È sbagliato, ed è misurato:

> `open_web` — `side_effect=False`, e la sua stessa descrizione dice
> *«Apre una pagina https in un pannello browser»*.
> `youtube_search` — `side_effect=False`, e *«lo fa partire»*.

In questo progetto `side_effect=True` significa **«c'è un percorso risolto da
mostrare a chi conferma»** (invariante 3, §6.2) — cioè «tocca il disco» — non
«cambia qualcosa».

Un'allowlist costruita su quel campo avrebbe lasciato JARVIS **aprire pagine e
far partire video di propria iniziativa**, al risveglio, senza che nessuno
chiedesse. Quindi `TOOL_OSSERVATIVI` è esplicita, e un test la confronta col
registro composto — non col sorgente, perché `core/tools/files.py` registra con
un aiutante locale e un grep del nome non lo troverebbe.

Restano fuori anche `mute`, `unmute`, `set_volume` (cambiano la voce) e
`read_screen` (fa una cattura vera, §12, e costa).

---

## Le decisioni

**Il primo giro non parla.** Non è un cambiamento, è un primo valore. Dirlo
vorrebbe dire che ogni protocollo nuovo parla una volta per niente, e la prima
cosa che JARVIS dice di sua iniziativa sarebbe rumore.

**L'impronta è canonica** (`sort_keys`, separatori fissi): senza, due giri
identici darebbero impronte diverse a seconda dell'ordine di un dizionario, e
ogni giro sembrerebbe un cambiamento. Un sorvegliante che grida sempre è un
sorvegliante che si spegne.

**La memoria è su disco.** Il core si è riavviato 27 volte in tre giorni: una
ronda che dimentica a ogni riavvio grida al primo giro dopo.

**Un'iniziativa solo quando c'è qualcosa da dire.** Una ronda che non trova
niente non è un evento: registrarla riempirebbe `initiatives/` di righe che
nessuno legge, e il resoconto direbbe ogni giorno che JARVIS ha guardato senza
dire mai che cosa. Il silenzio lo copre già «niente da riferire», una volta al
giorno.

**La frase la scrive l'utente.** JARVIS non compone una spiegazione di una cosa
che non ha deciso lui di sorvegliare: dice quella che gli è stata data.

**Il rifiuto è rumoroso.** Una dichiarazione storta che sparisse in silenzio è la
peggiore delle uscite possibili: JARVIS non sorveglia, e nessuno lo sa.

**E il predefinito è vuoto.** Quali cose JARVIS sorvegli è una decisione
dell'utente; un valore predefinito nel modello sarebbe JARVIS che decide per lui,
cioè l'opposto del modello che questa sezione imita.

---

## Verifica

### ✅ Fine a fine, col tool vero

`Ronda` contro `registry.invoke` e il `list_dir` registrato davvero, su una
cartella vera:

```
primo giro   : eseguito=True  cambiato=False  frase=''
secondo giro : eseguito=True  cambiato=False  frase=''
compare un file:
dopo un file : eseguito=True  cambiato=True   frase="e' cambiato qualcosa …"
e poi        : eseguito=True  cambiato=False  frase=''
```

E il percorso d'errore si è provato da sé: sbagliando il banco — una lista al
posto di una funzione — il tool ha sollevato, la ronda ha risposto
`eseguito=False, cambiato=False` con l'errore riferito, e non ha chiamato quel
`TypeError` un cambiamento.

### ✅ Le sei bocciature

| perturbazione | esito |
|---|---|
| `open_web` entra nell'allowlist | 4 rossi |
| il primo giro conta come cambiamento | 1 rosso |
| l'impronta non è canonica | 1 rosso |
| registra un'iniziativa anche senza cambiamento | 1 rosso |
| la ronda non gira al risveglio | 1 rosso |
| una sola strada di notte (recupero **o** 04:00) | 1 rosso |

### ✅ La suite

`1648 → 1676`, verde.

### ❌ NON verificato

- **Nessun protocollo gira in produzione.** I due dichiarati stanno in
  `config/settings.toml`, che è l'esempio del repository; il file vivo è
  `~/.config/jarvis-os/settings.toml` e non li ha. **È una decisione del
  Signore**, non una dimenticanza: il meccanismo è pronto e cosa JARVIS debba
  sorvegliare lo dice lui.
- **`ask_state` non è provato**: si registra solo col grado ARGUS acceso, e la
  validazione lo rifiuta a grado spento — che è il comportamento voluto, ma il
  ramo con ARGUS vivo non è mai stato percorso.
