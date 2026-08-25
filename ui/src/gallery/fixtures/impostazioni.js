/* GENERATO da scripts/fixture_impostazioni.py — non modificare a mano.
 *
 * Dal TEMPLATE `config/settings.toml`, non dal file vivo: quello porta
 * i percorsi della home, e una fixture committata li pubblicherebbe.
 * Le radici restano scritte come nel file (`~/JARVIS`) e non risolte.
 */

export const IMPOSTAZIONI = {
  "modificabili": {
    "voice.stt_provider": "deepgram",
    "voice.tts_provider": "deepgram",
    "voice.fallback_on_error": true,
    "voice.fallback_stt": "local",
    "voice.fallback_tts": "local",
    "voice.deepgram_stt_model": "flux-general-multi",
    "voice.eot_threshold": 0.7,
    "voice.eager_eot": false,
    "voice.whisper_model": "base",
    "voice.kokoro_voice": "bm_george",
    "voice.wake.confirm_tone_ms": 80,
    "voice.wake.log_triggers": true,
    "llm.backend": "claude_code",
    "llm.t1_model": "claude-haiku-4-5-20251001",
    "llm.t2_model": "sonnet",
    "llm.max_concurrent_t2": 2,
    "llm.max_t2_spawns_per_hour": 15,
    "vision.scope": "app",
    "vision.engine": "tesseract",
    "news.enabled": true,
    "news.max_interruptions_per_hour": 3,
    "news.topic_ttl_minutes": 30,
    "ui.target_fps": 60,
    "ui.grid_px": 110,
    "ui.gap_px": 8,
    "ui.scena_iniziale": "avvio",
    "meteo.enabled": true,
    "meteo.nome": "",
    "meteo.units": "celsius",
    "code.tmpfs_mb": 64,
    "code.memory_mb": 512,
    "code.cpu_percent": 50,
    "code.max_output_kb": 64,
    "code.max_timeout_s": 10.0,
    "code.max_concurrent": 2
  },
  "bloccate": {
    "code.enabled": false,
    "fs.allowed_roots": [
      "~/JARVIS",
      "~/Documenti",
      "~/Scaricati"
    ],
    "fs.trash_only": true,
    "vision.enabled": false,
    "voice.enabled": false
  },
  "file": "~/.config/jarvis-os/settings.toml"
};
