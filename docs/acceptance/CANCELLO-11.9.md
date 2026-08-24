# Cancello §11.9 — la seconda eccezione, e §11.7 regola 5

**Data:** 25 agosto 2026 · **Rollback:** `0807da9`
**Precedente di forma:** `e4851ae` / `CANCELLO-10.6.md` — governance, **zero codice**

## Che cosa lo motiva

Due sessioni di `npm run scrivania` danno `L>60` **26,1 %** e **25,3 %**, e la
differenza **non è attribuibile**. Il margine sulla soglia è passato da +1,1 a
+0,3 in un turno che non ha toccato nessuna superficie.

**Quattro misure contaminate in due giorni**, tutte già scritte:

| | dove sta scritto |
|---|---|
| le miniature del modulo Media | `ISTOGRAMMA-E-BIN-VUOTI.md` |
| il ritaglio del marchio contro `b2f7360` | `SUPERFICIE-CHIARA.md` |
| lo scatto con la CPU all'1,7 % invece del 3,6 % | `FONDO-26-5.md` — «un settimo scatto, scartato» |
| la barra rimasta `DEGRADED` | `DEBORDO-R99.md` |

In tutti e quattro il **numero era giusto** e il **confronto era nullo**.

## Perché non basta il protocollo A/B

Quello costruito il 24 agosto — tre scatti per lato, `git stash` in mezzo,
stessa sessione — è corretto e funziona **dentro** una sessione. Fra sessioni
non protegge niente: il core riparte, la CPU è quella che è, e la barra cambia
stato da sola.

## La causa, misurata

| sorgente | cadenza | effetto |
|---|---|---|
| `telemetry` | **2,5 Hz** | due serie uPlot ad **area piena**, `--fill-1` (L 66) e `--fill-2` (L 89), **entrambe sopra la soglia L>60**, alte quanto `cpu_percent`. Il pannello è il **16,5 %** dello schermo |
| `telemetry.top3` | 1 Hz | nomi processo e barre larghe quanto la CPU |
| barra `up` | 1 s | testo che avanza |
| barra `cpu/ram/temp` | 2,5 Hz | testo, e un riquadro `--amber` oltre soglia |
| globo | `new Date()` nel renderer | terminatore e conteggio luce/ombra |

⚠️ E `scattiIdentici` è **`false` in tutti e quattro** gli `occlusione.json`
presenti: due scatti a 250 ms **dentro la stessa esecuzione** già differiscono.
`telemetry` arriva ogni 400 ms — nel ~62 % dei casi ne cade uno in mezzo e uPlot
ridipinge. **Non è raggiunta l'identità nemmeno dentro un'esecuzione.**

## Che cosa cambia

§11.9 aveva **una** eccezione, la galleria. Adesso ne ha due, e la seconda **non
è un dataset: è un modo**. Vale solo con tutte e cinque le condizioni scritte in
§11.9, di cui le due che portano il peso:

- **i dati sono registrati da una sessione vera, mai generati** — l'invariante
  23 non si sfiora, e non è la concessione della galleria: là i dati sono finti
  con la *forma* dei veri, qui sono **veri e vecchi**;
- **una misura di fixture non si confronta mai con una viva** — sono due
  popolazioni.

⚠️ **Che cosa NON cambia.** L'invariante 1: il renderer riceve da un socket che
non controlla, e la sorgente resta **fuori** dall'applicazione. L'invariante 7:
socket UNIX in `$XDG_RUNTIME_DIR`, directory 0700, mai una porta — vale identica
per il riproduttore. E `npm run app` non tocca niente di tutto questo.

## §11.7 prende una regola 5

> **La provenienza di una misura fa parte della misura.** Un numero senza la sua
> sorgente non è un numero: non si sa con che cosa si può confrontare. Due numeri
> di provenienza diversa **non si sottraggono**, e un delta fra loro non esiste.

È la riga che avrebbe impedito tutte e quattro le contaminazioni, ed è la stessa
specie di §11.7 regola 4 — che viaggiò con §10.6 per la stessa ragione: due
emendamenti alla specifica stanno in un turno di governance, non dentro
un'implementazione.

## Quanto costa, e quanto vale

**Costa una baseline.** Rifare la registrazione azzera tutto ciò che era stato
misurato prima: la fixture compra **delta attribuibili dentro una baseline**, non
comparabilità fra baseline diverse.

**Vale l'unica soglia ancora aperta.** L'entropia sta a 2,21 su 2,40, e la mossa
più redditizia misurata fra i sei componenti a schermo vale **+0,07**. Con un
pavimento di rumore a ±1 punto di `L>60` e ±0,05 di entropia, +0,07 **non si
può leggere**. Senza fixture il lavoro che resta non è misurabile.

⚠️ **E una fixture fissa i dati, non il renderer.** Un aggiornamento di driver o
di font sposta il numero senza che nel repo cambi niente. Mitigazione a costo
quasi nullo, da fare in T3: scrivere in `occlusione.json` la versione di
Electron, il `devicePixelRatio` e la stringa del renderer.

## Il costo del ritorno

Chiudere il cancello dopo l'uso significa togliere il riproduttore e il
registratore — due script — e tornare a misurare dal vivo, cioè a un pavimento
di rumore che rende invisibile qualunque delta sotto il punto percentuale. Prima
dell'uso non costa niente: oggi nessun comando usa la seconda eccezione, e la
riga di §11.9 è inerte.
