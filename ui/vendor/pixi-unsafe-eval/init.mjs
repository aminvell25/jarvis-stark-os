import { GlUboSystem } from '../pixi.min.mjs';
import { GlShaderSystem } from '../pixi.min.mjs';
import { GlUniformGroupSystem } from '../pixi.min.mjs';
import { GpuUboSystem } from '../pixi.min.mjs';
import { UboSystem } from '../pixi.min.mjs';
import { AbstractRenderer } from '../pixi.min.mjs';
import { ParticleBuffer } from '../pixi.min.mjs';
import { generateParticleUpdatePolyfill } from './particle/generateParticleUpdatePolyfill.mjs';
import { generateShaderSyncPolyfill } from './shader/generateShaderSyncPolyfill.mjs';
import { generateUboSyncPolyfillSTD40, generateUboSyncPolyfillWGSL } from './ubo/generateUboSyncPolyfill.mjs';
import { generateUniformsSyncPolyfill } from './uniforms/generateUniformsSyncPolyfill.mjs';

"use strict";
function selfInstall() {
  Object.assign(AbstractRenderer.prototype, {
    // override unsafeEval check, as we don't need to use it
    _unsafeEvalCheck() {
    }
  });
  Object.assign(UboSystem.prototype, {
    // override unsafeEval check, as we don't need to use it
    _systemCheck() {
    }
  });
  Object.assign(GlUniformGroupSystem.prototype, {
    // use polyfill which avoids eval method
    _generateUniformsSync: generateUniformsSyncPolyfill
  });
  Object.assign(GlUboSystem.prototype, {
    // use polyfill which avoids eval method
    _generateUboSync: generateUboSyncPolyfillSTD40
  });
  Object.assign(GpuUboSystem.prototype, {
    // use polyfill which avoids eval method
    _generateUboSync: generateUboSyncPolyfillWGSL
  });
  Object.assign(GlShaderSystem.prototype, {
    // use polyfill which avoids eval method
    _generateShaderSync: generateShaderSyncPolyfill
  });
  Object.assign(ParticleBuffer.prototype, {
    // use polyfill which avoids eval method
    generateParticleUpdate: generateParticleUpdatePolyfill
  });
}
selfInstall();
//# sourceMappingURL=init.mjs.map
