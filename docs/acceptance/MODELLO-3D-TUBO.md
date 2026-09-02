# Il pilastro 3D — `tubo_spline`, la fetta 2

**Data**: 3 settembre 2026 · **Riferimento**: ADR-014
(`docs/PERIMETRO-E-DECISIONI.md`), `docs/SPEC.md` §17.1-17.3 e §17.4 ②,
invarianti 22, 34, §11.10 regole 2, 3, 4, 5 e 7 ·
**Rollback**: il commit precedente · **Test**: 2174 → **2203** passati
(2228 raccolti, 25 saltati, 29 nuovi)

---

## Che cosa aggiunge, e perché era la fetta successiva

`estrusione_45` aveva **conteggi chiusi**: 32 vertici e 64 triangoli, sempre.
Il tubo no — la sua densità viene dalla curvatura (§11.10 regola 2) — ed è la
ragione per cui questa fetta era la seconda e non un'altra forma qualunque:
è quella che obbliga a scrivere la regola della densità **due volte**, in
Python nel core e in JavaScript nel renderer, e a inchiodare le due copie.

§17.4 ② prescriveva `THREE.CatmullRomCurve3`, che §11.10 regola 5 vieta
insieme a tutte le geometrie standard. La matematica resta e cambia chi la
esegue: la curva è scritta per esteso nella forma di Barry e Goldman.

## Le tre cose che questa fetta ha dovuto risolvere

### ① Il gemello, e perché non si può cancellarne uno

`core/model3d/parametrico.py::segmenti_per` è
`ParametricComponent.segmentsFor()` riga per riga. Non è una duplicazione da
togliere: §17.2 mette il generatore nel core e il componente che lo incassa
nel renderer, e la regola della densità è dell'uno e dell'altro. La cura è
renderle **verificabili insieme** —
`tests/test_model3d.py::TestIlGemello` esegue entrambe su dodici ingressi
scelti sui punti in cui due implementazioni divergono: i due estremi del
clamp, un quoziente esattamente intero dove `ceil` non deve aggiungere uno,
archi parziali, corde diverse dalla predefinita.

### ② Il telaio si chiude, o il tubo ha una cucitura

Non la normale di Frenet: dove la curva è localmente dritta la curvatura va a
zero e la normale salta di novanta gradi. Si trasporta una normale lungo la
curva con la rotazione minima (Rodrigues), e **alla fine si chiude**: dopo un
giro il telaio torna ruotato di un angolo residuo, che qui si misura e si
distribuisce in parti uguali su tutti gli anelli.

Misurato: la rotazione fra l'ultimo anello e il primo è **1,02°** contro una
media di 2,38° fra gli altri. Senza la distribuzione diventa **118,77°**, ed è
la cucitura.

### ③ Il bbox non è esatto, e la deroga ha una forma chiusa

Un tubo di raggio `r` reso con `lati` lati è un prisma **inscritto** nel
cilindro. Il bbox dichiarato prende il cilindro circoscritto, e la differenza
è `2·r·(1 − cos(π/lati))` — con i valori predefiniti, **0,272 mm su un
ingombro di 215**, cioè lo 0,40 %.

`Modello` ha guadagnato `tolleranza_mm` e `motivo_tolleranza`, e i due sono
legati: **una tolleranza senza una ragione scritta non si costruisce**. Il
confronto è a senso unico oltre lo zero — il dichiarato può stare sopra il
misurato, mai sotto: un bbox più piccolo dei vertici non è una
discretizzazione, è un errore.

La deroga viaggia col pezzo fino al `qualityGate()` del renderer, che la legge
in `meta.bboxTolleranza`. È la stessa che `math/pointcloud.js` dichiara, per la
stessa ragione.

---

## Verifica

### ✅ Le proprietà della curva e della superficie

| | |
|---|---|
| passa per i punti di controllo | scarto max **1,5·10⁻¹⁴ mm** — §17.4 ② alla lettera |
| topologia | `is_watertight`, `euler_number == 0`, winding coerente, volume > 0 — lo dice trimesh |
| telaio | ortonormale a 10⁻⁹, chiusura 1,02° contro 2,38° di media |
| conteggi | 4080 vertici e 8160 triangoli, uguali a `conteggi_di` — che li calcola **senza spazzare niente** |
| curva contro sé stessa | distanza minima fra punti non vicini **24,85 mm**, diametro del tubo 16 |

### ✅ Dal vivo, «genera un tubo da 300 millimetri»

```
T0        genera_modello {'forma': 'tubo_spline', 'raggio_guida': 150.0}
CONFERMA  create  …/workspace/modelli/tubo_spline-20260903-004201.glb
          317x330x68 mm, 4488 vertici, 8976 triangoli, GLB
ESITO     ok=True verdetto=riuscito
OSSERVATO …tubo_spline-20260903-004201.glb e' un GLB 2 coerente, 4488 vertici, 316.7x330.4x67.9 mm
```

Il file, 162.556 byte, riletto con la sola libreria standard: 4488 vertici,
316,60 × 330,37 × 67,81 mm. `libmagic` di sistema: «glTF binary model, version
2, length 162556 bytes».

