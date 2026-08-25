# §26.7 — la pagina impostazioni, e il file resta la verità

**Rollback:** `752b830`
**Criterio ② del piano:** «ogni impostazione di `settings.toml` modificabile
dalla pagina, e il file resta la verità».
**Criterio 7 di §26.9:** «cambiare la dimensione delle icone dalla pagina
riscrive `settings.toml` **conservando i commenti**, e l'effetto si vede senza
riavviare».
**Esito: la pagina esiste, scrive conservando i commenti, e le cinque chiavi
che decidono se un sottosistema esiste NON si toccano da lì. Il criterio 7 è
soddisfatto a metà, e la metà mancante è dichiarata in §10.3.**

**✅ La densità è stata rimisurata** (§8b): `DENSITA' CONFORME`, e i sei numeri
sono **identici** a quelli di prima della pagina. La suite è a **777 verdi,
zero rossi**.

---

## 1. Il file da zero byte

`ui/src/panels/settings.js` era **0 byte dalla Fase 0**, come
`core/voice/audio_io.py` fino a ieri. `tomlkit` era fra le dipendenze dallo
stesso giorno, col commento «TOML in lettura E scrittura, commenti
preservati», e `core/settings.py` lo usava solo per `parse`: la scrittura era
prevista e non era mai stata fatta.

## 2. Le cinque regole di §26.7, e dove stanno

| regola | dove |
|---|---|
| 1. scrive il core, mai il renderer | `core/tools/impostazioni.py` è l'unico posto che riscrive il file |
| 2. con `tomlkit`, commenti preservati | provato: 26 commenti su 26 sopravvivono, e cambia **una riga sola** |
| 3. un solo tool, `side_effect=True` con conferma | `imposta_valore`, col piano che mostra il percorso risolto |
| 4. quattro chiavi non si cambiano dall'interfaccia | `BLOCCATE`, e sono **cinque** — vedi §4 |
| 5. il ricaricamento a caldo lo fa già `SettingsStore` | nessuna notifica scritta a mano |

## 3. L'allowlist si DERIVA dallo schema

`chiavi_modificabili()` cammina il modello pydantic invece di elencare a mano
le chiavi ammesse: **35 foglie scalari**. Un elenco scritto a mano è una
seconda opinione su che cosa esista, e diverge dal modello alla prima
aggiunta — il difetto già pagato coi tre ritagli, i due orologi e le due
clamp.

Passano solo `int`, `float`, `bool`, `str`. Le strutture — le scene, le frasi
di wake, le radici — non compaiono: `imposta_valore(chiave, valore)` sa
scrivere una foglia, e fingere il contrario darebbe un errore a metà scrittura
invece di un rifiuto. §26.7 le elenca fra ciò che la pagina regola: è **lavoro
dichiarato, non fatto**.

## 4. La quinta bloccata, aggiunta e dichiarata

§26.7 ne nomina quattro. `fs.trash_only` è la quinta, e per una ragione
meccanica: lo schema la dichiara `Literal[True]` — invariante 4, «solo
cestino» — quindi **l'unico cambiamento possibile è uno che viene rifiutato**.
Un comando che può solo fallire non è un comando: è un fatto, e i fatti si
mostrano.

## 5. Il file non si rompe mai a metà

Due difese, e servono tutt'e due:

* **si valida prima di scrivere.** Il documento modificato passa dal modello
  `Settings`; se non passa, non si scrive niente. Un `settings.toml` che non
  carica non è un fastidio: `load_settings` solleva e **il core non parte
  più**, e ci si ripara solo con un editor — cioè esattamente la cosa che
  questa pagina esiste per non richiedere.
* **si scrive per rinomina**, e il come sta in `core/platform.scrivi_atomico`.

⚠️ **L'invariante 29 l'ha trovato il suo controllo.** La prima versione faceva
`percorso.stat().st_mode` dentro `core/tools/`, e
`test_nessuna_chiamata_di_piattaforma_fuori_da_platform` è diventato rosso: i
bit di permesso sono POSIX, e su Windows `chmod` onora solo il flag di sola
lettura. La stessa riga significherebbe due cose diverse. Spostata.

## 6. Il quarto tipo in ingresso, e il ponte resta un ponte

`core/ws_server.py` accettava **tre** tipi e nient'altro, con una allowlist
deliberata: «non un dispatch generico su `topic`». Adesso ne accetta quattro.

`test_cio_che_sale_e_una_risposta_oppure_uno_STATO` aveva **previsto questo
giorno**:

> «il giorno in cui questo elenco conterrà un messaggio senza `id`, sarà una
> RICHIESTA, e allora il ponte avrà smesso di essere un ponte».

`ui.imposta` è una richiesta: nomina un'operazione e non cita l'`id` di nessuna
domanda. Ma **non esegue**: il core la instrada in `imposta_valore`, che ha
`side_effect=True` e apre percio' la conferma di §6.2. La richiesta fa
*nascere* una domanda, e la risposta la dà un umano.

