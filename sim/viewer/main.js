
// 荣耀-羽毛球竞技 · 弹道仿真查看器（只做呈现）
// 所有逻辑量（球、人物、蓄力、泡泡阶段、机位）都由 C# Shuttle.Core / Shuttle.Sim 逐 tick 算好写进 out/trajectories.json；
// 这里只做 tick 间插值、模型、特效和 HUD。坐标：C# cm，X 为击球方的“右”，Three.js 显示时取 x = −X/100。
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const data = await (await fetch('/out/trajectories.json')).json();
const $ = id => document.getElementById(id);
const TICK = 60;

// ---------------- 渲染器与场景 ----------------
const renderer = new THREE.WebGLRenderer({ canvas: $('gl'), antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.05;
renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x262a31); scene.fog = new THREE.Fog(0x262a31, 26, 60);
const camera = new THREE.PerspectiveCamera(40, 1, 0.05, 200);
const controls = new OrbitControls(camera, renderer.domElement); controls.enabled = false; controls.enableDamping = true;
scene.add(new THREE.HemisphereLight(0xdfe9ff, 0x30343c, 1.35));
const sun = new THREE.DirectionalLight(0xffffff, 1.9); sun.position.set(-5, 14, -6); sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048); Object.assign(sun.shadow.camera, { left: -10, right: 10, top: 10, bottom: -10, near: 1, far: 40 });
scene.add(sun);

// 背景：灰色网格空间（后期换场馆模型）
{
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(120, 120), new THREE.MeshStandardMaterial({ color: 0x30343b, roughness: 1 }));
  floor.rotation.x = -Math.PI / 2; floor.position.y = -0.01; floor.receiveShadow = true; scene.add(floor);
  const g = new THREE.GridHelper(120, 120, 0x5d6472, 0x444a55); g.position.y = -0.005; scene.add(g);
  const wallMat = { color: 0x535a66, mid: 0x3c424c };
  const mk = (w, h, pos, ry) => { const gh = new THREE.GridHelper(w, w, wallMat.color, wallMat.mid); gh.rotation.x = Math.PI / 2; const grp = new THREE.Group(); grp.add(gh); gh.position.y = 0; gh.scale.set(1, 1, h / w);
    grp.position.copy(pos); grp.rotation.y = ry; scene.add(grp); };
  mk(28, 12, new THREE.Vector3(0, 6, 20), 0); mk(28, 12, new THREE.Vector3(0, 6, -20), 0);
  mk(40, 12, new THREE.Vector3(14, 6, 0), Math.PI / 2); mk(40, 12, new THREE.Vector3(-14, 6, 0), Math.PI / 2);
  // 场边占位方块（示意观众席/裁判椅，后期换模型）
  const boxMat = new THREE.MeshStandardMaterial({ color: 0x5a6170, roughness: .9 });
  for (const s of [-1, 1]) { const b = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.42, 6), boxMat); b.position.set(s * 6.0, 0.21, 0); b.castShadow = b.receiveShadow = true; scene.add(b); }
  const chair = new THREE.Mesh(new THREE.BoxGeometry(0.7, 1.4, 0.7), boxMat); chair.position.set(-5.6, 0.7, 1.2); chair.castShadow = true; scene.add(chair);
}

// 球场：蓝色场地 + 绿色可移动区（9.0×16.4）+ 全套白线
const HW_D = 3.05, HW_S = data.halfWidth / 100, HL = data.halfLength / 100, NET = data.netHeight / 100;
{
  const surround = new THREE.Mesh(new THREE.PlaneGeometry(9.0, 16.4), new THREE.MeshStandardMaterial({ color: 0x2f62cc, roughness: .85 }));
  surround.rotation.x = -Math.PI / 2; surround.receiveShadow = true; scene.add(surround);
  const court = new THREE.Mesh(new THREE.PlaneGeometry(HW_D * 2 + 0.04, HL * 2 + 0.04), new THREE.MeshStandardMaterial({ color: 0x1f8f68, roughness: .7 }));
  court.rotation.x = -Math.PI / 2; court.position.y = 0.002; court.receiveShadow = true; scene.add(court);
  const lineMat = new THREE.MeshBasicMaterial({ color: 0xf4f7ff });
  const W = 0.045;
  const seg = (x1, z1, x2, z2) => { const len = Math.hypot(x2 - x1, z2 - z1); const m = new THREE.Mesh(new THREE.PlaneGeometry(x1 === x2 ? W : len + W, x1 === x2 ? len + W : W), lineMat);
    m.rotation.x = -Math.PI / 2; m.position.set((x1 + x2) / 2, 0.004, (z1 + z2) / 2); scene.add(m); };
  for (const s of [-1, 1]) {
    seg(-HW_D, s * HL, HW_D, s * HL);                 // 底线
    seg(s * HW_D, -HL, s * HW_D, HL);                 // 双打边线
    seg(s * HW_S, -HL, s * HW_S, HL);                 // 单打边线
    seg(-HW_D, s * 1.90, HW_D, s * 1.90);             // 前发球线
    seg(-HW_D, s * (HL - 0.76), HW_D, s * (HL - 0.76)); // 双打后发球线
    seg(0, s * 1.90, 0, s * HL);                      // 中线
  }
}
// 球网
const netGroup = new THREE.Group(); scene.add(netGroup);
{
  const cv = document.createElement('canvas'); cv.width = 512; cv.height = 64; const c = cv.getContext('2d');
  c.strokeStyle = 'rgba(235,240,250,0.9)'; c.lineWidth = 1.2;
  for (let x = 0; x <= 512; x += 6) { c.beginPath(); c.moveTo(x, 0); c.lineTo(x, 64); c.stroke(); }
  for (let y = 0; y <= 64; y += 6) { c.beginPath(); c.moveTo(0, y); c.lineTo(512, y); c.stroke(); }
  const tex = new THREE.CanvasTexture(cv); tex.wrapS = tex.wrapT = THREE.RepeatWrapping; tex.repeat.set(6, 1); tex.anisotropy = 8;
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(6.1, 0.76), new THREE.MeshBasicMaterial({ map: tex, transparent: true, opacity: .85, side: THREE.DoubleSide, depthWrite: false }));
  mesh.position.set(0, NET - 0.38, 0); netGroup.add(mesh);
  const tape = new THREE.Mesh(new THREE.BoxGeometry(6.1, 0.06, 0.02), new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0x666666 }));
  tape.position.set(0, NET - 0.03, 0); netGroup.add(tape);
  const postMat = new THREE.MeshStandardMaterial({ color: 0x222833, metalness: .3, roughness: .5 });
  const baseMat = new THREE.MeshStandardMaterial({ color: 0x2a8cff, roughness: .6 });
  for (const s of [-1, 1]) {
    const p = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.03, NET + 0.05, 12), postMat); p.position.set(s * 3.1, (NET + 0.05) / 2, 0); p.castShadow = true; scene.add(p);
    const b = new THREE.Mesh(new THREE.BoxGeometry(0.28, 0.16, 0.6), baseMat); b.position.set(s * 3.2, 0.08, 0); b.castShadow = true; scene.add(b);
  }
}

