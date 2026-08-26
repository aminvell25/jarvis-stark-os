# Il diario nella scrivania — due registri, e due difetti visti solo guardando

**Data**: 26 agosto 2026 · **Riferimento**: `docs/SPEC.md` §3.2, §10.2, §11.7, §11.8, §13
**Rollback**: `f0c0fa3` · **Test**: 1392 → **1401**

---

## Che cosa mostra, e perché due colonne

```
DIALOGO                          INTENZIONI E AZIONI
21:21:14 ◂ JARVIS  Intende…      21:20:52 NO needs_attention …   NESSUNA
21:21:08 ▸ SIGNORE Spiegami…     21:20:45 OK set_volume 40           TOOL
```

Non è impaginazione: sono **due domande diverse**. *«Che cosa mi ha risposto»*
si legge in ordine di conversazione; *«perché ha aperto quel pannello»* si legge
in ordine di causa. Mescolarle produce una colonna in cui non se ne legge
nessuna.

Tre cose che il registro rende visibili e che prima non lo erano:

- una risposta **INTERROTTA** dal barge-in, in ambra, distinta da una finita;
- un testo detto **stimato** — col TTS locale `text_spoken` non esiste, e ciò
  che si sa è il testo mandato al sintetizzatore: un limite superiore;
- un intento **senza destinazione**, in ambra: JARVIS ha capito e non ha fatto
  niente. È la riga più utile del registro.

## Il ciclo §11.7, eseguito

Reso in galleria, scattato, **guardato**, checklist §11.8 punto per punto. Ha
trovato **due difetti che nessun test avrebbe visto**.

### ① I due marcatori si escludevano a vicenda

Erano due regole `::after` sullo **stesso** pseudo-elemento. Quando una risposta
era insieme interrotta e stimata — cioè **il caso normale col TTS locale** — la
seconda regola vinceva e **INTERROTTO spariva**.

Il marcatore che conta di più era esattamente quello che si perdeva. Adesso i
marcatori sono **DATO nel DOM**, non decorazione CSS, e convivono.

### ② Il piede mostrava un epoch

`1787773978011`. `adesso()` restituisce i millisecondi dell'epoca; `ora()` è la
funzione che tutti i piedi tecnici usano già. Adesso: `21:53:45`.

Entrambi visibili nello scatto e in nessun altro modo. È l'argomento di §11.7 in
una riga: **generare lo screenshot non è guardarlo.**

### Lo stato vuoto, verificato con uno scatto suo

`shots/diario-vuoto.png`: «NESSUNA BATTUTA — non è stato detto nulla da quando
il core è partito», «NESSUNA AZIONE — nessun intento è stato deciso», piede a
`0 battute 0 azioni` e `--:--:--`. Invariante 23 verificato **visto**, non
dichiarato.

## Il fixture della galleria è registrato, non inventato

Le righe vengono dalla sessione vocale vera del 26 agosto, trascrizione sporca
inclusa — «duedici», «il cero è blu». §11.9 non serve: quelle frasi le ha dette
qualcuno. **Un fixture ripulito mostrerebbe un pannello che non esiste.**

---

## Tre guardiani hanno preteso una dichiarazione

Aggiungere un modulo non è aggiungere un file:

| guardiano | ha preteso |
|---|---|
| `test_l_elenco_degli_auditati_NON_DERIVA` | `diario` in `COMPONENTI`, o l'audit non lo guarda |
| `test_l_indice_ha_gli_otto_moduli…` | la riga in `DOPO`, con la sezione che lo introduce |
| `test_ogni_categoria_copre_la_griglia…` | `fuoriPiastrellatura`, perché la mia cella si sovrapponeva |

E la densità è stata **rimisurata**: 108 → 111 sorgenti, impronta
`0f76887d…` → `4eb4d262…`, esito **conforme**, `falliti: []`.

⚠️ **Categoria 1, non 3.** Il diario non è una finestra sul mondo, è uno
strumento sul **sistema**: sta accanto a telemetria e agenti, non al browser.

---

## Verifica

### ✅ Le bocciature

| perturbazione | esito |
|---|---|
| un colore letterale al posto di un token | 1 rosso |
| il marcatore composto a vuoto | 1 rosso — **dopo aver rafforzato l'assert** |

⚠️ La seconda **non discriminava**: svuotando `m.textContent` il marcatore
spariva dallo schermo e il test restava verde, perché le stringhe erano ancora
nel sorgente. Riscritto per guardare che la parola arrivi nel DOM.

### ⚠️ Tre inciampi miei, tutti della stessa famiglia

1. **Un backtick in un commento CSS** ha chiuso il template literal e il modulo
   non si caricava. **Quarta volta** in questo progetto — ed è in memoria.
   `tests/test_fogli_di_stile.py` lo dice in 0,04 s, e non l'avevo eseguito:
   ho lanciato `npm run shot`, che è andato in timeout senza spiegare niente.
2. Un mio test cercava `::after` e lo trovava **dentro un commento** che
   spiega perché non si usa più.
3. Un altro pescava `&#8862;` — la entity dei glifi di controllo — come
   «colore letterale».

Tutti e tre risolti tagliando i commenti prima di cercare. **Terza volta in
questa sessione** che un test guarda un commento invece del codice.

### ✅ La suite

`1392 → 1401`, verde. Densità conforme.

### ❌ NON verificato

- **Il pannello dal vivo, nella finestra Electron.** Reso e giudicato in
  galleria; che riceva `agent.diario` dal socket vero non è stato osservato —
  serve aprire l'app, ed è il passo successivo.
- **Il comportamento con molte righe.** `MAX_RIGHE = 40` per colonna, scelto
  perché il registro completo vive su disco. Con quaranta righe vere lo
  scorrimento non è stato guardato.
- **La colonna del dialogo in ordine inverso.** Il più recente in cima è giusto
  per un monitor e scomodo per una conversazione. È una scelta, non una misura.
