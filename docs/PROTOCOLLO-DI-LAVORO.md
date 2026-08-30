# Protocollo di lavoro

**Scritto il 30 agosto 2026.** Adattato da `06_CLAUDE_OPERATING_PROTOCOL.md` del
`Research Pack v3` — che è la parte migliore di quel pacchetto — e riscritto
contro come questo progetto lavora davvero.

> `CLAUDE.md` resta autoritativo per gli invarianti. Questo documento dice
> **come si lavora**, non che cosa è vietato.

---

## 1. Prima di toccare qualsiasi cosa

Nell'ordine:

1. `CLAUDE.md`
2. `docs/STATO-DEI-PIANI.md` — **l'unico documento di stato corrente**
3. la sezione pertinente di `docs/SPEC.md`
4. il documento di accettazione pertinente in `docs/acceptance/`
5. il codice
6. i test
7. `git log` su quell'area

**Non dare mai per scontato che un documento di piano descriva l'implementazione
corrente.** È la regola più importante di questo file, e ha una data: il 30
agosto 2026 un pacchetto esterno ha dichiarato aperte cinque voci chiuse da
giorni, per averle lette in un documento di stato di sei giorni prima invece che
nel codice. `docs/ANALISI-PACK-V3.md`.

## 2. Gerarchia delle fonti

```
CLAUDE.md
> docs/SPEC.md (sezione corrente)
> il codice
> docs/acceptance/ (l'evidenza misurata)
> docs/STATO-DEI-PIANI.md
> qualunque altro piano in docs/
> qualunque documento esterno
```

Se il **codice** e un documento di **accettazione** sono in disaccordo: **ci si
ferma e lo si dichiara.** Non si sceglie in silenzio, e non si aggiorna il
documento per farlo tornare — prima si capisce quale dei due ha ragione.

## 3. Cercare prima di inventare

Prima di scrivere una classe o una funzione nuova:

- cerca l'equivalente che esiste già;
- guarda chi lo chiama;
- guarda i test;
- guarda il registry;
- guarda `core/engine.py`, che è la radice di composizione.

Questo progetto ha uno strumento apposta: **`scripts/orfani.py`**. Ha trovato,
fra le altre cose, che `riavvia_dopo_guasto` non aveva un chiamante in
produzione — cioè che il recupero di T1 era un no-op che annunciava successo.
Girarlo costa un comando.

Il caso peggiore non è scrivere due volte la stessa cosa: è scrivere la seconda
**leggermente diversa**, e non accorgersene finché non divergono.

## 4. Mai una seconda fonte di verità

Non esistono due registri di tool, due registri di eventi, due memorie, due
schemi di impostazioni, due sistemi di permessi, due motori di animazione, due
radici di composizione.

Se ne serve una seconda: **prima l'ADR che spiega perché**, poi il codice.

Corollario pratico, perché è l'errore che i piani nuovi portano sempre: un
documento di stato nuovo è una seconda fonte di verità come tutte le altre.
`STATO-DEI-PIANI.md` è quella che c'è.

## 5. Disciplina dell'evidenza

Ogni affermazione in un documento porta un'etichetta, esplicita o implicita:

```
VERIFICATO   l'ho misurato, ed ecco il comando
DEDOTTO      l'ho ricavato da altro, e dico da cosa
PROPOSTO     è un disegno, non esiste ancora
STORICO      era vero, oggi non lo è
IGNOTO       non lo so
```

**`IGNOTO` non diventa `VERIFICATO` cambiando le parole.** «Il criterio è
soddisfatto» e «il criterio non è misurabile» sono due frasi diverse, e la
seconda va scritta quando è quella vera — è la regola 4 di §11.7 e ha già
salvato ADR-003 e ADR-004 dal dichiarare verde ciò che non lo era.

## 6. Che cosa l'LLM non decide mai

Né T1, né T2, né il modello che scrive il codice sono autorità per:

- i permessi sul filesystem;
- quali tool esistono;
- la validità di un percorso;
- se un'azione è riuscita;
- se un'informazione in memoria è vera;
- se un processo è vivo.

