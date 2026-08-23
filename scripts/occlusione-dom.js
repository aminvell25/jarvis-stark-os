/* La misura di OCCLUSIONE — `docs/PIANO-CORE-E-DENSITA.md` §5, turno 1.
 *
 * ⚠️ **Questo file non e' un modulo: e' UNA ESPRESSIONE**, da valutare dentro
 * la pagina viva. Non ha `import` ne' `export` apposta — chi lo usa lo legge
 * come testo e lo passa a `executeJavaScript` (Electron) o a `evaluate`
 * (Playwright). Ha un solo lettore oggi, `app/main.js`, e sta in un file
 * proprio per la stessa ragione per cui una costante sta in cima: perche' il
 * giorno che la misura cambia, cambi in un posto.
 *
 * ## Perche' esiste
 *
 * `scripts/densita.mjs` misura CIO' CHE SI VEDE e non sa che cosa e' coperto.
 * E' il motivo per cui il caldo della scrivania sta a 0,18 %: le cartelle
 * manila esistono — a riposo si vedono — e i pannelli ci stanno sopra. Una
 * metrica che conta i pixel accesi non distingue «non c'e'» da «c'e' e sta
 * sotto», e sono due difetti opposti: il primo si risolve costruendo, il
 * secondo spostando. Senza questa misura si costruisce per rimediare a una
 * sovrapposizione, che e' il modo piu' caro di sbagliare.
 *
 * ## Perche' `elementFromPoint` e non la geometria dei rettangoli
 *
 * Perche' «coperto» non e' una proprieta' dei rettangoli: e' il risultato
 * dell'ordine di pittura, degli strati, delle trasformazioni e dei ritagli.
 * Riscrivere qui la catena degli z-index vorrebbe dire duplicare il browser e
 * sbagliare in un caso su venti — e sarebbe una duplicazione MUTA, che risponde
 * con sicurezza anche quando ha torto. Il browser la domanda «chi sta in cima
 * qui?» sa gia' rispondersela.
 *
 * ⚠️ **Il limite, dichiarato**: `elementFromPoint` salta cio' che ha
 * `pointer-events: none`. Un elemento che copra visivamente senza raccogliere
 * il puntatore risulterebbe trasparente a questa misura. Sulla scrivania di
 * oggi non ce ne sono fra i pannelli — l'unico strato cosi' e' l'insegna
 * (`.sfd`), che sta SOTTO e non copre niente, e il contenitore delle icone
 * (`.ico-fondo`), i cui figli riprendono `auto`. Se un giorno un velo a schermo
 * intero passasse gli eventi, questa misura direbbe «scoperto» a torto: e'
 * scritto qui perche' chi lo aggiunge lo trovi.
 *
 * ## Le tre frazioni
 *
 * Sono le tre che §5 nomina, e sono frazioni, non giudizi. Il giudizio sta nel
 * documento di accettazione, dove qualcuno lo firma.
 */