Il terzo ramo non è una scappatoia perché è verificabile, e c'è un test nuovo
che lo verifica: l'instradamento passa dal registry, il tool ha
`side_effect=True`, e ha un planner — senza, chi conferma non vedrebbe quale
file sta per cambiare (invariante 3).

Il preload passa da cinque funzioni a sei. Lo stesso test dice come si
aggiorna: «dichiarando perché, non allentando il confronto a un `>=`».

## 7. Il ciclo §11.7, e la checklist §11.8 punto per punto

Reso in galleria, scattato, **guardato**. Tre difetti trovati guardando, non
ragionando:

| | trovato guardando |
|---|---|
| 1 | le **bloccate non si vedevano**: erano in fondo, e 35 righe le spingevano sotto il bordo. Sono la parte che §26.7 protegge, ed erano l'unica invisibile. Spostate in testa: non sono impostazioni, sono la cornice dentro cui si legge il resto |
| 2 | `flux-general-multi` **troncato** a 14ch |
| 3 | e poi `claude-haiku-4-5-20251001` troncato a 18ch + padding: avevo guardato una sezione sola e chiamato «il più lungo dello schema» il più lungo di quella |

La terza ha cambiato l'approccio: niente larghezza fissa. Il campo si
dimensiona sul proprio contenuto, perché un nome di modello si allunga quando
ne esce uno nuovo e una larghezza scelta oggi torna a tagliare fra sei mesi,
in silenzio.

⚠️ **E il backtick nel commento CSS, per la ventesima volta.** Chiude il
template literal e il modulo non si carica. `tests/test_fogli_di_stile.py` lo
prende in 0,04 s — e l'ha preso **due volte**, la seconda dentro
l'avvertimento che avevo appena scritto per non rifarlo.

### §11.8, punto per punto

```
GEOMETRIA
✓ border-radius 0            var(--radius), che tokens.css dichiara SEMPRE zero
✓ taglio a 45°               lo mette la cornice (app.css .winbox::before/after),
                             non il componente — una volta sola per tutti
✓ spaziature multiple di 4   solo --s-1 (4), --s-2 (8), --s-3 (16)
✓ pesi di linea              hair sui bordi, base sul focus. Nessun terzo

COLORE
✓ tutti da tokens.css        MISURATO: audit 0 elementi fuori sistema,
                             0 regole con letterali
✓ caldo < 10%                --amber su due elementi di testo su ~90
✓ tinte ≤ 3                  ciano, grigio, ambra
✓ zero gradienti             nessuno
✓ zero alone/bloom/glow      nessun box-shadow, nessun filter
~ ombra nera su chi copre    VACUO: non ci sono ombre. Lo dico invece di
                             spuntarlo come se avessi verificato qualcosa

TIPOGRAFIA
✓ solo i sei gradini         --t-micro, --t-data, --t-label
✓ numeri in --font-mono      chiavi e valori
✓ caps con letter-spacing    titoli 0.14em, tasti 0.12em
✓ niente sotto 8.5px         --t-micro è il pavimento, ed è usato per titoli,
                             errori e piede. Nessun corpo di prosa: le righe
                             sono dati, e i dati stanno a --t-data come in files.js

CONTENUTO
✓ dati VERI                  da config/settings.toml, per la stessa
                             chiavi_modificabili() della pagina viva
✓ etichetta + versione + piede   SETTINGS · VER 1; piede: 35 modificabili,
                             5 nel file, e il percorso
✓ un valore numerico mono    trentacinque
✗ densità contro il riferimento   NON MISURATO. Le famiglie di
                             docs/design-reference sono scrivanie, non pagine
                             di configurazione: non ho un riferimento con cui
                             confrontare, e non ne invento uno

MOVIMENTO
✓ ogni animazione ha causa   VACUO: non ce n'è nessuna
✓ zero animazione ambientale
✓ solo anime.js              nessuna animazione

TECNOLOGIA
✓ testo nel DOM              tutto DOM
— Line2 / uPlot              non applicabile: nessun 3D, nessun grafico
```

**Un ✗**, ed è dichiarato: il confronto di densità con un'immagine di
riferimento non si può fare perché il riferimento non esiste per questo tipo
di pagina.

## 8. Verifica, e che cosa resta rosso

| | |
|---|---|
| `tests/test_impostazioni_scrittura.py` | **35** asserzioni |
| `uv run pytest -q` | **777 passed** (era 741) |
| `node scripts/shot.mjs settings` | audit **0 e 0**, esito OK |
| `tests/eval_visual.py` | i miei rossi: **zero** (vedi §9) |

**Ritirata una correzione per volta:**

| ritirata | esito |
|---|---|
| i commenti non si conservano (dump semplice) | 2 rossi |
| non si valida prima di scrivere | 4 rossi |
| le bloccate non si controllano | 7 rossi |
| il ramo `secrets` escluso per nome | 1 rosso |
| l'ascolto dell'esito nel renderer | 1 rosso |
| il ponte manda un topic diverso | 1 rosso |
| il core non prova il quarto tipo in ingresso | 1 rosso |

