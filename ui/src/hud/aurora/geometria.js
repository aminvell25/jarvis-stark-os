/** Il sistema di riferimento del nucleo Aurora.
 *
 * Un solo posto per il viewBox e il centro: il riferimento e' disegnato a
 * 1024x1024 col centro a (512, 512), e ogni raggio di `strati.js` e' un numero
 * preso da li'. Cambiare VIEWBOX senza ricalcolare i raggi non ha senso, ed e'
 * per questo che stanno insieme.
 */
export const VIEWBOX = 1024;
export const CENTRO = VIEWBOX / 2;

/** Il raggio della tela WebGL, in unita' di viewBox.
 *
 * ⚠️ 278 e non 512: nel riferimento il nucleo 3D occupa 556 px su 1024, cioe'
 * poco piu' di meta' del quadro. Tutto cio' che sta fuori — ghiera, settori,
 * corone — e' SVG, e resta nitido a qualunque scala. Allargare la tela per
 * «riempire» sposterebbe testo e tacche dentro WebGL, dove si rasterizzano:
 * e' la ragione dell'invariante 20, e qui regge ancora. */
export const RAGGIO_TELA = 278;

/** Dove cadono le cose che stanno nel DOM, in frazione del lato. */
export const POSTI = {
  marchio: { alto: 484 / VIEWBOX, corpo: 46 },
  onda: { alto: 556 / VIEWBOX, largo: 360 / VIEWBOX, alta: 56 / VIEWBOX },
  nome: { alto: 636 / VIEWBOX },
};
