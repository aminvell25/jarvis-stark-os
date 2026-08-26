"""TTS primario: Deepgram **Aura-2** — SPEC §7.4.

⚠️ **§7.4 lo chiamava «Flux», e Flux non e' un TTS.** Al primo turno con una
chiave vera l'API ha risposto:

    Only flux models are supported on the `/v2/speak` endpoint.
    Please use the `/v1/speak` endpoint for Aura text-to-speech requests.

E il catalogo lo conferma: `GET /v1/models` restituisce **solo** voci `aura-*`
fra i TTS, nessuna `flux`. Flux e' il modello di **riconoscimento** (vedi
`stt_deepgram.py`), e il nome era finito nel posto sbagliato — in un file che
non aveva mai girato, quindi nessuno poteva accorgersene.

**`per_enunciato = False`, ed e' il punto di §7.4.** Flux accetta i token
direttamente e determina i confini internamente: metterci davanti il chunker
**aggiunge solo latenza**. La pipeline lo legge da questo attributo invece di
ricordarselo.

`interrupt()` riporta `text_spoken` — **cio' che l'utente ha effettivamente
udito**. Va conservato: senza, JARVIS crede di aver detto una frase che nessuno
ha sentito (§7.4).
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from urllib.parse import urlencode

import structlog

from core.providers.base import AudioChunk

log = structlog.get_logger(__name__)

#: `/v1/speak` per le voci Aura. `/v2/speak` serve i modelli Flux, che
#: fra i TTS non esistono — misurato interrogando il catalogo.
ENDPOINT = "wss://api.deepgram.com/v1/speak"

#: Quanto si aspetta un messaggio da Aura prima di chiudere il turno.
#: Il primo suono misurato su questa rete sta fra 3,6 e 14,0 s, quindi
#: venti secondi sono «il server tace», non «il server e' lento».
TETTO_RECV_S = 20.0


#: ⚠️ **Era `aura-2-thalia-en`, una voce INGLESE**, e `costruisci_tts` non la
#: sovrascriveva: il giorno in cui e' comparsa una chiave Deepgram, JARVIS ha
#: cominciato a leggere italiano con un accento inglese. Il difetto era
#: invisibile finche' la chiave mancava, perche' questo file non girava.
#:
#: `elio` scelto fra le nove voci italiane che l'API dichiara, per i tratti che
#: Deepgram le attribuisce — *calm, professional, smooth, trustworthy* — che
#: sono le tre parole con cui §5.7 descrive JARVIS. Le altre maschili sono
#: `flavio` (deep, confident), `cesare` (clear, knowledgeable) e `dionisio`
#: (melodic, positive): si cambiano da `settings.toml`, non da qui.
VOCE_DEFAULT = "aura-2-elio-it"


class DeepgramTTS:
    name = "deepgram"
    per_enunciato = False          # §7.4: token diretti, niente chunker

    def __init__(self, api_key: str, sample_rate: int = 16_000,
                 voce: str = VOCE_DEFAULT) -> None:
        self._key = api_key
        self._sample_rate = sample_rate
        self._voce = voce
        self._ws = None
        self.text_spoken: str = ""

    def url(self) -> str:
        return f"{ENDPOINT}?{urlencode({'model': self._voce, 'encoding': 'linear16', 'sample_rate': str(self._sample_rate)})}"

    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Token {self._key}"}

    async def stream(self, text: AsyncIterator[str]) -> AsyncIterator[AudioChunk]:
        import asyncio

        from websockets.asyncio.client import connect

        async with connect(self.url(), additional_headers=self.headers()) as ws:
            self._ws = ws

            async def invia() -> None:
                async for tok in text:
                    # I token uno per uno, senza aggregare: Aura accetta testo
                    # parziale e decide da se' i confini, quindi il chunker
                    # davanti aggiungerebbe solo latenza (§7.4).
                    await ws.send(json.dumps({"type": "Speak", "text": tok}))
                await ws.send(json.dumps({"type": "Flush"}))

            compito = asyncio.create_task(invia())
            try:
                while True:
                    # ⚠️ **Con un tetto, e non e' prudenza generica.**
                    #
                    # `async for msg in ws` finisce solo quando il socket si
                    # chiude, e Aura non lo chiude mai da sola. Qualunque
                    # silenzio del server — rete, quota, un evento che non
                    # arriva — teneva appeso `parla()`, e con lui **il ciclo
                    # principale**, che aspetta il turno dentro
                    # `async for blocco in dal_microfono(...)`. Il microfono
                    # restava aperto e sordo per il resto della sessione.
                    #
                    # Un turno perso e' un turno perso; una sessione muta e'
                    # un'altra cosa.
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=TETTO_RECV_S)
                    except asyncio.TimeoutError:
                        log.error("tts_muto", secondi=TETTO_RECV_S,
                                  conseguenza="turno chiuso, la voce resta viva")
                        break
                    if isinstance(msg, bytes):
                        yield AudioChunk(pcm=msg, sample_rate=self._sample_rate)
                    else:
                        e = json.loads(msg)
                        tipo = e.get("type")
                        if tipo == "Cleared":
                            # ⚠️ **Qui il ciclo non usciva.** `interrupt()`
                            # manda `Clear`, il server risponde `Cleared` — e
                            # questo ramo registrava `text_spoken` e
                            # **continuava ad aspettare**. Il barge-in
                            # zittiva l'altoparlante e lasciava appesa la
                            # generazione: misurato dal vivo il 26 agosto,
                            # `barge_in` alle 21:02:19 e poi piu' niente.
                            #
                            # `Cleared` vuol dire che l'enunciato e' finito.
                            if t := e.get("text_spoken"):
                                self.text_spoken = t
                            else:
                                # ⚠️ Misurato dal vivo: il `Cleared` di Aura
                                # NON porta `text_spoken`, e la cornice di
                                # §7.4 e' ricaduta sul limite superiore («al
                                # piu' questo») invece che sulla misura. Il
                                # ramo `misurato=True` resta non verificato.
                                # Questa riga dice come si chiama davvero il
                                # campo, alla prossima interruzione.
                                log.info("cleared_senza_testo",
                                         campi=sorted(e.keys()))
                            break
                        if tipo == "Flushed":
                            # ⚠️ **Il ciclo non finiva mai.** Dopo il `Flush`
                            # Aura manda l'audio e poi `Flushed`, ma **non
                            # chiude il socket**: `async for msg in ws` restava
                            # appeso per sempre, e con lui il turno. Terzo
                            # difetto in un file che non aveva mai girato, e i
                            # tre erano invisibili per la stessa ragione.
                            break
            finally:
                compito.cancel()
                self._ws = None

    async def flush(self) -> None:
        if self._ws is not None:
            await self._ws.send(json.dumps({"type": "Flush"}))

    async def interrupt(self) -> None:
        """Barge-in. La risposta porta `text_spoken`: cio' che e' stato UDITO."""
        if self._ws is not None:
            await self._ws.send(json.dumps({"type": "Clear"}))

    async def aclose(self) -> None:
        if self._ws is not None:
            await self._ws.close()
            self._ws = None