// ---------------- 火柴人（后期换 GLB 人物） ----------------
function makeStick(color) {
  const mat = new THREE.MeshStandardMaterial({ color, roughness: .45, emissive: color, emissiveIntensity: .25 });
  const g = new THREE.Group(); scene.add(g);
  const limb = r => { const m = new THREE.Mesh(new THREE.CylinderGeometry(r, r, 1, 10), mat); m.castShadow = true; g.add(m); return m; };
  const joint = r => { const m = new THREE.Mesh(new THREE.SphereGeometry(r, 12, 10), mat); m.castShadow = true; g.add(m); return m; };
  const parts = { torso: limb(0.055), neck: limb(0.035), uArmR: limb(0.032), lArmR: limb(0.03), uArmL: limb(0.032), lArmL: limb(0.03),
    thighR: limb(0.04), shinR: limb(0.036), thighL: limb(0.04), shinL: limb(0.036), shoulders: limb(0.035), hips: limb(0.04),
    head: joint(0.115), handR: joint(0.035), handL: joint(0.033), footR: joint(0.045), footL: joint(0.045), kneeR: joint(0.042), kneeL: joint(0.042), elbowR: joint(0.034), elbowL: joint(0.034) };
  // 球拍
  const racket = new THREE.Group(); g.add(racket);
  const rmat = new THREE.MeshStandardMaterial({ color: 0xf2f4f8, roughness: .3, metalness: .4 });
  const handle = new THREE.Mesh(new THREE.CylinderGeometry(0.014, 0.014, 0.40, 8), rmat); handle.position.y = 0.20; racket.add(handle);
  const frame = new THREE.Mesh(new THREE.TorusGeometry(0.1, 0.009, 8, 32), new THREE.MeshStandardMaterial({ color: 0x111111, roughness: .4 }));
  frame.scale.set(1, 1.25, 1); frame.position.y = 0.53; racket.add(frame);
  const strings = new THREE.Mesh(new THREE.CircleGeometry(0.1, 24), new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: .25, side: THREE.DoubleSide }));
  strings.scale.set(1, 1.25, 1); strings.position.y = 0.53; racket.add(strings);
  return { g, parts, racket, phase: 0, last: null, dir: new THREE.Vector3(0, 0, 1) };
}
const UP = new THREE.Vector3(0, 1, 0);
function setLimb(m, a, b) { const d = new THREE.Vector3().subVectors(b, a); const L = d.length(); m.position.copy(a).addScaledVector(d, .5); m.scale.set(1, Math.max(L, 1e-3), 1); m.quaternion.setFromUnitVectors(UP, d.normalize()); }
function twoBone(root, target, l1, l2, bendHint) {
  const d = new THREE.Vector3().subVectors(target, root); let L = d.length(); L = Math.min(L, l1 + l2 - 1e-3); d.setLength(L);
  const end = root.clone().add(d);
  const a = Math.acos(THREE.MathUtils.clamp((l1 * l1 + L * L - l2 * l2) / (2 * l1 * L), -1, 1));
  const n = d.clone().normalize(); const hint = bendHint.clone().sub(n.clone().multiplyScalar(bendHint.dot(n))).normalize();
  const mid = root.clone().addScaledVector(n, Math.cos(a) * l1).addScaledVector(hint, Math.sin(a) * l1);
  return [mid, end];
}
// pose: 局部坐标（面向 +z，右手 = −x），world 由 group 朝向决定
function poseStick(s, o) {
  const P = s.parts, lift = o.lift || 0, A = o.stride, ph = s.phase;
  const pelvis = new THREE.Vector3(0, 0.95 + lift - A * 0.03, 0), chest = new THREE.Vector3(0, 1.40 + lift, 0.02 + A * 0.05);
  const hipR = pelvis.clone().add(new THREE.Vector3(-0.1, 0, 0)), hipL = pelvis.clone().add(new THREE.Vector3(0.1, 0, 0));
  const shR = chest.clone().add(new THREE.Vector3(-0.19, 0, 0)), shL = chest.clone().add(new THREE.Vector3(0.19, 0, 0));
  setLimb(P.torso, pelvis, chest); setLimb(P.hips, hipR, hipL); setLimb(P.shoulders, shR, shL);
  const neckTop = chest.clone().add(new THREE.Vector3(0, 0.12, 0)); setLimb(P.neck, chest, neckTop); P.head.position.copy(neckTop).add(new THREE.Vector3(0, 0.1, 0));
  const tuck = lift > 0.05 ? 0.25 : 0;
  for (const [hip, thigh, shin, knee, foot, sgn] of [[hipR, P.thighR, P.shinR, P.kneeR, P.footR, 1], [hipL, P.thighL, P.shinL, P.kneeL, P.footL, -1]]) {
    const sw = Math.sin(ph + (sgn > 0 ? 0 : Math.PI));
    const ft = new THREE.Vector3(hip.x * 1.6, Math.max(0.045, lift + Math.max(0, Math.cos(ph + (sgn > 0 ? 0 : Math.PI))) * 0.14 * A + tuck), sw * 0.34 * A + 0.02);
    const [kn, en] = twoBone(hip, ft, 0.46, 0.46, new THREE.Vector3(0, 0, 1));
    setLimb(thigh, hip, kn); setLimb(shin, kn, en); knee.position.copy(kn); foot.position.copy(en);
  }
  // 持拍手
  const hand = o.hand || shR.clone().add(new THREE.Vector3(-0.12, -0.2, 0.3));
  const [elR, haR] = twoBone(shR, hand, 0.3, 0.3, new THREE.Vector3(-0.6, -0.5, -0.5));
  setLimb(P.uArmR, shR, elR); setLimb(P.lArmR, elR, haR); P.elbowR.position.copy(elR); P.handR.position.copy(haR);
  const offHand = shL.clone().add(new THREE.Vector3(0.12, -0.35, 0.1 - Math.sin(ph) * 0.2 * A + (o.offReach || 0)));
  const [elL, haL] = twoBone(shL, offHand, 0.3, 0.3, new THREE.Vector3(0.6, -0.4, -0.5));
  setLimb(P.uArmL, shL, elL); setLimb(P.lArmL, elL, haL); P.elbowL.position.copy(elL); P.handL.position.copy(haL);
  s.racket.position.copy(haR); const rd = (o.racketDir || new THREE.Vector3(-0.3, 0.6, 0.6)).clone().normalize();
  s.racket.quaternion.setFromUnitVectors(UP, rd);
}
const own = makeStick(0x46c3ff), opp = makeStick(0xff6b5e);

