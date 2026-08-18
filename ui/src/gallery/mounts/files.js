/* Il pannello file nella galleria, col componente vero e dati dalla FORMA di
 * dati veri: nomi plausibili, dimensioni non tonde, categorie che il core
 * calcola davvero (§11.9, eccezione della galleria). */

import { crea, css as cssPannello, meta as metaPannello } from "../../panels/files.js";

export const meta = { nome: "files", versione: metaPannello.versione };
export const css = cssPannello;

const VOCI = [
  ["Documenti", "dir", null, null], ["Immagini", "dir", null, null],
  ["Modelli", "dir", null, null],
  ["fattura-2026-08.pdf", "file", 284_713, "Documenti"],
  ["IMG_20260817_1042.jpg", "file", 3_918_442, "Immagini"],
  ["riunione-agosto.m4a", "file", 18_226_101, "Audio"],
  ["backup-progetti.tar.zst", "file", 941_002_337, "Archivi"],
  ["telemetry-export.csv", "file", 72_884, "Fogli"],
  ["staffa-v3.stl", "file", 2_104_620, "Modelli"],
  ["setup.sh", "file", 1_842, "Codice"],
  ["dump.sql", "file", 15_338_291, "Altro"],
  ["contratto-firmato.pdf", "file", 1_204_886, "Documenti"],
  ["voce-nota-2.opus", "file", 402_119, "Audio"],
  ["logo-vettoriale.svg", "file", 14_772, "Immagini"],
  ["preventivo.xlsx", "file", 48_902, "Fogli"],
  ["clip-demo.mp4", "file", 128_774_310, "Video"],
  ["schema.png", "file", 221_408, "Immagini"],
  ["appunti.md", "file", 6_331, "Documenti"],
  ["driver-stampante.deb", "file", 33_118_204, "Altro"],
  ["telecamera-firmware.bin", "file", 8_388_608, "Altro"],
  ["corso-python-lezione-04.mkv", "file", 742_009_115, "Video"],
  ["estratto-conto-luglio.pdf", "file", 190_442, "Documenti"],
  ["mesh-riparata.obj", "file", 5_772_140, "Modelli"],
  ["curriculum.odt", "file", 38_115, "Documenti"],
  ["playlist-lavoro.m3u", "file", 1_204, "Altro"],
];

export async function monta(ospite) {
  ospite.style.width = "720px";
  ospite.style.height = "420px";
  crea(ospite).aggiorna({
    topic: "fs.list",
    path: "/home/aminvell/Scaricati",
    totale: VOCI.length,
    voci: VOCI.map(([name, type, size, categoria]) => ({ name, type, size, categoria })),
  });
}
