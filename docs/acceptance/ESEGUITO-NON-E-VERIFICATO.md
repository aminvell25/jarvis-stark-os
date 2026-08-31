# «Eseguito» non è «verificato» — ADR-012, fetta 2

**Data**: 30 agosto 2026 · **Riferimento**: `docs/DECISIONI-COGNITIVE.md` ADR-012,
`CLAUDE.md` invariante 32 · **Rollback**: `f3f06ed`
**Test**: 1877 → 1901 → **2057** dopo le correzioni del 31 agosto (§⑧), 25 saltati, **0 rossi**

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
| `NON_VERIFICATO` | `registry._verifica` quando manca un verificatore, quando cade, **o quando ritorna un non-`Verifica`** (dal 31 agosto) |

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

⚠️ **E dal 31 agosto si contano due cose, non una.** Quel `3/25` conta i
verificatori **DICHIARATI**, e dichiarare non è verificare: tre
`lambda: Verifica.non_verificata("todo")` avrebbero portato il check da `warn`
a `ok` con zero coperti a runtime. L'unica misura che sorveglia l'onestà di
questo ADR era l'unica falsificabile in tre righe.

Adesso `registry._verifica` — l'unico punto da cui passa ogni verdetto — tiene
il conto per tool e per valore, e lo snapshot lo porta accanto a `verificabile`:

```
"verificabile": true,  "verdetti": {"riuscito": 2}
```

Il cancello `ok`/`warn` **resta sui distruttivi scoperti**: un core appena
avviato non ha prodotto niente, e non deve dire il falso per questo. Ciò che si
aggiunge è il **nome** di chi ha girato e non ha mai concluso:

```
1/1 tool hanno un verificatore; distruttivi scoperti: 0/0. ⚠️ dichiarano un
verificatore e non hanno mai concluso: finto (5 verdetti, 0 conclusivi)
```

Uno stub non si scopre all'avvio — non c'è ancora niente da scoprire — ma **al
primo uso reale**, che è quando la bugia comincia a contare.

---

## ⑥ Che cosa NON è verificato — per nome

0. ~~**L'atteso di `imposta_valore` veniva dal referto del tool.**~~ ✅
   **Chiuso il 31 agosto**, vedi §⑧. Era il difetto peggiore di questo
   documento e non era dichiarato da nessuna parte: due verificatori nello
   stesso ADR con regole opposte.
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

## ⑧ Quattro correzioni della revisione del 31 agosto

Quattro difetti trovati rileggendo questo ADR contro il codice, e chiusi in un
commit solo. Tre riguardano ADR-012; il quarto è il suo criterio 1.

### ① L'atteso veniva dal referto del tool

```python
scritto = (r.output or {}).get("valore")      # ← il tool che parla di sé
atteso=f"{a.chiave} = {scritto!r} sul disco, con i commenti"
```

L'osservato era indipendente — il file riletto con `tomlkit` — ma l'atteso no.
Il confronto chiedeva «ciò che il tool dice di aver scritto è ciò che il tool ha
scritto», che è vero per costruzione. E il gemello `create_file` vieta
esattamente questo **per iscritto**: *«se dipendesse dal referto del tool, il
tool si autocertificherebbe»*. Due verificatori nello stesso ADR con regole
opposte, e §⑥ non lo dichiarava: dichiarava l'altra metà, quella sui commenti.

Corretto, non dichiarato debole — l'atteso è derivabile dagli argomenti in
tutt'e due le forme:

| forma | atteso |
|---|---|
| scalare | `_converti(a.valore, _tipo_atteso(...))`, la **stessa** conversione che `imposta()` applica |
| elemento | non un valore ma una **presenza**: dopo `aggiungi` l'elemento c'è, dopo `togli` non c'è |

Il confronto per la forma a elemento usa solo i **campi che il chiamante ha
dato**: `model_dump()` riempie i default e un record sul disco può ometterli,
quindi l'uguaglianza fra dizionari darebbe un `FALLITO` falso su una scrittura
andata benissimo. E il `togli` guarda l'assenza di **entrambe** le forme,
normalizzata e grezza, perché il file può tenere `~/Documenti` dove l'argomento
diceva il percorso espanso.

### ② Un verificatore che RITORNA storto sfuggiva dal `try`

`if tool.name in esito.fonte:` stava **fuori**. Un verificatore che restituisce
un non-`Verifica` — `None` è il caso ovvio, e `core/tools/files.py` tipizza già
`_non_eseguito(...) -> Verifica | None` **dentro questo stesso ADR** — alzava
`AttributeError`, che usciva da `invoke()` dopo la scrittura distruttiva e prima
di `_riferisci`:

```
_esegui  →  _verifica ✗  →  ( _riferisci mai chiamato )
azione avvenuta · nessun fs.result · nessuna riga di diario
```

Cioè il guasto peggiore che quel modulo possa produrre, perché due righe stavano
dopo il `except` invece che dentro il `try`. Non era raggiungibile con i tre
verificatori di oggi; il tipo non lo impediva, e il docstring prometteva «Non
solleva» da sempre. **Una promessa mantenuta per fortuna non è mantenuta.**

### ③ Il criterio 1 diceva «si vede nel diario», e non si vedeva

`scripts/diario.py` non nominava `verdetto` in nessuna riga — zero occorrenze in
tutto il file. `jarvis diario` stampava `ok create_file` anche con
`verdetto=fallito`, cioè proprio nel caso per cui questo ADR esiste. Il campo
era nel JSONL dal 30 agosto; per leggerlo bisognava aprire il file a mano.

Due colonne, e il verdetto che smentisce l'`ok` va in **maiuscolo**. L'osservato
si stampa solo quando il verdetto non è `riuscito`, troncato a 64 caratteri.

⚠️ E la regola su ciò che manca è l'**opposta** di quella di `_traccia()`: una
riga senza traccia è un orfano, una riga senza verdetto è spesso una riga che
non è l'esecuzione di un tool — `_annota_instradamento` scrive `verdetto=None`
di proposito. Marcarle riempirebbe il registro di trattini muti.

### ④ `doctor` contava i verificatori dichiarati

Vedi §⑤: il conto dei **verdetti prodotti** sta accanto a quello dei
dichiarati, e il check nomina chi ha girato senza mai concludere.

### I quattro sabotaggi

| sabotaggio | rosso |
|---|---|
| l'atteso torna dal referto del tool | `test_un_referto_che_MENTE_non_cambia_il_verdetto`, `test_e_un_referto_che_TACE_nemmeno` |
| il ritorno storto non è più controllato | `TestUnVerificatoreCheRITORNAStorto` ×4 |
| il diario torna a tacere il verdetto | `TestIlVerdettoSiVedeNelDiario` ×3 |
| `doctor` torna a contare i dichiarati | `test_uno_STUB_che_ha_girato_viene_NOMINATO`, `test_un_BLOCCATO_non_conta_come_conclusivo` |

⚠️ **Non provato sul registro vero.** Il diario di questa macchina non ha
**nessuna** riga con un verdetto: il core non ha eseguito un tool dopo il 30
agosto. La resa è provata dai test e su righe costruite a mano; che una riga
vera con `FALLITO` si veda bene resta da guardare il giorno in cui ce ne sarà
una.

---

## ⑦ Rapporto con l'invariante 3 — invariato

**La verifica non sostituisce mai la conferma.** La conferma sta *prima*
dell'azione e la autorizza un umano; la verifica sta *dopo* e la fa la macchina.
Nessun tool `side_effect=True` ha smesso di chiedere conferma perché adesso si
verifica, e i test di `test_confirm_e2e.py` (10) sono verdi senza una modifica.
