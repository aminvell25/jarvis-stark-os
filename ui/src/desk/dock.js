/* Dock inferiore — SPEC §13.
 *
 * §13, verbatim: «gli otto moduli, indicatore T2 attivo, azioni rapide».
 *
 * ## Otto, ne' sette ne' nove
 *
 * Sono le otto righe della tabella dei moduli di §13. Il dock non elenca tutto
 * cio' che sta a schermo: gli anelli, i quadranti, i glifi, la board e i piani
 * sono ARREDO del workspace, non moduli. Un dock che elencasse anche quelli
 * risponderebbe a due domande diverse — «cosa posso accendere?» e «cosa c'e'
 * a schermo?» — e non risponderebbe bene a nessuna delle due.
 *
 * ## Lo stato del pulsante e' lo stato vero
 *
 * Acceso = il pannello e' aperto adesso. Non «l'ho premuto»: la scrivania
 * annuncia, il dock ridisegna. Se un pannello si chiude col suo ⊠, il dock lo
 * sa senza che nessuno glielo dica.
 *
 * ## Le azioni rapide sono le scorciatoie, col mouse
 *
 * `Alt+H` e `Alt+T` sono in §13 e sono azioni della scrivania, non richieste
 * al core: si possono fare, e averle anche col mouse non aggiunge nessuna
 * superficie. Le altre due scorciatoie di §13 — `Alt+Spazio` e `Esc` —
 * parlerebbero al core, e non ci sono: vedi `SEZIONE-13.md`.
 */

export const meta = { nome: "dock", versione: "1" };

export const css = `
.dck {
  display: flex;
  align-items: center;
  gap: var(--s-2);
  /* ⚠️ Il padding verticale scende a --s-1, e l'ALTEZZA DEL DOCK NON CAMBIA.
     Non e' cosmesi: se il dock cresce, il pavimento si accorcia, e un'icona
     posata vicino al bordo basso viene ritagliata al riavvio. Misurato — coi
     chip a --s-1 di padding il dock passava da 28 a 36 px e
     TestIconeVere::test_10_riavviato_il_core_e_ANCORA_LI cadeva.
     Lo spazio per i chip si prende da DENTRO: 4 + 20 + 4 = 28, gli stessi 28
     di prima, e i chip passano da 12 px di altezza a 20. */
  padding: var(--s-1) var(--s-3);
  background: var(--bg-deep);
  border-top: var(--line-base) solid var(--cy-900);
  font-family: var(--font-ui);
}
/* Vedi barra.js: lo spazio lo assorbe chi sta prima. margin-left: auto
   si risolve in un numero di pixel qualunque, e l'audit lo boccia — a
   ragione, perche' non viene da nessuna scala. */
/* ADR-010: fuori dal filtro, non fuori dalla scrivania. Solo il colore del
   testo scende — niente opacita', che smorzerebbe anche il bordo e farebbe
   sembrare il pulsante disattivato invece che di un'altra categoria. */

.dck__filtro {
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.10em;
  color: var(--txt-ghost);
  padding-right: var(--s-2);
  border-right: var(--line-hair) solid var(--cy-900);
}

/* ⚠️ I CAMPI DI STATO — e sono lo STESSO chip della barra, non un secondo.
   .brr__campo: padding --s-1, fondo --fill-1, mono --t-micro, etichetta
   --icona in maiuscole e valore --txt-primary. Una scrivania con due modi di
   dire «ecco un dato» ne ha uno di troppo.
   Il campo senza valore resta SPENTO, come nella barra: acceso vuol dire
   «questo dato c'e'». */
/* flex: 1 e non margin-left: auto su T2: auto si risolve in un numero di
   pixel qualunque e l'audit lo boccia, a ragione, perche' non viene da nessuna
   scala. Lo spazio lo assorbe chi sta prima — e' la regola di barra.js, e il
   commento in cima a questo file la citava gia' senza averla applicata.
   Cosi' T2 si ancora a destra e la fascia prende la forma del riferimento: due
   gruppi e un varco, invece di tutto ammucchiato a sinistra. */
.dck__campi { display: flex; flex: 1; gap: var(--s-1); }
.dck__campo {
  display: flex;
  align-items: baseline;
  gap: var(--s-1);
  padding: var(--s-1);
  background: var(--fill-1);
  border-radius: var(--radius);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.08em;
  white-space: nowrap;
}
.dck__et { color: var(--icona); text-transform: uppercase; }
.dck__vl { color: var(--txt-primary); }
.dck__campo[data-vuoto] { background: var(--bg-raised); }
.dck__campo[data-vuoto] .dck__vl { color: var(--txt-ghost); }

.dck__t2 {
  display: flex;
  align-items: baseline;
  gap: var(--s-2);
  padding-left: var(--s-3);
  border-left: var(--line-hair) solid var(--cy-900);
  font-family: var(--font-mono);
  font-size: var(--t-micro);
  letter-spacing: 0.10em;
  text-transform: uppercase;
  color: var(--txt-ghost);
}
.dck__t2[data-attivo] { color: var(--cy-500); }
.dck__spia {
  width: var(--s-2);
  height: var(--s-2);
  background: var(--txt-ghost);
  border-radius: var(--radius);
}
.dck__t2[data-attivo] .dck__spia { background: var(--cy-500); }
`;

