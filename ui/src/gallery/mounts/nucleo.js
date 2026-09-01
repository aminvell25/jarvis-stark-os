/* Il nucleo dentro la galleria — il ciclo §11.7 su un componente di FONDO.
 *
 * ⚠️ Non c'era, e avrebbe dovuto esserci. Il nucleo è l'oggetto più grande a
 * schermo e l'unico che nessuno auditasse: `desk/sfondo.js` non aveva un mount,
 * quindi non stava in `COMPONENTI` di `eval_visual.py` e l'audit dei token non
 * ci passava sopra. Si verificava solo con `npm run nucleo`, che scatta
 * fotografie ma non legge il CSSOM.
 */

import { crea as creaNucleo, css as cssNucleo, meta as metaNucleo } from "../../desk/sfondo.js";

export const meta = { nome: "nucleo", versione: metaNucleo.versione };
export const css = cssNucleo + `
/* La galleria dà al componente un riquadro; il nucleo si aspetta la scrivania,
   che ha un pavimento. Qui glielo si mette, ed è un token: senza, il disco
   starebbe su un fondo che non è quello vero e ogni misura di contrasto direbbe
   un altro numero. */
.gal-nucleo {
  position: relative;
  width: 100%;
  height: 100%;
  background: var(--bg-void);
  overflow: hidden;
}
`;

export async function monta(ospite) {
  /* ⚠️ 850 e non 560, e la ragione è che si giudica a occhio.
     Il nucleo si dimensiona sul lato minore della scrivania: sulla finestra di
     misura (1536x843) fa Ø326. Un riquadro da 560 ne dà Ø216, cioè il 66 % —
     e a quella scala il testo, che è in pixel veri, sembra enorme rispetto al
     disco. Giudicare la composizione lì porta a stringere cose che nella
     finestra vera stanno bene: è successo, e l'ho corretto due volte prima di
     accorgermene.
     850 x 0,386 = 328: la stessa proporzione della scrivania vera. */
  ospite.style.width = "850px";
  ospite.style.height = "850px";
  const scatola = document.createElement("div");
  scatola.className = "gal-nucleo";
  ospite.appendChild(scatola);
  const nucleo = creaNucleo(scatola);
  scatola.appendChild(nucleo.radice);

  /* ⚠️ La FORMA di uno stato vero — §11.9, l'unica eccezione concessa alla
     regola dei dati veri, e vale nella galleria e in nessun altro posto.
     I numeri sono plausibili e dichiarati tali; in finestra vera arrivano dal
     bus, ed è lì che si verifica che ci arrivino. */
  nucleo.aggiorna({ topic: "state.snapshot", fase: 9,
                    agente: { livello: "nominal" }, core_vivo: true });
  nucleo.aggiorna({ topic: "agent.mesh", livello: "nominal", nodi: [
    { id: "t0", attivo: false }, { id: "t1", attivo: true },
    { id: "t2", attivo: false }, { id: "sub-1", tipo: "subagent", attivo: false },
  ] });
  nucleo.aggiorna({ topic: "telemetry",
                    cpu_percent: 12.4, ram_percent: 38.1, package_temp_c: 54.0 });

  window.__nucleoGalleria = nucleo;
}
