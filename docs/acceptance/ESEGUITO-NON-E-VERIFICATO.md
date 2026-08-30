# «Eseguito» non è «verificato» — ADR-012, fetta 2

**Data**: 30 agosto 2026 · **Riferimento**: `docs/DECISIONI-COGNITIVE.md` ADR-012,
`CLAUDE.md` invariante 32 · **Rollback**: `f3f06ed`
**Test**: 1877 → **1901**, 25 saltati, **0 rossi**

---

## Il criterio, punto per punto

| # | criterio | esito |
|---|---|---|
| 1 | un'azione finisce in `NON_VERIFICATO` invece che in un `ok=True` falso, e si vede nel diario con la sua traccia | ✅ |
| 2 | rompendo il verificatore di `create_file` un test diventa **rosso** | ✅ sabotaggio 1 |
| 3 | un verificatore che rilegge attraverso il tool stesso viene rifiutato | ✅ **e non in revisione: nel registro** |
| 4 | `jarvis doctor` riporta quanti tool hanno un verificatore | ✅ `3/25`, distruttivi scoperti `6/9` |
| 5 | `uv run pytest -q` verde | ✅ 1901 passati, 0 rossi |

---

## ① Quattro correzioni ad ADR-012, prima della prima riga di codice

**`Esito` → `Verdetto`.** In `core/` `Esito` è già il nome di **tre** classi
diverse — la ronda dei protocolli, la conferma di §6.2, i collettori di news — e
`scripts/orfani.py` conta gli `ast.Attribute` **per nome**: la sua intestazione
dichiara che 52 nomi pubblici sono già definiti da due o più moduli e che due
volte in un giorno quel punto cieco ha coperto un orfano vero. Un quarto omonimo
avrebbe spostato il rinominare sui chiamanti (`import Esito as EsitoVerifica`)
invece che sulla definizione.

**Sei valori → quattro.** `ANNULLATO` e `DEGRADATO` non li emetteva nessuno:
niente annulla un tool — la conferma è rifiutata o scaduta, e sono entrambe un
blocco — e il ripiego annunciato dell'invariante 12 riguarda la **voce**, che non
è un tool. Stessa regola applicata a `Origine` nella fetta 1: un valore senza
produttore è un test rosso, non un posto tenuto caldo.

| verdetto | chi lo produce |
|---|---|
| `RIUSCITO` / `FALLITO` | `Verifica.confronta`, dal verificatore |
| `BLOCCATO` | `registry._bloccata`, **dal registro** — non dal tool. ⚠️ *Il 31 agosto si è scoperto che non raggiungeva il diario*: vedi sotto |
| `NON_VERIFICATO` | `registry._verifica` quando manca un verificatore |

**La firma del verificatore prende il PIANO.** ADR-012 diceva `(args,
ToolResult)`. Non basta per i tre tool che l'ADR stesso nomina: sono tutti
`side_effect=True`, e i loro percorsi **risolti** vivono nel piano congelato.
Un verificatore che risolvesse di nuovo `a.path` rifarebbe esattamente ciò che
§6.2 esiste per impedire — fra la conferma e l'esecuzione un symlink può essere
cambiato — e guarderebbe un percorso diverso da quello toccato, **con l'aria di
aver verificato**. È il difetto peggiore possibile in un verificatore, e ha il
suo test: `test_create_file_guarda_il_PIANO_e_non_gli_argomenti`.

**I nomi dei tool non esistono.** ADR-012 dice `fs.write` e `fs.trash`; nel
registro sono **`create_file`** e **`trash_path`**. `fs.*` è lo spazio dei
*topic* di §6.2 (`fs.confirm`, `fs.result`), non quello dei tool.

---

## ② Il criterio 3 è passato da «in revisione» a «imposto»