//: Le azioni rapide. Sono le scorciatoie di §13 che si possono fare, con lo
//: stesso nome che hanno li'.

/** Byte in GiB, coppia usato/totale. Il disco della telemetria usa GiB: due
 *  unita' diverse per due memorie della stessa macchina sarebbero due scale. */
function gibi(usati, totali) {
  if (typeof usati !== "number" || typeof totali !== "number" || totali <= 0) return null;
  const G = 1024 ** 3;
  return `${(usati / G).toFixed(1)}/${(totali / G).toFixed(1)} GiB`;
}

export function crea(ospite, { scrivania, bus }) {
  /* ⚠️ §26.3 — il dock ha CEDUTO l'indice al catalogo.
   *
   * Aveva gli otto moduli e le due azioni rapide. Adesso l'indice dei moduli
   * e' la linguetta MODULI del catalogo, e le azioni stanno sul suo plinto:
   * §26.3 dice che il catalogo «unifica la barra delle applicazioni e il file
   * manager», e due elenchi degli stessi otto moduli a schermo sarebbero due
   * posti in cui la stessa verita' puo' divergere.
   *
   * Quello che resta e' STATO, non comandi: dove siamo (il filtro) e che cosa
   * sta facendo il sistema (T2). Una striscia sottile, non una barra.
   *
   * Il criterio A di §13 — «le otto voci aprono e chiudono il proprio
   * modulo» — non e' stato cancellato: si e' SPOSTATO sul catalogo, e
   * `--verifica-scrivania` lo prova li'.
   */
  const el = document.createElement("div");
  el.className = "dck";

  const etichettaFiltro = document.createElement("span");
  etichettaFiltro.className = "dck__filtro";

  const t2 = document.createElement("div");
  t2.className = "dck__t2";
  const spia = document.createElement("span");
  spia.className = "dck__spia";
  const testoT2 = document.createElement("span");
  testoT2.textContent = "T2 inerte";
  t2.append(spia, testoT2);

  /* ⚠️ CINQUE FATTI CHE NON SI VEDONO DA NESSUNA PARTE, e la fascia era vuota
   * per il 91 % della sua larghezza.
   *
   * `DIVARIO-PREMIUM.md` §7 lo chiede da tempo: «riempirli con informazione che
   * gia' esiste e non mostriamo … sono tutti in state.snapshot e oggi finiscono
   * in un solo pannello». Il punto e' stato eseguito sulla BARRA, che infatti
   * sta al 55,8 % di inchiostro; il dock era rimasto al 2,0 % contro il 20
   * della soglia e il 22,8-26,2 % dei due riferimenti.
   *
   * Misurato prima di scegliere: `grep seccomp|gpu|trash_only|tts_provider` su
   * tutto `ui/src` non trova NIENTE fuori dal finto della galleria. Questi
   * cinque non duplicano nessun pannello, ed e' la ragione per cui sono questi
   * — §26.3 rifiuta due posti in cui la stessa verita' puo' divergere.
   *
   *   GPU, VRAM   la telemetria mostra cpu, ram, temp e disco. Non la GPU.
   *   SECCOMP     lo stato della sandbox. Oggi non lo dice nessuno.
   *   CESTINO     l'invariante 4, resa visibile invece che promessa.
   *   LAYOUT      dove vive lo stato della scrivania, e se e' integro.
   *
   * Restano fuori, dichiarati: `tts_provider` — la barra porta `STT` e mettere
   * `TTS` qui spezzerebbe una coppia su due strisce — e `quota.restanti`, che
   * il dettaglio di T2 gia' porta a destra.
   *
   * Sono campi di `state.snapshot`, che arriva UNA volta: restano fermi per
   * tutta la sessione, quindi non aggiungono nessuna deriva alla fixture. */
  const campi = document.createElement("div");
  campi.className = "dck__campi";
  const CAMPI = [
    { id: "gpu", et: "GPU", da: (m) => m.gpu?.driver ?? null },
    { id: "vram", et: "VRAM", da: (m) => gibi(m.gpu?.used_bytes, m.gpu?.total_bytes) },
    { id: "seccomp", et: "SECCOMP",
      da: (m) => (typeof m.core?.seccomp === "boolean" ? (m.core.seccomp ? "si" : "no") : null) },
    { id: "cestino", et: "CESTINO",
      da: (m) => (typeof m.settings?.fs?.trash_only === "boolean"
        ? (m.settings.fs.trash_only ? "solo" : "no") : null) },
    { id: "layout", et: "LAYOUT",
      da: (m) => (m.layout ? (m.layout.corrotto_in ? "corrotto"
        : m.layout.esiste ? "ok" : "assente") : null) },
    //: «client collegati» sta NOMINATO nell'elenco di DIVARIO-PREMIUM §7, ed
    //: era l'unica voce di quell'elenco che nessuna striscia mostrava: la barra
    //: porta gia' tool, uptime, byte sul socket, fase, PID e il provider STT.
    { id: "client", et: "CLIENT",
      da: (m) => (typeof m.ws?.clients === "number" ? String(m.ws.clients) : null) },
    //: La barra dice «LLM claude_code», che e' il BACKEND di T2. Quale modello
    //: gira T1 e' un altro fatto — invariante 15 — e non lo diceva nessuno.
    { id: "t1", et: "T1", da: (m) => m.settings?.llm?.t1_model ?? null },
    //: La sandbox del codice: se e' accesa, quanto puo' prendere. Oggi non
    //: compare da nessuna parte, ed e' una capacita', non una preferenza.
    { id: "codice", et: "CODICE",
      da: (m) => (typeof m.codice?.acceso === "boolean"
        ? (m.codice.acceso ? `${m.codice.memoria_mb} MiB` : "spento") : null) },
  ];
  const celle = new Map();
  for (const c of CAMPI) {
    const campo = document.createElement("div");
    campo.className = "dck__campo";
    campo.dataset.vuoto = "";
    const et = document.createElement("span");
    et.className = "dck__et";
    et.textContent = c.et;
    const vl = document.createElement("span");
    vl.className = "dck__vl";
    vl.textContent = "—";
    campo.append(et, vl);
    campi.appendChild(campo);
    celle.set(c.id, { campo, vl });
  }

  el.append(etichettaFiltro, campi, t2);
  ospite.appendChild(el);

  function scrivi(id, valore) {
    const cella = celle.get(id);
    if (!cella) return;
    cella.vl.textContent = valore ?? "—";
    if (valore == null) cella.campo.dataset.vuoto = "";
    else delete cella.campo.dataset.vuoto;
  }

  bus.su("state.snapshot", (m) => {
    for (const c of CAMPI) scrivi(c.id, c.da(m));
  });

  scrivania.osserva(({ filtro, aperti }) => {
    etichettaFiltro.textContent =
      (filtro ? `FILTRO ${String(filtro).padStart(2, "0")}` : "TUTTO") +
      ` · ${aperti.length} pannelli`;
  });

  bus.su("agent.mesh", (m) => {
    const nodo = (m.nodi ?? []).find((n) => n.id === "t2");
    const attivo = Boolean(nodo?.attivo);
    if (attivo) t2.dataset.attivo = "";
    else delete t2.dataset.attivo;
    // Il dettaglio del nodo dice quante sessioni e quante nella finestra: e'
    // il conto del Governor, non un'etichetta.
    testoT2.textContent = nodo
      ? `T2 ${nodo.stato}${nodo.dettaglio ? ` · ${nodo.dettaglio}` : ""}`
      : "T2 non collegato";
  });

  bus.suStato(({ stato }) => {
    if (stato === "connesso") return;
    delete t2.dataset.attivo;
    testoT2.textContent = "T2 non collegato";
    // Col core scollegato i campi non sono vecchi: sono ignoti. Si spengono,
    // come fa la barra.
    for (const c of CAMPI) scrivi(c.id, null);
  });

  return { el, altezza: () => el.getBoundingClientRect().height };
}