(() => {
  //: Il passo del campionamento. 2 px e non 1: su 1536x843 sono 323 000 punti
  //: contro 1 295 000, la misura cambia sotto il decimo di punto percentuale e
  //: il costo si divide per quattro. Non e' una tolleranza — e' la risoluzione
  //: dichiarata della misura, e va scritta accanto al numero che produce.
  const PASSO = 2;

  //: Quanto di un elemento caldo deve sparire perche' si dica coperto. Meta'.
  //: Un'icona coperta al 40 % si legge ancora; al 60 % e' un angolo che spunta.
  const SOGLIA_COPERTO = 0.5;

  //: I punti con cui si giudica un elemento caldo: griglia fissa 8x8 dentro il
  //: suo riquadro, indipendente dalla sua dimensione. Un'icona da 55 px e una
  //: cartella da 200 devono essere giudicate con la stessa severita'.
  const GRIGLIA = 8;

  const s = window.__scrivania && window.__scrivania.scrivania;
  if (!s) {
    return { errore: "window.__scrivania.scrivania non c'e': questa misura vuole la scrivania vera, non la galleria" };
  }

  /* ── il protocollo di §5, verificato invece che sperato ─────────────────
     Ognuno dei cinque punti o e' un fatto che si legge, o non e' un vincolo. */
  const st = s.stato();
  const area = s.misura();                       // il pavimento: fra barra e dock
  const protocollo = {
    finestra: [window.innerWidth, window.innerHeight],
    /* ⚠️ Lo schermo NON si confronta con la finestra, e il primo giro di questa
       misura ci e' cascato: diceva «massimizzata: false» su una finestra
       massimizzata davvero. `screen.availWidth` risponde 1920 e `innerWidth`
       1536, che e' 1920 / 1,25 — il fattore di scala del display. Sono due
       unita' diverse, e il confronto fra le due e' una domanda malposta.
       Chi sa la risposta e' Electron: `finestra.isMaximized()`. La stampiglia
       `app/main.js` in `protocollo.massimizzata`, come fa con `scattiIdentici`.
       Qui restano i due numeri grezzi, che servono a leggere il resto. */
    schermo: [window.screen.availWidth, window.screen.availHeight],
    scala: window.devicePixelRatio,
    pavimento: area,
    /* ⚠️ §5.2 vuole l'insieme dei pannelli MISURATI, che non e' `stato().aperti`.
       `applicaScena` non chiude quelli fuori scena: li NASCONDE, e restano in
       `aperti`. Misurato: dopo un giro di `verifica:scrivania` questo campo
       diceva nove — browser, console, file, meteo, sorgente compresi — mentre
       a schermo ce n'erano quattro. Un protocollo che dichiara nove pannelli e
       ne fotografa quattro non e' un protocollo.
       I visibili si leggono piu' sotto dai riquadri, che sono la stessa cosa
       che la misura usa; qui resta il conteggio degli aperti come contesto.
       ⚠️ I due elenchi non hanno gli stessi nomi ed e' voluto: `aperti` porta
       gli id del registro (`telemetria`), i riquadri il nome del componente
       (`telemetry`). Sono due nomi veri della stessa cosa. */
    aperti: st.aperti.slice().sort(),
    scena: st.scena,                             // §5.3 — la scena
    filtro: st.filtro,                           // §5.3 — nessun filtro
    riposo: st.tuttoNascosto,                    // §5.3 — riposo escluso
    passo: PASSO,
    /* ⚠️ Quanti fotogrammi ha chiesto l'insegna da quando e' montata.
       E' il criterio dell'invariante 25 — «zero animazione ambientale» — reso
       un numero: un componente che si assesta e smette ne chiede una manciata,
       uno che gira sempre ne chiede sessanta al secondo. Alla stesura a nuvola
       questo campo non poteva esistere, perche' quel ciclo non finiva mai. */
    fotogrammiInsegna: window.__insegna ? window.__insegna.fotogrammi : null,
  };

  /* ── chi copre ───────────────────────────────────────────────────────── */
  const dentroPannello = (el) => !!(el && el.closest && el.closest(".winbox"));
  /* La cornice dell'ambiente: barra, dock, catalogo. Sta SOPRA i pannelli
     (--z-cornice), quindi copre anche lei — ma non e' la stessa cosa, perche'
     e' fissa e dichiarata mentre un pannello e' mobile. Contata a parte.

     ⚠️ `#scrivania` STESSO non e' cornice: e' il pavimento. E' un `<main>` a
     schermo intero, quindi `elementFromPoint` lo restituisce ovunque non ci sia
     nient'altro — e il primo giro di questa misura, che usava `closest`
     soltanto, ha risposto «cornice 43,3 % del pavimento» e «disco coperto dalla
     cornice al 100 %». Erano lo stesso numero letto al contrario: quel 43 % era
     pavimento NUDO, e il disco era completamente libero. Un difetto che
     rendeva impossibile la risposta giusta, non che la sbagliava di poco. */
  const CORNICE = "#scrivania > *";
  const dentroCornice = (el) => !!(el && el.closest && el.closest(CORNICE) && !dentroPannello(el));

  /** Che cosa c'e' in cima al punto: "pannello", "cornice", "fondo", "fuori". */
  function chiInCima(x, y) {
    const el = document.elementFromPoint(x, y);
    if (!el) return "fuori";
    if (dentroPannello(el)) return "pannello";
    if (dentroCornice(el)) return "cornice";
    return "fondo";
  }

  /* ── ① % del pavimento coperto da pannelli ──────────────────────────────
     Il denominatore e' l'area utile che la scrivania stessa dichiara — quella
     fra barra e dock — e non lo schermo: coprire la barra non e' coprire il
     pavimento, e usare lo schermo intero renderebbe il numero piu' piccolo
     senza che nulla sia migliorato. */
  const conta = { pannello: 0, cornice: 0, fondo: 0, fuori: 0 };
  let punti = 0;
  for (let y = area.alto + PASSO / 2; y < area.alto + area.altezza; y += PASSO) {
    for (let x = area.sinistra + PASSO / 2; x < area.sinistra + area.larghezza; x += PASSO) {
      conta[chiInCima(x, y)]++;
      punti++;
    }
  }
  const pavimento = {
    punti,
    copertoDaPannelli: (100 * conta.pannello) / punti,
    copertoDallaCornice: (100 * conta.cornice) / punti,
    libero: (100 * conta.fondo) / punti,
  };

  /* ── ② % degli elementi caldi coperti ───────────────────────────────────
     «Conteggio sull'albero, non sui pixel», dice §5: si contano gli OGGETTI,
     perche' la domanda e' «quante cartelle non si vedono», non «quanta area
     calda manca». Le due risposte divergono e la seconda ce l'ha gia'
     `densita.mjs`.

     Caldo e' la stessa definizione della densita' — r > b + 15 — e non una
     lista di classi: una lista invecchia in silenzio il giorno che qualcuno
     aggiunge un elemento manila con un nome nuovo. Vale il colore dipinto
     davvero, fondo o testo che sia. */
  function caldo(c) {
    const m = /^rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?/.exec(c || "");
    if (!m) return false;
    if (m[4] !== undefined && parseFloat(m[4]) === 0) return false;
    return +m[1] > +m[3] + 15;
  }
  const haTestoProprio = (el) =>
    [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim() !== "");
  /* ⚠️ IL TERZO MODO DI DIPINGERE, e la prima stesura lo aveva dimenticato.
     Un glifo SVG non ha fondo e non ha testo proprio: ha `fill`. La misura
     rispondeva «zero elementi caldi» su una scrivania dove una cartella manila
     si vedeva a occhio nudo — l'ho trovata GUARDANDO lo scatto, non leggendo il
     codice, ed e' il motivo per cui §11.7 mette lo sguardo dopo la misura e non
     al posto suo.
     `segni.js` dipinge ogni glifo con fill="currentColor" apposta, perche' un
     segno non ha un colore proprio ma quello del posto in cui sta. Il valore
     risolto lo sa solo getComputedStyle. */
  const dipintoInSvg = (el, c) =>
    el.namespaceURI === "http://www.w3.org/2000/svg" && c.fill && c.fill !== "none";

  const caldi = [];
  const antenatiCaldi = new WeakSet();
  for (const el of document.querySelectorAll("body *")) {
    const c = getComputedStyle(el);
    if (c.display === "none" || c.visibility === "hidden" || +c.opacity === 0) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) continue;
    const suo = caldo(c.backgroundColor)
      || (haTestoProprio(el) && caldo(c.color))
      || (dipintoInSvg(el, c) && caldo(c.fill));
    if (!suo) continue;
    /* Un solo oggetto per nido: l'etichetta calda dentro un'icona calda e' la
       stessa cosa vista due volte, e contarle entrambe farebbe salire il totale
       ogni volta che qualcuno aggiunge uno `<span>`. */
    if (el.parentElement && antenatiCaldi.has(el.parentElement)) {
      antenatiCaldi.add(el);
      continue;
    }
    antenatiCaldi.add(el);
    caldi.push({ el, r, dentroPannello: dentroPannello(el) });
  }

  const suPavimento = [];
  for (const c of caldi) {
    if (c.dentroPannello) continue;             // sta DENTRO un pannello: non e' coperto da lui
    let coperti = 0, visti = 0;
    for (let i = 0; i < GRIGLIA; i++) {
      for (let j = 0; j < GRIGLIA; j++) {
        const x = c.r.left + (c.r.width * (i + 0.5)) / GRIGLIA;
        const y = c.r.top + (c.r.height * (j + 0.5)) / GRIGLIA;
        const chi = chiInCima(x, y);
        if (chi === "fuori") continue;
        visti++;
        if (chi === "pannello" || chi === "cornice") coperti++;
      }
    }
    const frazione = visti ? coperti / visti : 1;
    suPavimento.push({
      chi: c.el.className && typeof c.el.className === "string"
        ? "." + c.el.className.trim().split(/\s+/).join(".")
        : c.el.tagName.toLowerCase(),
      testo: (c.el.textContent || "").trim().slice(0, 24),
      largo: Math.round(c.r.width),
      alto: Math.round(c.r.height),
      coperto: frazione,
    });
  }
  suPavimento.sort((a, b) => b.coperto - a.coperto);
  const nascosti = suPavimento.filter((e) => e.coperto >= SOGLIA_COPERTO);

  const eleCaldi = {
    sulPavimento: suPavimento.length,
    dentroPannelli: caldi.filter((c) => c.dentroPannello).length,
    coperti: nascosti.length,
    percentuale: suPavimento.length ? (100 * nascosti.length) / suPavimento.length : 0,
    soglia: SOGLIA_COPERTO,
    elenco: suPavimento.slice(0, 12),
    /* ⚠️ Anche quelli DENTRO i pannelli, che non entrano nella frazione.
       Servono a distinguere due zeri che si scrivono uguale: «nessun elemento
       caldo e' coperto» e «il predicato non ne trova nessuno». Senza questo
       elenco la seconda si legge come la prima, ed e' il modo classico in cui
       una metrica passa sempre. */
    dentroPannelliElenco: caldi.filter((c) => c.dentroPannello).slice(0, 12).map((c) => ({
      chi: c.el.className && typeof c.el.className === "string"
        ? "." + c.el.className.trim().split(/\s+/).join(".")
        : c.el.tagName.toLowerCase(),
      testo: (c.el.textContent || "").trim().slice(0, 24),
      largo: Math.round(c.r.width), alto: Math.round(c.r.height),
    })),
    /* ⚠️ IL LIMITE, dichiarato: questa misura conta ELEMENTI, e l'arco ambra
       dell'insegna e' dipinto su un canvas — un elemento solo, di fondo
       trasparente, che questo predicato non vede. §5 chiede il conteggio
       sull'albero e l'albero non sa che cosa c'e' dentro una tela: il caldo
       dipinto lo misura `densita.mjs` sui pixel, e le due misure vanno lette
       insieme come gia' densita' e traboccamento. */
    canvasNonContati: document.querySelectorAll("canvas").length,
  };

  /* ── ②bis le icone libere, calde o no ───────────────────────────────────
     §5 dava per scontato che gli elementi caldi sul pavimento fossero le
     cartelle manila di §26.5. Non lo sono: le icone libere si dipingono a
     `--icona`, che e' freddo, e il predicato del caldo non le vede — non per un
     difetto, perche' calde non sono. La domanda del turno 4 pero' e' la loro,
     non quella del colore: «quante icone del piano sono sotto un pannello?».
     Si misura sulla classe, che qui e' lecito perche' `.ico` e' l'oggetto
     stesso di §26.5 e non un modo per riconoscerne il colore. */
  const icone = [];
  for (const el of document.querySelectorAll(".ico")) {
    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) continue;
    let coperti = 0, visti = 0;
    for (let i = 0; i < GRIGLIA; i++) {
      for (let j = 0; j < GRIGLIA; j++) {
        const chi = chiInCima(r.left + (r.width * (i + 0.5)) / GRIGLIA,
                              r.top + (r.height * (j + 0.5)) / GRIGLIA);
        if (chi === "fuori") continue;
        visti++;
        if (chi === "pannello" || chi === "cornice") coperti++;
      }
    }
    icone.push({ nome: (el.textContent || "").trim().slice(0, 24),
                 coperto: visti ? coperti / visti : 1 });
  }
  icone.sort((a, b) => b.coperto - a.coperto);
  const libere = {
    totale: icone.length,
    coperte: icone.filter((i) => i.coperto >= SOGLIA_COPERTO).length,
    percentuale: icone.length
      ? (100 * icone.filter((i) => i.coperto >= SOGLIA_COPERTO).length) / icone.length : 0,
    elenco: icone.slice(0, 12),
  };

  /* ── ③ % del disco del nucleo coperto ───────────────────────────────────
     Il disco non si ricalcola qui: lo DICHIARA chi lo disegna, in
     `data-disco` su `.sfd` (centro x, centro y, raggio, in pixel CSS relativi
     al proprio riquadro). Ricopiare AMPIEZZA in questo file vorrebbe dire
     avere il raggio scritto due volte, e il giorno che il nucleo cambia forma
     questa misura risponderebbe con sicurezza sul disco di ieri. */
  const sfd = document.querySelector(".sfd");
  let disco = null;
  if (sfd && sfd.dataset.disco) {
    const box = sfd.getBoundingClientRect();
    const [dx, dy, rr] = sfd.dataset.disco.split(",").map(Number);
    const cx = box.left + dx, cy = box.top + dy;
    const d2 = { pannello: 0, cornice: 0, fondo: 0, fuori: 0 };
    let dentro = 0;
    for (let y = cy - rr; y <= cy + rr; y += PASSO) {
      for (let x = cx - rr; x <= cx + rr; x += PASSO) {
        if ((x - cx) ** 2 + (y - cy) ** 2 > rr * rr) continue;
        d2[chiInCima(x, y)]++;
        dentro++;
      }
    }
    disco = {
      centro: [Math.round(cx), Math.round(cy)],
      raggio: rr,
      //: Quanto pesa il disco sul pavimento: serve a leggere le altre due
      //: frazioni. Un disco che copre il 42 % del pavimento e un pavimento
      //: coperto al 42 % dai pannelli non possono essere entrambi liberi.
      quotaDelPavimento: (100 * Math.PI * rr * rr) / (area.larghezza * area.altezza),
      punti: dentro,
      copertoDaPannelli: (100 * d2.pannello) / dentro,
      copertoDallaCornice: (100 * d2.cornice) / dentro,
      libero: (100 * d2.fondo) / dentro,
    };
  }

  /* ── ③bis quanto e' grande il BUCO che la scena tiene aperto ─────────────
     Non e' una curiosita': e' il tetto vero del nucleo.
     La scena «avvio» lascia il centro libero apposta (§25, uscita B), e il
     nucleo che ci sta dentro oggi e' la nuvola di `sfondo.js`, Ø326. Ma §25
     aveva misurato il nucleo di `rings.js`, Ø502 — 42 % del pavimento contro
     6,9 %. Se il buco e' piu' grande di cio' che lo riempie, la scena sta
     tenendo aperto uno spazio che nessuno usa, e il conto non torna a nessuno
     dei due: ne' a chi misura la densita' (pavimento nudo), ne' a chi misura la
     presenza (nucleo invisibile).
     Si cerca il raggio massimo, attorno allo stesso centro, che nessun pannello
     tocca: si cresce di 4 px e si prova un anello di 180 punti. */
  let buco = null;
  if (sfd && sfd.dataset.disco) {
    const box = sfd.getBoundingClientRect();
    const [dx, dy] = sfd.dataset.disco.split(",").map(Number);
    const cx = box.left + dx, cy = box.top + dy;
    let r = 0;
    cresci: for (let prova = 4; prova < Math.max(window.innerWidth, window.innerHeight); prova += 4) {
      for (let k = 0; k < 180; k++) {
        const a = (k * Math.PI) / 90;
        const chi = chiInCima(cx + prova * Math.cos(a), cy + prova * Math.sin(a));
        if (chi !== "fondo") break cresci;
      }
      r = prova;
    }
    buco = {
      raggio: r,
      diametro: 2 * r,
      quotaDelPavimento: (100 * Math.PI * r * r) / (area.larghezza * area.altezza),
    };
  }

  /* I riquadri dei pannelli, in pixel CSS — che sono anche i pixel del PNG,
     perche' `capturePage` cattura alla dimensione della finestra.
     Non servono a questa misura: servono a `densita.mjs`, che ha i pixel e non
     ha il layout, per dire DOVE stanno i pixel che cambiano fra due scatti. Un
     conteggio dice quanto si muove; solo il layout dice se e' la nuvola. */
  const rettangoli = [...document.querySelectorAll(".winbox")]
    .filter((w) => getComputedStyle(w).display !== "none")
    .map((w) => {
      const r = w.getBoundingClientRect();
      /* Il nome lo mette `desk/cornice.js` in `data-pannello`. `.wb-title` non
         serve: i nostri pannelli hanno la propria testa e quella di WinBox
         resta vuota — cercarla li' rispondeva «(senza titolo)» per tutti. */
      const t = w.querySelector(".wb-title");
      return { chi: w.dataset.pannello || (t && t.textContent.trim()) || "(senza titolo)",
               r: [r.left, r.top, r.width, r.height].map(Math.round) };
    })
    .filter((p) => p.r[2] > 0 && p.r[3] > 0);

  return { protocollo, pavimento, caldi: eleCaldi, icone: libere, disco, buco, rettangoli };
})()