// 脚下光圈（手绘图：中心四段圆弧顺时针旋转，外弧+三角指向移动方向）
function makeFootRing(color) {
  const g = new THREE.Group(); scene.add(g);
  const m = (o) => new THREE.MeshBasicMaterial({ color, transparent: true, opacity: o, side: THREE.DoubleSide, depthWrite: false });
  const base = new THREE.Mesh(new THREE.RingGeometry(0.43, 0.455, 64), m(.85)); base.rotation.x = -Math.PI / 2; g.add(base);
  const glow = new THREE.Mesh(new THREE.RingGeometry(0.30, 0.43, 64), m(.10)); glow.rotation.x = -Math.PI / 2; g.add(glow);
  const spin = new THREE.Group(); g.add(spin);
  for (let i = 0; i < 4; i++) { const a = new THREE.Mesh(new THREE.RingGeometry(0.31, 0.35, 24, 1, i * Math.PI / 2 + 0.2, Math.PI / 2 - 0.4), m(.8)); a.rotation.x = -Math.PI / 2; spin.add(a); }
  const ptr = new THREE.Group(); g.add(ptr);
  const arc = new THREE.Mesh(new THREE.RingGeometry(0.47, 0.51, 32, 1, Math.PI / 2 - 0.55, 1.1), m(.95)); arc.rotation.x = -Math.PI / 2; ptr.add(arc);
  const tri = new THREE.Shape(); tri.moveTo(0, 0.62); tri.lineTo(-0.07, 0.5); tri.lineTo(0.07, 0.5); tri.lineTo(0, 0.62);
  const t = new THREE.Mesh(new THREE.ShapeGeometry(tri), m(1)); t.rotation.x = -Math.PI / 2; ptr.add(t);
  g.position.y = 0.012;
  return { g, spin, ptr };
}
const ownRing = makeFootRing(0x39d4ff), oppRing = makeFootRing(0xff5a5a);

// ---------------- 羽毛球（后期换建模刚体） ----------------
const ball = new THREE.Group(); scene.add(ball);
{
  const S = 2.0; // 设计文档 10.4：球模型放大 2.0 倍
  const cork = new THREE.Mesh(new THREE.SphereGeometry(0.0125 * S, 16, 12), new THREE.MeshStandardMaterial({ color: 0xfaf6ee, roughness: .6 })); ball.add(cork);
  const band = new THREE.Mesh(new THREE.CylinderGeometry(0.0135 * S, 0.0135 * S, 0.006 * S, 16), new THREE.MeshStandardMaterial({ color: 0x2255cc })); band.position.y = -0.008 * S; ball.add(band);
  const cv = document.createElement('canvas'); cv.width = 256; cv.height = 64; const c = cv.getContext('2d');
  c.fillStyle = 'rgba(255,255,255,0.78)'; c.fillRect(0, 0, 256, 64); c.strokeStyle = 'rgba(170,175,190,0.9)'; c.lineWidth = 2;
  for (let i = 0; i < 16; i++) { c.beginPath(); c.moveTo(i * 16, 0); c.lineTo(i * 16, 64); c.stroke(); }
  const skirt = new THREE.Mesh(new THREE.CylinderGeometry(0.033 * S, 0.0135 * S, 0.062 * S, 16, 1, true),
    new THREE.MeshStandardMaterial({ map: new THREE.CanvasTexture(cv), transparent: true, side: THREE.DoubleSide, roughness: .8, depthWrite: false }));
  skirt.position.y = -(0.01 + 0.031) * S; ball.add(skirt);
}
const glowTex = (() => { const cv = document.createElement('canvas'); cv.width = cv.height = 128; const c = cv.getContext('2d');
  const gr = c.createRadialGradient(64, 64, 0, 64, 64, 64); gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(.25, 'rgba(255,255,255,.7)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
  c.fillStyle = gr; c.fillRect(0, 0, 128, 128); return new THREE.CanvasTexture(cv); })();
const ballGlow = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, color: 0xffffff, blending: THREE.AdditiveBlending, transparent: true, depthWrite: false })); scene.add(ballGlow);
const hitFlash = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, color: 0xffffff, blending: THREE.AdditiveBlending, transparent: true, depthWrite: false })); scene.add(hitFlash);
const ballShadow = new THREE.Mesh(new THREE.CircleGeometry(0.12, 24), new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: .35, depthWrite: false }));
ballShadow.rotation.x = -Math.PI / 2; scene.add(ballShadow);

// 时机泡泡（fresnel 透明泡，阶段一紫色 8 Hz，阶段二浅蓝 2 Hz）
const bubbleMat = new THREE.ShaderMaterial({ transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  uniforms: { col: { value: new THREE.Color(0x7fd8ff) }, k: { value: 1 } },
  vertexShader: 'varying vec3 vN; varying vec3 vV; void main(){ vec4 mv = modelViewMatrix*vec4(position,1.0); vN = normalize(normalMatrix*normal); vV = normalize(-mv.xyz); gl_Position = projectionMatrix*mv; }',
  fragmentShader: 'uniform vec3 col; uniform float k; varying vec3 vN; varying vec3 vV; void main(){ float f = pow(1.0-abs(dot(vN,vV)), 2.2); gl_FragColor = vec4(col*(0.25+1.6*f)*k, (0.06+0.9*f)*k); }' });
const bubble = new THREE.Mesh(new THREE.SphereGeometry(0.2, 32, 24), bubbleMat); scene.add(bubble);