ADR-012 scriveva: *«un verificatore che rilegge attraverso il tool stesso viene
rifiutato in revisione»*. Una regola affidata alla disciplina regge finché
qualcuno ha fretta. Adesso è il registro a non poterla saltare, come per la
conferma: `registry._verifica` **declassa a `NON_VERIFICATO`** un verificatore
la cui `fonte` nomina il proprio tool, e lo scrive nel log.

```
verificatore_si_autocertifica  nome=create_file  fonte='rileggo con create_file'
    conseguenza=declassato a non_verificato: rileggere attraverso lo stesso
                codice non e' una verifica
```

E `Verifica.__post_init__` rifiuta una `fonte` vuota: senza quel campo, «ho
guardato» e «non ho guardato» sarebbero la stessa riga.

Le tre fonti, tutte diverse dal tool che verificano:

| tool | fonte |
|---|---|
| `create_file` | `os.stat` sul percorso risolto del piano |
| `trash_path` | i due `os.path.exists`, sull'origine e sulla copia |
| `imposta_valore` | `settings.toml` riletto dal disco con `tomlkit` |

---

## ③ Gli otto sabotaggi, con l'esito

Ognuno applicato, eseguito, ripristinato.

| sabotaggio | rosso |
|---|---|
| **il verificatore di `create_file` guarda `a.path` invece del piano** — il criterio 2 | `test_create_file_guarda_il_PIANO_e_non_gli_argomenti` |
| senza verificatore si torna `RIUSCITO` | `test_un_tool_senza_verificatore_torna_NON_VERIFICATO`, `test_e_NON_torna_riuscito` |
| un verificatore dichiara sé stesso come fonte | `test_nessuno_dei_tre_nomina_se_stesso_nella_fonte`, `test_create_file_misura_i_BYTE…` |
| la conferma rifiutata non produce `BLOCCATO` | `test_il_Signore_dice_no` |
| un quinto valore in `Verdetto` | `test_i_valori_sono_QUATTRO_e_ognuno_ha_un_produttore` |
| l'atteso di `create_file` torna a contare caratteri | `test_create_file_misura_i_BYTE_non_i_caratteri` |
| la riga di diario della conferma perde il verdetto | `test_la_riga_porta_ok_E_verdetto` |
| `jarvis doctor` dice sempre `ok` | `test_warn_quando_un_tool_DISTRUTTIVO_e_scoperto` |

---

## ④ Due difetti trovati scrivendo i verificatori

### `create_file` riferiva caratteri sotto un nome che diceva byte

```
output del tool  : {'path': '…/x.txt', 'bytes': 52}
os.stat st_size  : 62
```

`return ToolResult(ok=True, output={… "bytes": len(a.content)})` — `len()` su
una `str` conta **caratteri**. «però è così, con àèìòù» sono 52 caratteri e 62
byte. Nessuno leggeva quel campo, quindi il difetto era invisibile: è
esattamente il tipo di referto che ADR-012 dichiara inaffidabile — il tool che
parla di sé.

Corretto (`len(a.content.encode("utf-8"))`), e il verificatore non lo usa
comunque: l'atteso viene dagli **argomenti**, l'osservato dal **filesystem**. Se
dipendesse dal referto, il tool si autocertificherebbe.

### `trash_path` verificava già, e buttava via il risultato

`_trash` cerca dove è finito il file (`find_trashed`) e riferisce
`verificato: bool` — **e poi restituisce `ok=True` comunque**. Un'osservazione
che non ha effetto non è una verifica.

È il **quarto** esempio del pattern che ADR-012 elenca (ne elencava tre) e il
più istruttivo, perché lì il campo c'era ed era pure corretto. Adesso quella
metà entra nel verdetto, e quando il tool non sa dove sia finito il file la
metà non osservabile si **dichiara**:

```
verdetto : non_verificato
fonte    : os.path.exists sull'origine; la destinazione non è stata riferita
           e non si può guardare
```

---

## ⑤ Il debito, contato invece che nascosto