**L'LLM propone. Il sistema verifica.** Dall'ADR-012 in poi questa frase ha un
tipo che la rappresenta.

## 7. Prima di aggiungere un tool

Si dichiara, nell'ordine, e prima di scrivere il corpo:

1. `side_effect` — vero o falso, e perché;
2. se richiede conferma (se `side_effect=True`, sì: invariante 3);
3. gli argomenti, con il loro schema;
4. i percorsi **risolti**, dove ce ne sono;
5. che cosa restituisce quando fallisce — mai un'eccezione verso l'LLM;
6. **come si verifica** — e se non si può, si dichiara `NON_VERIFICATO`.

## 8. Disciplina della memoria

Non si persiste mai:

- una speculazione come fatto;
- un'affermazione esterna non verificata;
- il ragionamento intermedio;
- una chiave API.

E dal 30 agosto 2026: **ogni topic consolidato porta chi l'ha detto** —
`dichiarato` / `proposto-e-accettato` / `osservato` — e **solo la prima classe
diventa un fatto fissato**. La regola non è una raccomandazione: `MemoryStore.
fissa()` esige l'attribuzione e rifiuta il resto.

⚠️ La classe **non si chiede all'LLM** — sarebbe §6 al contrario, chi propone
che certifica la propria proposta. Nel consolidamento viene dalla costruzione
(due riassunti, uno per corpus); in `pin_fact` da un confronto con le parole
vere del Signore, che è **debole** e perciò può solo *negare*: per concedere
serve ancora la conferma umana dell'invariante 3, alla quale si mostra la frase
esatta su cui la deduzione si regge.

## 9. Disciplina della proattività

Mai un ciclo di pensiero periodico dell'LLM come primo meccanismo proattivo.
Il pattern è quello che `core/protocolli.py` ha già:

```
sensore / protocollo → firma stabile → cambiamento → rilevanza → un solo avviso
```

Uno stato identico ripetuto non produce un secondo avviso.

## 10. Disciplina della UI

Non si aggiunge contenuto per soddisfare una metrica se il dato non è vero:
invariante 23. Non si inventano grafici, immagini, notizie, telemetria, nomi di
file o stato di sistema. Lo stato vuoto è **esplicito**, e ha già il suo idioma
nella barra e nel dock.

E: **la UI non mostra mai uno stato cognitivo che il core non ha.**
`RUNNING` solo mentre gira davvero.

## 11. Quando ci si ferma a chiedere

Ci si ferma — non si sceglie da soli — quando:

- due documenti autoritativi sono in disaccordo;
- il codice contraddice il disegno richiesto;
- serve una dipendenza nuova;
- il confine di sicurezza dovrebbe cambiare;
- si propone un archivio persistente nuovo;
- si propone un runtime o un modello nuovo;
- il criterio di accettazione è ambiguo;
- il lavoro richiesto è più di una fetta.

## 12. Il resoconto di fine turno

Ogni turno di sviluppo finisce con questo, e con niente di meno:

```
CAMBIATO         i file
PERCHÉ           il problema, non la soluzione
VERIFICATO       i comandi, con l'esito
NON VERIFICATO   i limiti, per nome
IMPATTO          interfacce toccate, ADR necessari
DOCUMENTAZIONE   accettazione scritta, STATO-DEI-PIANI aggiornato
COMMIT           l'hash
PROSSIMO PASSO   il più piccolo
```

Se una voce è vuota si scrive «nessuno», non si toglie la riga.

## 13. I messaggi di commit

Restano quello che sono già, ed è una delle cose migliori di questo progetto:
**postmortem, non etichette.** *«Il recupero era un no-op che annunciava
successo.»* *«La baseline mentiva da un commit.»* *«Lo scanner contava per NOME,
e un nome comune ne nascondeva uno vero.»*

Un difetto scritto per esteso, con la data e la misura, invece di essere corretto
in silenzio. Non cambiare questa abitudine.