// 拖尾：相机朝向的带状网格，RGBA 顶点色
class Ribbon {
  constructor(max = 96) {
    this.max = max; const g = new THREE.BufferGeometry();
    this.pos = new Float32Array(max * 2 * 3); this.col = new Float32Array(max * 2 * 4);
    g.setAttribute('position', new THREE.BufferAttribute(this.pos, 3)); g.setAttribute('color', new THREE.BufferAttribute(this.col, 4));
    const idx = []; for (let i = 0; i < max - 1; i++) { const a = i * 2; idx.push(a, a + 1, a + 2, a + 1, a + 3, a + 2); } g.setIndex(idx);
    this.mat = new THREE.MeshBasicMaterial({ vertexColors: true, transparent: true, depthWrite: false, side: THREE.DoubleSide, blending: THREE.AdditiveBlending });
    this.mesh = new THREE.Mesh(g, this.mat); this.mesh.frustumCulled = false; scene.add(this.mesh); this.g = g;
  }
  set(pts, color, alpha, width, offset, additive) {
    const n = Math.min(pts.length, this.max); this.mat.blending = additive ? THREE.AdditiveBlending : THREE.NormalBlending;
    if (n < 2) { this.g.setDrawRange(0, 0); return; }
    const c = new THREE.Color(color), view = new THREE.Vector3(), tan = new THREE.Vector3(), side = new THREE.Vector3();
    for (let i = 0; i < n; i++) {
      const p = pts[pts.length - n + i], q = pts[Math.min(pts.length - 1, pts.length - n + i + 1)], r0 = pts[Math.max(0, pts.length - n + i - 1)];
      tan.subVectors(q, r0).normalize(); view.subVectors(camera.position, p).normalize(); side.crossVectors(tan, view).normalize();
      const u = i / (n - 1), w = width * (0.2 + 0.8 * u), a = alpha * Math.pow(u, 1.4);
      const cx = p.x + side.x * offset, cy = p.y + side.y * offset, cz = p.z + side.z * offset;
      this.pos.set([cx + side.x * w, cy + side.y * w, cz + side.z * w, cx - side.x * w, cy - side.y * w, cz - side.z * w], i * 6);
      const hl = 0.55 + 0.45 * u; // 头部更亮
      this.col.set([c.r * hl + (1 - hl) * 0, c.g * hl, c.b * hl, a, c.r * hl, c.g * hl, c.b * hl, a], i * 8);
    }
    this.g.attributes.position.needsUpdate = true; this.g.attributes.color.needsUpdate = true; this.g.setDrawRange(0, (n - 1) * 6);
  }
  hide() { this.g.setDrawRange(0, 0); }
}
const ribbons = [new Ribbon(), new Ribbon(), new Ribbon(), new Ribbon()];
const sparks = new THREE.Points(new THREE.BufferGeometry(), new THREE.PointsMaterial({ map: glowTex, size: 0.06, color: 0xffffff, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
sparks.geometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(64 * 3), 3)); sparks.frustumCulled = false; scene.add(sparks);

// 落点标记（手绘图：深色核心 + 高亮环填充，外圈圆弧顺时针旋转，粒子上浮）+ 三圈范围 + 落地水波
const marker = new THREE.Group(); scene.add(marker);
const mm = (c, o) => new THREE.MeshBasicMaterial({ color: c, transparent: true, opacity: o, side: THREE.DoubleSide, depthWrite: false });
const flat = m => { m.rotation.x = -Math.PI / 2; return m; };
const mkCore = flat(new THREE.Mesh(new THREE.CircleGeometry(0.16, 32), mm(0x0b2a4a, .75))); marker.add(mkCore);
const mkFill = flat(new THREE.Mesh(new THREE.RingGeometry(0.16, 0.30, 48), mm(0xbff3ff, .55))); marker.add(mkFill);
const mkEdge = flat(new THREE.Mesh(new THREE.RingGeometry(0.30, 0.325, 48), mm(0xffffff, .9))); marker.add(mkEdge);
const mkSpin = new THREE.Group(); marker.add(mkSpin);
for (let i = 0; i < 4; i++) mkSpin.add(flat(new THREE.Mesh(new THREE.RingGeometry(0.36, 0.42, 24, 1, i * Math.PI / 2 + 0.25, Math.PI / 2 - 0.5), mm(0x8fe6ff, .9))));
const ranges = [0.6, 1.2, 1.8].map((r, i) => { const m = flat(new THREE.Mesh(new THREE.RingGeometry(r - 0.012, r + 0.012, 96), mm(0xffffff, [.45, .28, .16][i]))); marker.add(m); return m; });
const mkParts = new THREE.Points(new THREE.BufferGeometry(), new THREE.PointsMaterial({ map: glowTex, size: 0.07, color: 0xbff3ff, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
mkParts.geometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(24 * 3), 3)); marker.add(mkParts);
const ripples = new THREE.Group(); scene.add(ripples);
for (let i = 0; i < 4; i++) ripples.add(flat(new THREE.Mesh(new THREE.RingGeometry(0.96, 1.0, 64), mm(0xdff8ff, .8))));
marker.position.y = ripples.position.y = 0.015;

// ---------------- HUD ----------------
const ICON = {
  Drop: '<svg viewBox="0 0 40 40" class="ico"><path d="M6 30 Q14 6 24 10 Q31 13 33 30" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round"/><path d="M28 27 L33 32 L36 25" fill="none" stroke="#fff" stroke-width="3" stroke-linejoin="round"/></svg>',
  Flat: '<svg viewBox="0 0 40 40" class="ico"><path d="M5 16 L33 24" stroke="#fff" stroke-width="3.4" stroke-linecap="round"/><path d="M26 18 L34 24 L25 28" fill="none" stroke="#fff" stroke-width="3" stroke-linejoin="round"/><path d="M5 11 L20 14 M7 21 L18 23" stroke="#fff" stroke-width="1.6" opacity=".6"/></svg>',
  High: '<svg viewBox="0 0 40 40" class="ico"><path d="M5 33 Q20 -8 35 33" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round"/><path d="M30 28 L35 34 L38 27" fill="none" stroke="#fff" stroke-width="3" stroke-linejoin="round"/></svg>'
};
const FAMLBL = { Drop: '切削·下坠', Flat: '攻击·平弧', High: '挑送·高弧' }, FAMNAME = { Drop: '下坠', Flat: '平弧', High: '高弧' };
const TIERCOL = ['#FFFFFF', '#FFD23F', '#FF8A1F', '#FF2E2E'];
const C = 2 * Math.PI * 46;
const btn = {};
for (const f of ['Drop', 'Flat', 'High']) {
  const el = $('b' + f); let segs = '';
  for (let i = 0; i < 4; i++) segs += '<circle class="seg" id="seg' + f + i + '" cx="50" cy="50" r="46" stroke="' + TIERCOL[i] + '" stroke-dasharray="0 ' + C + '" stroke-dashoffset="' + (-i * C / 4) + '"/>';
  let ticks = ''; for (let i = 0; i < 4; i++) { const a = i * Math.PI / 2; ticks += '<line class="tick" x1="' + (50 + 42 * Math.cos(a)) + '" y1="' + (50 + 42 * Math.sin(a)) + '" x2="' + (50 + 50 * Math.cos(a)) + '" y2="' + (50 + 50 * Math.sin(a)) + '"/>'; }
  el.innerHTML = '<svg viewBox="0 0 100 100"><circle class="base" cx="50" cy="50" r="46"/>' + segs + ticks + '</svg><div class="face">' + ICON[f] + '<b id="name' + f + '">' + FAMNAME[f] + '</b></div><div class="lbl">' + FAMLBL[f] + '</div>';
  btn[f] = el;
}
const arrow = document.createElement('div'); arrow.id = 'ballArrow'; arrow.innerHTML = '<span></span>'; document.body.appendChild(arrow);
const legend = document.createElement('div'); legend.id = 'legend';
legend.innerHTML = '<div><i style="background:#FF2020"></i>完美</div><div><i style="background:#FFC800"></i>跨步</div><div><i style="background:#C8C8C8"></i>糟糕（球体发白光）</div><div><i style="background:linear-gradient(#fff,#ff2020,#fff);height:8px"></i>杀球三光带</div><div><i style="background:#b46bff"></i>泡泡·跳杀时机</div><div><i style="background:#7fd8ff"></i>泡泡·击球时机</div>';
document.body.appendChild(legend);

// ---------------- 播放状态 ----------------
let list = [], cur = null, ft = 0, playing = true, view = 'game', camLive = { p: new THREE.Vector3(), l: new THREE.Vector3(), fov: 40 };
const QCOL = { 完美: 0xff2020, 跨步: 0xffc800, 糟糕: 0xc8c8c8 };
const V = (x, y, z) => new THREE.Vector3(-x / 100, y / 100, z / 100);
function arr(a, k, w, i) { return a[k * w + i]; }
function ballAt(f) { const S = cur.scene, T = S.ticks - 1; const k = Math.max(0, Math.min(T, Math.floor(f))), k2 = Math.min(T, k + 1), u = f - k;
  return V(arr(S.ball, k, 3, 0) * (1 - u) + arr(S.ball, k2, 3, 0) * u, arr(S.ball, k, 3, 1) * (1 - u) + arr(S.ball, k2, 3, 1) * u, arr(S.ball, k, 3, 2) * (1 - u) + arr(S.ball, k2, 3, 2) * u); }
function personAt(a, w, f) { const S = cur.scene, T = S.ticks - 1; const k = Math.max(0, Math.min(T, Math.floor(f))), k2 = Math.min(T, k + 1), u = f - k;
  const x = arr(a, k, w, 0) * (1 - u) + arr(a, k2, w, 0) * u, z = arr(a, k, w, 1) * (1 - u) + arr(a, k2, w, 1) * u, l = w > 2 ? arr(a, k, w, 2) * (1 - u) + arr(a, k2, w, 2) * u : 0;
  return { p: V(x, 0, z), lift: l / 100 }; }

function filter() {
  const f = { group: $('fGroup').value, zone: $('fZone').value, tier: $('fTier').value, quality: $('fQual').value, lane: $('fLane').value };
  list = data.shots.filter(s => Object.entries(f).every(([k, v]) => !v || s[k] === v));
  $('list').innerHTML = list.map((s, i) => '<div data-i="' + i + '"><span class="dot" style="background:#' + QCOL[s.quality].toString(16).padStart(6, '0') + '"></span>#' + s.id + ' ' + s.zone + (s.label === '地面' ? '' : '·' + s.label) + ' ' + s.action + ' ' + s.tier + s.lane + s.quality +
    (s.netHit ? '<span class="badge">撞网</span>' : s.placeholder ? '<span class="badge ph">占位</span>' : '') + '</div>').join('');
}
function select(i) {
  cur = list[i]; if (!cur) return; ft = 0; playing = true;
  document.querySelectorAll('#list div').forEach(d => d.classList.toggle('sel', +d.dataset.i === i));
  const S = cur.scene; $('scrub').max = S.ticks - 1;
  const f = familyOf(cur);
  for (const k of ['Drop', 'Flat', 'High']) $('name' + k).textContent = k === f ? cur.action.split(' ')[1] : FAMNAME[k];
  const km = Math.round(Math.hypot(S.landX - cur.p[0], S.landZ - cur.p[2]) / 100 / (cur.n / 60) * 3.6 * 7.2);
  $('info').textContent = '#' + cur.id + '  ' + cur.action + (cur.placeholder ? '（白档顶点为占位值，待拍板）' : '') +
    '\n' + cur.group + ' · ' + cur.zone + ' · ' + cur.label + '\n蓄力档 ' + cur.tier + '（' + S.charge + ' tick）　线路 ' + cur.lane + '　质量 ' + cur.quality +
    '\n飞行 ' + cur.n + ' tick（' + (cur.n / 60).toFixed(2) + ' s）　显示球速约 ' + km + ' km/h' +
    '\n顶点 ' + cur.apex + ' cm　过网高度 ' + cur.netY + ' cm' + (cur.netHit ? '　→ 撞网' : '') +
    '\n落点 横向 ' + S.landX + '　距网 ' + S.landZ + ' cm' +
    '\n接球方最多可蓄 ' + cur.receiverCharge + ' tick' + (S.recvDist >= 0 ? '\n示意跑位：落地时对手距落点 ' + S.recvDist + ' cm（反应 15 tick）' : '');
  popped = {};
}
function familyOf(s) { const id = s.action[0]; return id === 'Q' ? 'Drop' : id === 'Z' ? 'Flat' : 'High'; }

// ---------------- 每帧 ----------------
let popped = {}, lastT = performance.now(), fpsAcc = 0, fpsN = 0, awakeT0 = performance.now(), prevOwn = null, prevOpp = null;
function project(v) { const p = v.clone().project(camera); return { x: (p.x * .5 + .5) * innerWidth, y: (-p.y * .5 + .5) * innerHeight, behind: p.z > 1 }; }
function popTag(cls, text, at) { const e = document.createElement('div'); e.className = cls; e.textContent = text; document.body.appendChild(e);
  const p = project(at); e.style.left = p.x + 'px'; e.style.top = (p.y - 50) + 'px';
  e.animate([{ transform: 'translate(-50%,-50%) skewX(-12deg) scale(1.5)', opacity: 0 }, { transform: 'translate(-50%,-50%) skewX(-12deg) scale(1)', opacity: 1, offset: .17 }, { clipPath: 'inset(0 0 0 0)', offset: .75 }, { clipPath: 'inset(0 0 0 100%)', opacity: 1 }],
    { duration: 600 / (+$('speed').value), easing: 'ease-out' }).onfinish = () => e.remove(); }

function animStick(s, ring, st, faceSign, extra, dt) {
  const p = st.p; s.g.position.set(p.x, 0, p.z); s.g.rotation.y = faceSign > 0 ? 0 : Math.PI;
  const v = s.last ? p.clone().sub(s.last) : new THREE.Vector3(); s.last = p.clone();
  const sp = v.length() / Math.max(dt, 1e-4); // m/s（播放速度下）
  const spd = sp / (+$('speed').value || 1);
  s.phase += v.length() * 5.2; const stride = THREE.MathUtils.clamp(spd / 3.8, 0, 1);
  if (v.lengthSq() > 1e-8) s.dir.copy(v).setY(0).normalize();
  poseStick(s, Object.assign({ stride, lift: st.lift }, extra));
  ring.g.position.set(p.x, 0.012, p.z); ring.spin.rotation.y -= dt * 2.4;
  ring.ptr.rotation.y = Math.atan2(s.dir.x, s.dir.z) - Math.PI / 2 + Math.PI / 2; ring.ptr.rotation.y = Math.atan2(s.dir.x, s.dir.z);
  ring.ptr.visible = stride > 0.05;
}

function frame(now) {
  const dt = Math.min(0.1, (now - lastT) / 1000); lastT = now; fpsAcc += dt; fpsN++;
  if (fpsAcc > 0.5) { $('fps').textContent = Math.round(fpsN / fpsAcc); fpsAcc = 0; fpsN = 0; }
  if (!cur) { renderer.render(scene, camera); requestAnimationFrame(frame); return; }
  const S = cur.scene, T = S.ticks - 1;
  if (playing) { ft += dt * TICK * (+$('speed').value); if (ft >= T) { ft = 0; popped = {}; } }
  const k = Math.floor(ft), t = k - S.pre;
  $('scrub').value = k; $('tickLbl').textContent = 'tick ' + k + ' / ' + T + (t >= 0 ? '  出球+' + t : '  来球' + t);
  $('clock').textContent = '00:' + String(Math.floor(k / 60) % 60).padStart(2, '0');

  // 球
  const bp = ballAt(ft), bp2 = ballAt(Math.min(T, ft + 0.5)), live = k <= S.land;
  ball.position.copy(bp); const vel = bp2.clone().sub(bp);
  if (vel.lengthSq() > 1e-8 && live) ball.quaternion.setFromUnitVectors(UP, vel.normalize());
  ballShadow.position.set(bp.x, 0.008, bp.z); ballShadow.visible = bp.y > 0.03;
  const bad = cur.quality === '糟糕' && t >= 0 && live;
  ballGlow.visible = bad; ballGlow.position.copy(bp); ballGlow.scale.setScalar(0.42 + 0.06 * Math.sin(now / 90)); ballGlow.material.opacity = .85;

  // 拖尾
  ribbons.forEach(r => r.hide()); sparks.visible = false;
  const outgoing = t >= 0, life = outgoing && cur.scene.kill && !bad ? 26 : 20;
  const start = outgoing ? S.pre : 0, from = Math.max(start, ft - life);
  if (ft - start > 0.5 && k <= S.land + life) {
    const pts = []; for (let f = from; f < Math.min(ft, S.land); f += 0.5) pts.push(ballAt(f)); pts.push(ballAt(Math.min(ft, S.land)));
    const fade = k > S.land ? Math.max(0, 1 - (ft - S.land) / life) : 1;
    if (!outgoing) ribbons[0].set(pts, 0xffc800, 0.55 * fade, 0.035, 0, true);           // 来球（示意，对手跨步球）
    else if (bad) ribbons[0].set(pts, 0xc8c8c8, 0.6 * fade, 0.05, 0, false);             // 糟糕：浅灰拖尾
    else if (cur.scene.kill) {                                                         // 杀类：三条平行光带，加宽加亮
      const c = QCOL[cur.quality]; ribbons[0].set(pts, c, 1.0 * fade, 0.07, 0, true); ribbons[1].set(pts, c, .85 * fade, .04, .13, true);
      ribbons[2].set(pts, c, .85 * fade, .04, -.13, true); ribbons[3].set(pts, 0xffffff, 1.0 * fade, .018, 0, true);
      const sp = sparks.geometry.attributes.position; let n = 0;
      for (let i = 0; i < pts.length && n < 64; i += 1) { const h = Math.sin((Math.floor(from) + i) * 12.9898) * 43758.5; const r = h - Math.floor(h);
        if (r < .55) { sp.setXYZ(n++, pts[i].x + (r - .27) * .25, pts[i].y + (r * 7 % 1 - .5) * .2, pts[i].z + (r * 13 % 1 - .5) * .2); } }
      sp.needsUpdate = true; sparks.geometry.setDrawRange(0, n); sparks.visible = true; sparks.material.opacity = fade;
    } else { ribbons[0].set(pts, QCOL[cur.quality], 0.95 * fade, 0.045, 0, true); ribbons[1].set(pts, 0xffffff, .6 * fade, .01, 0, true); }
  }
  // 触球闪光：完美大闪 / 跨步中闪 / 糟糕只闪球体
  const ht = ft - S.pre;
  if (ht >= 0 && ht < 9) { const a = 1 - ht / 9; hitFlash.visible = true; hitFlash.position.copy(ballAt(S.pre));
    const sz = cur.quality === '完美' ? 0.9 : cur.quality === '跨步' ? 0.45 : 0.22; hitFlash.scale.setScalar(sz * (0.6 + 0.6 * (1 - a))); hitFlash.material.opacity = a;
    hitFlash.material.color.set(cur.quality === '糟糕' ? 0xffffff : cur.scene.kill ? 0xfff0e0 : 0xffffff);
  } else hitFlash.visible = false;
  if (ht >= 0 && !popped.q) { popped.q = 1; if (cur.quality === '完美') popTag('qtag perfect', '完美', ballAt(S.pre)); if (cur.quality === '糟糕') popTag('qtag bad', '糟糕', ballAt(S.pre));
    if (cur.tier === '红' && cur.scene.kill) { const km = Math.round(Math.hypot(S.landX - cur.p[0], S.landZ - cur.p[2]) / 100 / (cur.n / 60) * 3.6 * 7.2); setTimeout(() => popTag('pop', km + ' km/h', ballAt(S.pre).add(new THREE.Vector3(0, .3, 0))), 120); } }

  // 泡泡
  const ph = S.bubble[Math.min(k, T)];
  bubble.visible = ph > 0; bubble.position.copy(bp);
  if (ph > 0) { const hz = ph === 2 ? 8 : 2; const blink = 0.35 + 0.65 * (0.5 + 0.5 * Math.cos(2 * Math.PI * hz * ft / TICK));
    bubbleMat.uniforms.col.value.set(ph === 2 ? 0xb46bff : 0x7fd8ff); bubbleMat.uniforms.k.value = blink; }

  // 落点标记：出球后第 6 tick 在对手场地出现；来球段在本方击球点
  const showMk = !cur.netHit && ((t >= 6 && k <= S.land) || (t < 0 && k >= 6));
  marker.visible = showMk;
  if (showMk) { const lp = t >= 0 ? V(S.landX, 0, S.landZ) : V(cur.p[0], 0, cur.p[2]); marker.position.set(lp.x, 0.015, lp.z); mkSpin.rotation.y -= dt * 2.2;
    const pulse = 1 + 0.06 * Math.sin(now / 160); mkFill.scale.setScalar(pulse);
    ranges.forEach(r => r.visible = $('optRanges').checked);
    const pa = mkParts.geometry.attributes.position; for (let i = 0; i < 24; i++) { const a = i * 2.399, r = 0.15 + (i % 5) * 0.06, y = ((now / 1000 * 0.5 + i / 24) % 1);
      pa.setXYZ(i, Math.cos(a) * r, y * 0.6, Math.sin(a) * r); } pa.needsUpdate = true; mkParts.material.opacity = 0.9; }
  // 落地水波（球落地仍未接到）
  const after = ft - S.land; ripples.visible = !cur.netHit && after > 0;
  if (ripples.visible) { ripples.position.set(-S.landX / 100, 0.015, S.landZ / 100);
    ripples.children.forEach((r, i) => { const u = ((after / 40) + i / 4) % 1; const s = 0.2 + u * 1.3; r.scale.setScalar(s); r.material.opacity = (1 - u) * 0.8 * Math.min(1, after / 6); }); }
  // 撞网：网抖（纯视觉）
  netGroup.position.z = cur.netHit && after > 0 && after < 20 ? Math.sin(after * 1.6) * 0.04 * (1 - after / 20) : 0;

  // 人物
  const os = personAt(S.own, 3, ft), ps = personAt(S.opp, 2, ft);
  const ch = S.chargeTicks;
  const local = (w, s) => { const d = w.clone().sub(s.g.position); return new THREE.Vector3(-d.x, d.y, d.z); }; // own 面向 +z：世界→局部（x 取反见右手约定）
  // 持拍手：来球段架拍→蓄力引拍→命中前 6 tick 挥拍到球→随挥
  const contact = ballAt(S.pre); const shR = new THREE.Vector3(-0.19, 1.40 + os.lift, 0.02);
  let hand, rdir, extra = {};
  const cocked = new THREE.Vector3(-0.32, 1.75 + os.lift, -0.28), ready = new THREE.Vector3(-0.32, 1.15 + os.lift, 0.32);
  const cLocal = (() => { const d = contact.clone().sub(new THREE.Vector3(os.p.x, 0, os.p.z)); return new THREE.Vector3(d.x, d.y, d.z); })();
  // 注意：火柴人 group 面向 +z 且 rotation 0，局部 = 世界偏移
  const lowShot = contact.y < 1.2;
  const cockLow = new THREE.Vector3(-0.4, 0.9, -0.1);
  const wind = THREE.MathUtils.clamp((t + Math.max(ch, 8) + 7) / Math.max(ch, 8), 0, 1);
  const tgt = cLocal.clone(); const armMax = 0.6;
  const reach = (c) => { const d = c.clone().sub(shR); const L = d.length(); return shR.clone().add(d.setLength(Math.min(L - 0.5, armMax))); };
  if (t < -6) { hand = ready.clone().lerp(lowShot ? cockLow : cocked, wind); rdir = lowShot ? new THREE.Vector3(-0.5, -0.2, -0.6) : new THREE.Vector3(0.1, -0.3, -1); }
  else if (t <= 0) { const u = (t + 6) / 6; const h0 = lowShot ? cockLow : cocked; const hc = reach(tgt); hand = h0.clone().lerp(hc, u * u); rdir = tgt.clone().sub(hand).normalize().lerp(lowShot ? new THREE.Vector3(0, -0.4, -0.5) : new THREE.Vector3(0, 0.2, -1), 1 - u); }
  else { const u = Math.min(1, t / 14); hand = reach(tgt).lerp(new THREE.Vector3(0.15, lowShot ? 1.5 : 0.95, 0.35), u).lerp(ready, Math.max(0, (t - 20) / 20)); rdir = new THREE.Vector3(0.6, lowShot ? 0.6 : -0.4, 0.5).lerp(new THREE.Vector3(-0.3, 0.6, 0.6), Math.max(0, (t - 20) / 20)); }
  extra = { hand, racketDir: rdir, offReach: t < 0 && !lowShot ? 0.35 * wind : 0 };
  animStick(own, ownRing, os, 1, extra, dt);
  animStick(opp, oppRing, ps, -1, {}, dt);

  // HUD：按键蓄力环（从正上方顺时针：白→黄→橙→红）、窗口白环、进档震动
  const fam = familyOf(cur), cv = S.charge[Math.min(k, T)];
  for (const f of ['Drop', 'Flat', 'High']) {
    const on = f === fam && cv >= 0; btn[f].classList.toggle('press', on); btn[f].classList.toggle('window', t < 0 && k >= 4 && !on);
    for (let i = 0; i < 4; i++) { let fill = 0;
      if (on) { const edges = [0, 36, 54, 72, 73]; fill = i < 3 ? THREE.MathUtils.clamp((cv - edges[i]) / (edges[i + 1] - edges[i]), 0, 1) : (cv >= 72 ? 1 : 0);
        if (i === 0 && ch === 0) fill = 0.06; }
      $('seg' + f + i).setAttribute('stroke-dasharray', (fill * C / 4 - (fill > 0 ? 1.2 : 0)) + ' ' + C); }
  }
  const tierNow = cv >= 72 ? 3 : cv >= 54 ? 2 : cv >= 36 ? 1 : cv >= 0 ? 0 : -1;
  if (tierNow >= 0 && popped.tier !== tierNow && cv > 0 || (cv === 0 && popped.tier === undefined)) { popped.tier = tierNow; const b = btn[fam]; b.classList.remove('buzz'); void b.offsetWidth; b.classList.add('buzz'); if (navigator.vibrate) navigator.vibrate(tierNow === 0 ? 60 : 20); }
  if (t === -6 && !popped.rel) { popped.rel = 1; const b = btn[fam]; b.classList.add('release'); setTimeout(() => b.classList.remove('release'), 120); }
  // 摇杆：本方移动方向（屏幕坐标）
  const mv = own.dir, moving = ownRing.ptr.visible; $('knob').style.transform = moving ? 'translate(' + (-mv.x * 38) + '%,' + (-mv.z * 38) + '%)' : 'none';
  // 觉醒演示
  const aw = $('optAwake').checked; $('bAwake').style.display = aw ? 'block' : 'none'; $('bAwake').classList.toggle('on', aw);
  let tags = '';
  if (aw) { const e = ((now - awakeT0) / 1000) % 8, rem = 8 - e; $('awRing').setAttribute('stroke-dasharray', (rem / 8 * C) + ' ' + C); $('awRing').setAttribute('stroke-dashoffset', -(e / 8) * C);
    tags += '<span class="tag-awake">觉醒中 ' + rem.toFixed(1) + 's</span>'; $('will').style.width = (rem / 8 * 100) + '%'; } else $('will').style.width = '62%';
  $('tagsMe').innerHTML = tags; $('stam').style.width = '82%';

  // 机位
  if (view === 'game') { const c = S.cam, f = ft, k0 = Math.floor(f), k1 = Math.min(T, k0 + 1), u = f - k0, g = (i) => c[k0 * 7 + i] * (1 - u) + c[k1 * 7 + i] * u;
    camera.position.copy(V(g(0), g(1), g(2))); camera.lookAt(V(g(3), g(4), g(5))); if (Math.abs(camera.fov - g(6)) > 0.01) { camera.fov = g(6); camera.updateProjectionMatrix(); } }
  else if (view === 'recv') { camera.position.set(ps.p.x * 0.5, 5.6, ps.p.z + 11.5); camera.lookAt(ps.p.x * 0.5, 0, ps.p.z - 2); }
  else if (view === 'free') controls.update();
  // 球出屏指示器
  const pr = project(bp); const m = 24; const off = pr.behind || pr.x < m || pr.y < m || pr.x > innerWidth - m || pr.y > innerHeight - m;
  if (off && live) { const cx = innerWidth / 2, cy = innerHeight / 2; let dx = pr.x - cx, dy = pr.y - cy; if (pr.behind) { dx = -dx; dy = -dy; }
    const s = Math.min((cx - 40) / Math.abs(dx || 1e-3), (cy - 40) / Math.abs(dy || 1e-3)); arrow.style.display = 'block';
    arrow.style.left = (cx + dx * s - 12) + 'px'; arrow.style.top = (cy + dy * s - 11) + 'px'; arrow.style.transform = 'rotate(' + (Math.atan2(dy, dx) * 180 / Math.PI + 90) + 'deg)';
    arrow.firstChild.textContent = bp.y.toFixed(1) + 'm'; } else arrow.style.display = 'none';
  renderer.render(scene, camera); requestAnimationFrame(frame);
}

// ---------------- 交互 ----------------
function setView(v) {
  view = v; controls.enabled = v === 'free';
  document.querySelectorAll('#tool .views button').forEach(b => b.classList.toggle('on', b.dataset.v === v));
  camera.fov = 40; camera.updateProjectionMatrix();
  if (v === 'side') { camera.position.set(13.5, 4.6, 0); camera.lookAt(0, 1.2, 0); }
  if (v === 'top') { camera.position.set(0, 25, 0.01); camera.lookAt(0, 0, 0); }
  if (v === 'free') { controls.target.set(0, 1, 0); camera.position.set(9, 7, -11); controls.update(); }
  $('hud').style.display = v === 'game' ? 'block' : 'none';
  legend.style.display = 'block';
}
['fGroup', 'fZone', 'fTier', 'fQual', 'fLane'].forEach(id => $(id).onchange = () => { filter(); select(0); });
$('list').onclick = e => { const d = e.target.closest('div[data-i]'); if (d) select(+d.dataset.i); };
$('play').onclick = () => { playing = !playing; $('play').textContent = playing ? '❚❚' : '▶'; };
$('step').onclick = () => { playing = false; $('play').textContent = '▶'; ft = Math.min(Math.floor(ft) + 1, cur.scene.ticks - 1); };
$('scrub').oninput = e => { playing = false; $('play').textContent = '▶'; ft = +e.target.value; popped = { q: ft >= cur.scene.pre ? 1 : 0, tier: undefined }; };
$('drawer').onclick = () => $('panel').classList.toggle('open');
$('optAwake').onchange = () => { awakeT0 = performance.now(); };
document.querySelectorAll('#tool .views button').forEach(b => b.onclick = () => setView(b.dataset.v));
addEventListener('keydown', e => {
  if (e.code === 'Space') { e.preventDefault(); $('play').click(); }
  if (e.code === 'ArrowRight') $('step').click();
  if (e.code === 'Tab') { e.preventDefault(); $('drawer').click(); }
  if (e.code === 'KeyV') { const vs = ['game', 'free', 'side', 'top', 'recv']; setView(vs[(vs.indexOf(view) + 1) % vs.length]); }
});
function resize() { renderer.setSize(innerWidth, innerHeight, false); camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix(); }
addEventListener('resize', resize); resize();
const q = new URLSearchParams(location.search);
for (const [k, id] of [['zone', 'fZone'], ['tier', 'fTier'], ['qual', 'fQual'], ['group', 'fGroup'], ['lane', 'fLane']]) if (q.get(k)) $(id).value = q.get(k);
filter(); select(+(q.get('i') || 0)); setView(q.get('view') || 'game'); $('play').textContent = '❚❚';
if (q.get('t')) { ft = +q.get('t'); playing = false; $('play').textContent = '▶'; }
if (q.get('awake')) $('optAwake').checked = true;
if (q.get('panel') === '0') $('panel').classList.remove('open');
requestAnimationFrame(frame);
