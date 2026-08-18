/* Il pannello telemetria dentro la galleria.
 *
 * Non re-implementa nulla: importa il componente VERO e gli da' una sorgente
 * finta. E' l'unica eccezione che §11.9 concede — dati finti per costruzione,
 * ma con la FORMA di dati veri: percentuali non tonde, temperature plausibili,
 * nomi di processo realistici, timestamp coerenti.
 *
 * Se questo file disegnasse un'imitazione in HTML, il ciclo §11.7 giudicherebbe
 * un componente diverso da quello che gira in Electron.
 */

import { crea, css as cssPannello, meta as metaPannello } from "../../panels/telemetry.js";

export const meta = { nome: "telemetry", versione: metaPannello.versione };
export const css = cssPannello;

const NOMI = ["gnome-shell", "electron", "python3", "claude-desktop", "pipewire"];

export async function monta(ospite) {
  // Il pannello riempie chi lo ospita: nella galleria la cella dichiara la
  // dimensione, in Electron la dichiara WinBox. Stesso componente.
  ospite.style.width = "720px";
  ospite.style.height = "420px";
  const pannello = crea(ospite);

  // Una serie con la forma di una serie vera: passeggiata casuale attorno a
  // valori plausibili, non una sinusoide e non numeri tondi.
  let cpu = 18.3, ram = 52.7, t = Math.floor(Date.now() / 1000) - 120;
  for (let i = 0; i < 90; i++) {
    cpu = Math.min(97, Math.max(2, cpu + (Math.sin(i / 7) * 6) + (i % 11) - 5));
    ram = Math.min(96, Math.max(30, ram + Math.sin(i / 13) * 1.4));
    t += 1;
    pannello.aggiorna({
      topic: "telemetry",
      ts: t,
      cpu_percent: Number(cpu.toFixed(1)),
      ram_percent: Number(ram.toFixed(1)),
      ram_available_bytes: Math.round((100 - ram) / 100 * 22.6 * 2 ** 30),
      package_temp_c: Number((41.6 + Math.sin(i / 9) * 3.2).toFixed(2)),
      top3: NOMI.slice(0, 3).map((name, k) => ({
        pid: 1200 + k * 37,
        name,
        cpu: Number((cpu / (k + 1.4)).toFixed(1)),
      })),
    });
  }
}