⚠️ **La quota detta è il DIAMETRO, non il raggio**: «un tubo da 300
millimetri» è un anello largo 300, che è come lo direbbe chiunque
guardandolo. La metà si fa nella grammatica, una volta sola, dove la parola
diventa un numero.

### ✅ Le cinque bocciature — e la quinta è arrivata dopo

| sabotaggio | esito |
|---|---|
| il gemello JavaScript diverge di un segmento | rosso, e nomina i tre ingressi che divergono |
| il clamp Python cambia estremo | 2 rossi |
| la chiusura del telaio non si distribuisce | rosso: «la chiusura gira di 118,77° contro un massimo di 8,55°» |
| il conteggio non viene più dalla formula | rosso |
| **nodi uniformi invece che centripeti** | ⚠️ **VERDE alla prima corsa** |

⚠️ **La quinta bocciatura era verde, e ha trovato due cose.** Sostituendo i
nodi centripeti con nodi uniformi, i test sui punti di controllo e sulla
topologia restavano tutti verdi: una scelta dichiarata che nessuna misura
distingue è una scelta che qualcuno cancellerà per semplificare.

E misurando **che cosa** la centripeta comprasse, il numero ha smentito il
commento che avevo scritto:

| parametrizzazione | scarto max dalla poligonale dei punti |
|---|---|
| uniforme | 2,92 mm |
| **centripeta** | **2,72 mm** |
| cordale | 3,16 mm |

Su un guscio più duro — ondulazione 70 su raggio 90 — la centripeta è perfino
**peggio**: 10,16 contro 9,45. La ragione: i punti di controllo sono
equispaziati in angolo su una formula liscia, quindi le corde si somigliano e
le tre parametrizzazioni quasi coincidono. La patologia da cui la centripeta
protegge — cuspidi e cappi da spaziature molto disuguali — qui non si presenta.

La prima stesura del commento diceva «la garanzia serve davvero». **È stata
corretta**: la centripeta resta perché è la scelta giusta il giorno in cui i
punti non verranno più da una formula, e costa una radice quadrata. Il
presidio nuovo fissa **la parametrizzazione**, non una proprietà che qui non
consegna.

### ✅ Il ciclo §11.7 — e un difetto che non c'era

`npm run shot -- modello-tubo`: audit **0 elementi fuori sistema, 0 regole con
letterali**, font tutti caricati. Il pezzo sta dentro il riquadro, gli anelli
e le generatrici leggono la forma e la torsione, le tre quote sono a posto.

⚠️ **Guardando lo scatto avevo letto un difetto che non c'era.** La quota della
profondità sembrava cadere sotto il bordo del riquadro; ho scritto un rientro
che riporta le quote dentro la tela, e poi ho **misurato** i rettangoli con e
senza — `getBoundingClientRect` di ogni quota contro quello della propria
tela. Le quote fuori sono **zero in entrambi i casi**: quella quota sta a tre
pixel dal bordo, e tre pixel dentro sono dentro.

Il rientro è stato **tolto**. Era codice corretto per un difetto inesistente,
cioè una riga che non scatta mai. §11.7 regola 4 vale in tutt'e due i versi:
non si dichiara verde ciò che non si è misurato, e non si dichiara riparato
ciò che non era rotto.

⚠️ E la prima misura era sbagliata a sua volta: confrontavo le quote del tubo
con la tela dell'**estrusione**, perché la galleria stava rendendo entrambi i
pannelli e la mia interrogazione prendeva la prima tela della pagina. Dava sei
quote «fuori» su sei. La seconda misura scopa ogni quota alla propria tela.

### ✅ Le misure

```
uv run pytest -q -p no:cacheprovider     → 2203 passati, 25 saltati (2228 raccolti)
npm run shot -- modello-tubo             → audit pulito, font tutti caricati
npm run verifica:densita                 → CONFORME, impronta su 118 sorgenti
uv run python scripts/orfani.py          → 5 sospetti, nessuno nuovo
```

| | estrusione_45 | tubo_spline |
|---|---:|---:|
| vertici | 32 | 4080 |
| triangoli | 64 | 8160 |
| `model3d.preview` | 3,1 KB | 216,5 KB |
| tolleranza sul bbox | 0 (esatto) | 0,272 mm (0,40 %) |

### ❌ NON verificato, dichiarato

- **Che la curva non si autointersechi in generale.** La validazione controlla
  che il tubo non sia più grosso del rientro della guida, che è una condizione
  **necessaria e non sufficiente**. Sui valori predefiniti è misurato — 24,85
  mm contro 16 di diametro — e per parametri arbitrari no.
- **Il GLB in un visualizzatore esterno o in `gltf-validator`**, come per la
  fetta 1.
- **Il budget di frame dell'invariante 26** con il pannello aperto sulla
  scrivania piena: il tubo ha 4080 vertici contro i 32 dell'estrusione, e la
  misura vale la pena farla. Non è stata fatta.
- **La finestra Electron vera**: il giro ha usato la scrivania finta.
