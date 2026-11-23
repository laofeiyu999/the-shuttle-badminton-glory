// 只做呈现：轨迹由 C# 核心（sim/src/Shuttle.Core）逐 tick 算好，这里按 tick 播放，不重算任何弹道。
// 坐标：C# 用 cm，X 为击球方右手方向为负…此处约定 C# 的 X+ = 击球方视角“右”；Three.js 相机从 Z<0 看向 +Z 时屏幕右 = −X，故显示时取 −X。
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const data = await (await fetch('/out/trajectories.json')).json();
const HW = data.halfWidth / 100, HL = data.halfLength / 100, NET = data.netHeight / 100;
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(devicePixelRatio); document.body.appendChild(renderer.domElement);
const scene = new THREE.Scene(); scene.background = new THREE.Color(0x2a3038);
const camera = new THREE.PerspectiveCamera(42, 1, 0.05, 200);
const controls = new OrbitControls(camera, renderer.domElement); controls.enabled = false;
scene.add(new THREE.HemisphereLight(0xffffff, 0x445566, 1.2));
const sun = new THREE.DirectionalLight(0xffffff, 1.2); sun.position.set(4, 10, -3); scene.add(sun);

// 场地：单打外框、中线、前发球线、网
const floor = new THREE.Mesh(new THREE.PlaneGeometry(9.0, 16.4), new THREE.MeshLambertMaterial({ color: 0x2f6b4f }));
floor.rotation.x = -Math.PI / 2; scene.add(floor);
const lineMat = new THREE.LineBasicMaterial({ color: 0xffffff });
function line(pts) { scene.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts.map(p => new THREE.Vector3(p[0], 0.005, p[1]))), lineMat)); }
line([[-HW, -HL], [HW, -HL], [HW, HL], [-HW, HL], [-HW, -HL]]);
for (const s of [-1, 1]) { line([[-HW, s * 1.9], [HW, s * 1.9]]); line([[0, s * 1.9], [0, s * HL]]); }
const net = new THREE.Mesh(new THREE.PlaneGeometry(6.1, 0.76), new THREE.MeshBasicMaterial({ color: 0xdddddd, transparent: true, opacity: 0.35, side: THREE.DoubleSide }));
net.position.set(0, NET - 0.38, 0); scene.add(net);
const tape = new THREE.Mesh(new THREE.BoxGeometry(6.1, 0.03, 0.02), new THREE.MeshBasicMaterial({ color: 0xffffff })); tape.position.set(0, NET, 0); scene.add(tape);
for (const s of [-1, 1]) { const post = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.02, NET), new THREE.MeshLambertMaterial({ color: 0x888888 })); post.position.set(s * 3.05, NET / 2, 0); scene.add(post); }

// 人物占位：逻辑身高 1.75 m 胶囊（后续换 GLB 模型）
function person(color) { const g = new THREE.Group(); const m = new THREE.Mesh(new THREE.CapsuleGeometry(0.22, 1.31, 4, 12), new THREE.MeshLambertMaterial({ color })); m.position.y = 0.875; g.add(m); scene.add(g); return g; }
const hitter = person(0x3d7bd9), receiver = person(0xd9553d);
const ball = new THREE.Mesh(new THREE.SphereGeometry(0.05, 16, 12), new THREE.MeshBasicMaterial({ color: 0xffffff })); scene.add(ball);
const landMark = new THREE.Mesh(new THREE.RingGeometry(0.12, 0.16, 32), new THREE.MeshBasicMaterial({ color: 0xffee55, side: THREE.DoubleSide }));
landMark.rotation.x = -Math.PI / 2; landMark.position.y = 0.01; scene.add(landMark);
const trailGroup = new THREE.Group(); scene.add(trailGroup);
// 拖尾铁律（第 10 章）：完美红 #FF2020、跨步黄 #FFC800、糟糕浅灰
const qColor = { 完美: 0xff2020, 跨步: 0xffc800, 糟糕: 0xcccccc };

