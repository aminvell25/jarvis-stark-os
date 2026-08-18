/* La finestra di conferma nella galleria.
 *
 * Importa il componente VERO e gli da' una richiesta con la FORMA di una
 * richiesta vera: percorsi assoluti gia' risolti, un piano di organize_folder
 * piu' lungo di quanto si elenchi, un id esadecimale. E' l'eccezione che
 * §11.9 concede alla sola galleria.
 */

import { crea, css as cssConferma, meta as metaConferma } from "../../windows/confirm.js";

export const meta = { nome: "confirm", versione: metaConferma.versione };
export const css = cssConferma;

const BASE = "/home/aminvell/Scaricati";
const FILE = [
  ["fattura-2026-08.pdf", "Documenti"], ["IMG_20260817_1042.jpg", "Immagini"],
  ["riunione-agosto.m4a", "Audio"], ["backup-progetti.tar.zst", "Archivi"],
  ["telemetry-export.csv", "Fogli"], ["staffa-v3.stl", "Modelli"],
  ["appunti.md", "Documenti"], ["clip-demo.mp4", "Video"],
  ["setup.sh", "Codice"], ["schema.png", "Immagini"],
  ["contratto-firmato.pdf", "Documenti"], ["voce-nota-2.opus", "Audio"],
  ["dump.sql", "Altro"], ["logo-vettoriale.svg", "Immagini"],
  ["preventivo.xlsx", "Fogli"],
];

export async function monta(ospite) {
  ospite.style.width = "720px";
  ospite.style.height = "420px";
  const finestra = crea(ospite, { rispondi: () => {} });
  finestra.mostra({
    id: "9f3ac1de52b74a08",
    tool: "organize_folder",
    riepilogo: `${FILE.length} file in 7 cartelle: Altro, Archivi, Audio, Codice, Documenti, Fogli, Immagini, Modelli, Video`,
    operazioni: FILE.map(([nome, cat]) => ({
      tipo: "move",
      sorgente: `${BASE}/${nome}`,
      destinazione: `${BASE}/${cat}/${nome}`,
    })),
  });
}
