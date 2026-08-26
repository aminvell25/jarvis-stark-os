/* Righe VERE del diario, registrate dalla sessione vocale del 26 agosto 2026.
 *
 * Non sono inventate e non hanno bisogno della concessione di §11.9: le ha
 * dette qualcuno, e la trascrizione sporca — «duedici», «il cero e' blu» — e'
 * quella che Deepgram ha davvero prodotto. Un fixture ripulito mostrerebbe un
 * pannello che non esiste.
 *
 * Lo stato scelto contiene le tre cose che rendono il registro utile: una
 * risposta INTERROTTA dal barge-in, un testo detto STIMATO (il TTS locale non
 * riporta cio' che ha davvero pronunciato), e un intento SENZA DESTINAZIONE.
 */

const T = 1787772000;

export const RIGHE = [
  { topic: "agent.diario", ts: T + 0,  flusso: "dialogo", chi: "signore",
    testo: "Quando fa duedici per sette?", secondi: 2.56 },
  { topic: "agent.diario", ts: T + 6,  flusso: "dialogo", chi: "jarvis",
    testo: "Ottantaquattro, Signore.", misurato: true, secondi: 1.9 },
  { topic: "agent.diario", ts: T + 31, flusso: "dialogo", chi: "signore",
    testo: "Secondo me il sole gira intorno alla terra.", secondi: 4.22 },
  { topic: "agent.diario", ts: T + 39, flusso: "dialogo", chi: "jarvis",
    testo: "È il contrario, Signore. La Terra orbita attorno al Sole.",
    misurato: true, secondi: 3.4 },
  { topic: "agent.diario", ts: T + 68, flusso: "dialogo", chi: "signore",
    testo: "Spiegami perché il cero è blu.", secondi: 2.94 },
  { topic: "agent.diario", ts: T + 74, flusso: "dialogo", chi: "jarvis",
    testo: "Intende il cielo, Signore? La luce blu ha una lunghezza d'onda più corta",
    interrotto: true, misurato: false, secondi: 5.1 },

  { topic: "agent.diario", ts: T + 6,  flusso: "azione", intento: "brief_me",
    ok: true, strada: "core", da: "voce" },
  { topic: "agent.diario", ts: T + 20, flusso: "azione", intento: "open_panel",
    args: { panel: "telemetria" }, ok: true, strada: "ui", da: "voce" },
  { topic: "agent.diario", ts: T + 45, flusso: "azione", intento: "set_volume",
    args: { level: 40 }, ok: true, strada: "tool", da: "voce" },
  { topic: "agent.diario", ts: T + 52, flusso: "azione", intento: "needs_attention",
    ok: false, strada: "nessuna", da: "voce",
    errore: "T2 non composto: nessun modello per i meta-comandi" },
];