let shots = [], cur = null, tick = 0, playing = false, acc = 0, view = 'game';
const $ = id => document.getElementById(id);
function pts(s) { const a = []; for (let i = 0; i < s.p.length; i += 3) a.push(new THREE.Vector3(-s.p[i] / 100, s.p[i + 1] / 100, s.p[i + 2] / 100)); return a; }
function filter() {
  const f = { group: $('fGroup').value, zone: $('fZone').value, tier: $('fTier').value, quality: $('fQual').value, lane: $('fLane').value };
  shots = data.shots.filter(s => Object.entries(f).every(([k, v]) => !v || s[k] === v));
  $('list').innerHTML = shots.map((s, i) => '<option value="' + i + '">#' + s.id + ' ' + s.zone + (s.label === '地面' ? '' : s.label) + ' ' + s.action + ' ' + s.tier + s.lane + s.quality + (s.netHit ? ' 撞网' : '') + (s.placeholder ? ' *占位' : '') + '</option>').join('');
}
function clearTrails() { while (trailGroup.children.length) trailGroup.remove(trailGroup.children[0]); }
function drawTrail(s, opacity) {
  trailGroup.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts(s)), new THREE.LineBasicMaterial({ color: qColor[s.quality], transparent: true, opacity })));
}
function select(i) {
  cur = shots[i]; if (!cur) return; tick = 0; playing = false; clearTrails(); drawTrail(cur, 0.9);
  const P = pts(cur), last = P[P.length - 1];
  hitter.position.set(P[0].x, 0, P[0].z - 0.35);
  receiver.position.set(cur.netHit ? 0 : last.x, 0, cur.netHit ? 3.5 : Math.min(last.z + 0.4, HL));
  landMark.visible = !cur.netHit; landMark.position.x = last.x; landMark.position.z = last.z;
  $('info').textContent = '#' + cur.id + ' ' + cur.action + '\n组/场区：' + cur.group + ' / ' + cur.zone + ' / ' + cur.label +
    '\n蓄力档：' + cur.tier + '　线路：' + cur.lane + '　质量：' + cur.quality +
    '\n时长：' + cur.n + ' tick（' + (cur.n / 60).toFixed(2) + ' s）\n顶点：' + cur.apex + ' cm　网平面：' + cur.netY + ' cm' +
    '\n撞网：' + (cur.netHit ? '是' : '否') + '\n落点：横向 ' + Math.round(-last.x * 100) + '（负=左）' + '，距网 ' + Math.round(last.z * 100) + ' cm' +
    '\n接球方最多可蓄：' + cur.receiverCharge + ' tick' + (cur.placeholder ? '\n* 该动作白档顶点为占位值，待拍板' : '');
  update();
}
function update() {
  if (!cur) return; const P = pts(cur); const i = Math.min(tick, P.length - 1); ball.position.copy(P[i]);
  $('hud').textContent = 'tick ' + i + ' / ' + (P.length - 1) + '　视角：' + { game: '实战', free: '自由360°', side: '侧视', top: '俯视', recv: '接球方' }[view];
}
// 实战视角临时实现：第 10.7.2 节主机位初值（后 5.5 m、高 7.0 m、俯 32°、vFOV 42°、横向跟随 0.35）。
// 正式版改为调用 C# Camera.rigParams 的同一段机位代码（仿真与游戏同源），这里先占位。
function gameCam() {
  const fx = hitter.position.x * 0.35; // 横向跟随 0.35
  camera.fov = 42; camera.position.set(fx, 7.0, hitter.position.z - 5.5);
  const tgtZ = camera.position.z + 7.0 / Math.tan(32 * Math.PI / 180);
  camera.lookAt(fx, 0, tgtZ);
}
function setView(v) {
  view = v; controls.enabled = v === 'free'; camera.fov = 42;
  if (v === 'side') { camera.position.set(13, 3.2, 0); camera.lookAt(0, 1.5, 0); }
  if (v === 'top') { camera.position.set(0, 22, 0.01); camera.lookAt(0, 0, 0); }
  if (v === 'recv') { camera.position.set(0, 7.0, HL + 5.5); camera.lookAt(0, 0, HL + 5.5 - 7.0 / Math.tan(32 * Math.PI / 180)); }
  if (v === 'free') { controls.target.set(0, 1, 0); camera.position.set(9, 6, -9); controls.update(); }
  camera.updateProjectionMatrix(); update();
}
['fGroup', 'fZone', 'fTier', 'fQual', 'fLane'].forEach(id => $(id).onchange = () => { filter(); if (shots.length) { $('list').selectedIndex = 0; select(0); } });
$('list').onchange = e => select(+e.target.value);
$('play').onclick = () => { if (!cur) return; if (tick >= cur.p.length / 3 - 1) tick = 0; playing = !playing; };
$('step').onclick = () => { if (!cur) return; playing = false; tick = Math.min(tick + 1, cur.p.length / 3 - 1); update(); };
$('all').onclick = () => { clearTrails(); shots.slice(0, 120).forEach(s => drawTrail(s, 0.35)); if (cur) drawTrail(cur, 1); };
document.querySelectorAll('.views button').forEach(b => b.onclick = () => setView(b.dataset.v));
addEventListener('keydown', e => { if (e.code === 'Space') $('play').click(); if (e.code === 'ArrowRight') $('step').click(); });
function resize() { renderer.setSize(innerWidth, innerHeight); camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix(); }
addEventListener('resize', resize); resize();
filter(); $('list').selectedIndex = 0; select(0); setView('game');
let lastT = performance.now();
renderer.setAnimationLoop(t => {
  const dt = (t - lastT) / 1000; lastT = t;
  if (playing && cur) { acc += dt * 60 * +$('speed').value; while (acc >= 1) { acc -= 1; tick++; } if (tick >= cur.p.length / 3 - 1) { tick = cur.p.length / 3 - 1; playing = false; } update(); }
  if (view === 'game') gameCam(); if (view === 'free') controls.update();
  renderer.render(scene, camera);
});