```
$ jarvis doctor
VERIFICA  WARN   3/25 tool hanno un verificatore; distruttivi scoperti: 6/9 —
                 copy_path, create_folder, move_path, organize_folder,
                 pin_fact, write_topic. Ognuno di questi dichiara
                 NON_VERIFICATO, che e' onesto: e' il debito, ed e' dichiarato
```

`warn` e non `ok`, e la scelta è deliberata: un `list_dir` senza verificatore
non fa male a nessuno, un `move_path` che dichiara `ok=True` senza che nessuno
abbia guardato dove sono finiti i file è precisamente il caso per cui ADR-012
esiste.

⚠️ Il numero viaggia nello `state.snapshot`: il registro dei tool vive nel
processo del core e `jarvis doctor` è un altro processo. Chiederlo al registro
locale darebbe **zero** — un numero falso e tranquillizzante al contrario, cioè
il peggiore dei due modi di sbagliare.

---

## ⑥ Che cosa NON è verificato — per nome

1. **La metà «i commenti ci sono ancora» di `imposta_valore` è DEBOLE.**
   ADR-012 la chiede; senza un conteggio di *prima* si può solo verificare che
   non siano spariti **tutti**. Il caso reale è coperto — un file di
   impostazioni i commenti li perde in blocco, quando qualcuno sostituisce
   `tomlkit` con un `toml.dump` — ma un commento perso su venti non lo vedrei.
   Dichiarato debole invece che spacciato per forte: è la regola di ADR-012.
2. **Sei tool distruttivi su nove restano scoperti.** `copy_path`,
   `create_folder`, `move_path`, `organize_folder`, `pin_fact`, `write_topic`.
   Dichiarano `NON_VERIFICATO`, che è lo stato corretto, e `jarvis doctor` li
   nomina. È il debito, ed è misurato: 6/9.
3. **Nessun verificatore è stato provato contro un guasto reale del
   filesystem** — disco pieno, permessi tolti a metà, `os.replace` interrotto.
   Provati contro il caso riuscito e contro il caso non eseguito, non contro il
   caso *rotto a metà*, che è quello in cui un verificatore vale di più.
4. **`_verifica` gira anche sui tool in sola lettura**, e per tutti torna
   `NON_VERIFICATO`. Non è un costo misurato: non ho cronometrato l'aggiunta
   sul percorso di `list_dir`, che sta nello stato iniziale di ogni scrivania.

---

## ⑥bis `BLOCCATO` non arrivava al registro — trovato il 31 agosto

⚠️ **Aggiunto dopo, provando il RIFIUTO della conferma dal vivo con Electron.**

`_ESITO` — il gancio di §6.2 — girava solo sul ramo approvato. Una domanda
**rifiutata** non lasciava nessuna riga di diario: il log l'aveva, il registro
no. Quindi il verdetto che questo ADR ha introdotto per il caso «non è stato
fatto, e il registro l'ha visto» **non poteva essere visto da nessuno** che
rileggesse il diario, salvo per la via della voce, dove `esegui_t0` scrive la
riga per conto proprio.

Adesso il gancio gira su entrambi i rami — *un piano, una risposta* — e
`_bloccata` timbra anche la traccia di ADR-011, che sul ramo rifiutato arrivava
`None` perché `invoke()` timbra al ritorno, cioè dopo il gancio.

È lo stesso difetto del ramo approvato, chiuso il 30 agosto con la stessa cura,
ricomparso sul ramo che nessuno aveva attraversato.

---

## ⑦ Rapporto con l'invariante 3 — invariato

**La verifica non sostituisce mai la conferma.** La conferma sta *prima*
dell'azione e la autorizza un umano; la verifica sta *dopo* e la fa la macchina.
Nessun tool `side_effect=True` ha smesso di chiedere conferma perché adesso si
verifica, e i test di `test_confirm_e2e.py` (10) sono verdi senza una modifica.