⚠️ **Al momento del commit restava un rosso**:
`test_densita.py::test_la_misura_descrive_i_sorgenti_di_ADESSO`. L'impronta
copre tutti i sorgenti di `ui/`, e ne avevo aggiunti due e toccati tre. Non
potevo rimisurare: la scrivania era aperta da un'ora e venti e teneva
`scatto.lock` — la correzione, giusta, che impedisce due Electron insieme.
Chiuderla mentre era in uso non era una decisione mia.

## 8b. La densità rimisurata, a scrivania chiusa

```
scrivania.png    1536x843   lum 46 · dev 34.8 · H 2.43 · 25-120 65.5 %
                            L>60 28 % · L>120 5.5 % · caldo 3.7 % · barra 63.8 %
scrivania-b.png             identico — 0 pixel su 1.294.848 in 250 ms
esito            impronta su 108 sorgenti · fixture:4d5edf35cfdb64af
DENSITA' CONFORME
```

| criterio | soglia | misura | margine |
|---|---|---|---|
| entropia | 2,40 | **2,43** | **+0,03** |
| dev. std | 32 | 34,8 | +2,8 |
| `L>60` | 25 % | 28 % | +3 |
| caldo | 3-6 % | 3,7 % | dentro |
| barra | 25 % | 63,8 % | +38,8 |
| dock | 20 % | 24,2 % | +4,2 |

⚠️ **I sei numeri sono identici a quelli di prima della pagina**, alla
precisione stampata. È coerente con la scelta di §7: il pannello è
`suRichiesta` e non entra nella scena `avvio`, quindi non c'è a schermo quando
la misura scatta.

Non dico «zero pixel cambiati rispetto alla misura precedente»: quel PNG è
stato sovrascritto da questa esecuzione, e non ho più il termine di paragone.
Quello che è misurato è che **le due riprese di QUESTA esecuzione coincidono**,
e che le sei metriche non si sono mosse.

Il margine sull'entropia resta **+0,03**, il quinto atterraggio nei centesimi
di questo progetto. Non l'ha peggiorato la pagina, e non l'ha migliorato.

## 9. Cinque rossi che ho trovato e che non sono miei

`tests/eval_visual.py` — la suite trasversale che §22 dice di far girare
**all'inizio di ogni fase** — era già rossa prima che toccassi niente:

```
test_l_indice_ha_gli_otto_moduli_di_13_piu_quelli_dichiarati_dopo
test_ogni_categoria_copre_la_griglia_senza_buchi
test_l_insegna_non_usa_i_colori_del_dato
test_il_traffico_dell_insegna_non_conta_il_battito
test_la_scena_di_avvio_lascia_LIBERO_il_centro
```

Verificato con `git stash`: cinque prima, cinque dopo. **Non è nella suite
predefinita**, quindi nessuno la stava eseguendo — ed è esattamente il caso
per cui §22 scrive «gira all'inizio di ogni fase, non solo alla fine: è così
che scopre le regressioni della fase precedente».

Uno di quei test lo ha fatto davvero: `test_i_nomi_che_si_dicono_a_voce_
trovano_un_pannello` **fissava `impostazioni` come eccezione dichiarata** —
«la grammatica lo accetta dalla Fase 3, il file è vuoto». Il debito che
sorvegliava è chiuso, e l'elenco delle eccezioni adesso è vuoto.

## 10. Dichiarato aperto

1. ~~**La misura di densità va rifatta**~~ — **fatta**, vedi §8b. Il punto 1
   della *definizione di fatto* è verde.
2. **Le strutture non si modificano**: scene, frasi di wake, radici. §26.7 le
   elenca; il tool scrive foglie. Aggiungerle vuol dire un secondo tool con
   una forma diversa, non un parametro in più.
3. **Il criterio 7 di §26.9 è soddisfatto a metà.** «Riscrive conservando i
   commenti»: provato. «L'effetto si vede senza riavviare»: il `SettingsStore`
   ricarica a caldo e il core rimanda lo snapshot, ma `ui.grid_px` **non è
   collegato a `--grid`** — tokens.css lo dichiara `110px` fisso e nessuno
   legge l'impostazione. Due proprietari per la stessa misura, che oggi
   coincidono per caso: cambiarne uno li separa in silenzio. Non l'ho
   collegato in questo turno perché è una decisione di design — quali token
   siano guidati dalle impostazioni — e non un dettaglio.
4. **La scrittura non è provata dal vivo**: le prove coprono il tool, la forma
   dei messaggi e ogni giunzione, ma nessuno ha ancora cambiato un valore
   cliccando. Serve la scrivania aperta e un clic.
5. **I cinque rossi di `eval_visual.py`** (§9) restano.
