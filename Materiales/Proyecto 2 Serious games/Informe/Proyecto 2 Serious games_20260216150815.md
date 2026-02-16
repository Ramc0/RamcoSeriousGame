# Reporte de proyecto

## Estructura del proyecto

```
D:\Arcon\Clase\TAME\Programación multimedia y dispositivos móviles\000- Actividaddes\Proyecto 2 Serious games
├── Algoritmo genetico
│   └── Algoritmo genetico.html
├── Entorno 3d mover camara
│   └── Camara movimiento.html
├── Informe
├── Openstreetmap
│   └── MapaManos.html
├── Python Blender
│   └── PythonBlender.py
└── TPS multijugador
    └── Multi.html
```

## Código (intercalado)

# Proyecto 2 Serious games
## Algoritmo genetico
**Algoritmo genetico.html**
```html
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <title>Simulación de robots tipo Roomba (evolutivos)</title>
  <style>
    * { box-sizing: border-box; }
    body{
      margin:0;
      background: radial-gradient(circle at top left,#1b2735 0%,#090a0f 40%,#000 100%);
      height:100vh;
      color:#eee;
      font-family: system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
      overflow:hidden;
    }
    #container{ display:flex; width:100vw; height:100vh; padding:16px; gap:16px; }
    #leftPane{ flex:1 1 auto; display:flex; justify-content:center; align-items:center; }
    #rightPane{ width:320px; display:flex; flex-direction:column; gap:12px; }
    #sim{
      background: radial-gradient(circle at center,#141820 0%,#050609 100%);
      border-radius:14px;
      box-shadow:0 0 40px rgba(0,0,0,.8);
      display:block;
      width:100%;
      height:100%;
    }
    #chart{
      background: linear-gradient(135deg,rgba(10,10,20,.96),rgba(5,8,18,.96));
      border-radius:10px;
      box-shadow:0 8px 20px rgba(0,0,0,.45);
    }
    #info{
      background: linear-gradient(135deg,rgba(10,10,20,.95),rgba(25,25,45,.96));
      padding:10px 14px;
      font-size:12px;
      border-radius:10px;
      white-space:pre-line;
      border:1px solid rgba(120,160,255,.3);
      box-shadow:0 8px 20px rgba(0,0,0,.4);
      backdrop-filter: blur(6px);
    }
    #info strong{ color:#9cc4ff; }
  </style>
</head>
<body>
<div id="container">
  <div id="leftPane"><canvas id="sim"></canvas></div>
  <div id="rightPane">
    <div id="info"></div>
    <canvas id="chart" width="280" height="170"></canvas>
  </div>
</div>

<script>
/* ---------- Configuración básica ---------- */
const simCanvas   = document.getElementById("sim");
const simCtx      = simCanvas.getContext("2d");
const infoDiv     = document.getElementById("info");
const chartCanvas = document.getElementById("chart");
const chartCtx    = chartCanvas.getContext("2d");

const margin = 16;
const SIDEBAR_WIDTH = 320;

simCanvas.width  = window.innerWidth  - SIDEBAR_WIDTH - margin * 3;
simCanvas.height = window.innerHeight - margin * 2;

const walls = [];
let cellSize;
let cols, rows;
let border = 20;

let GOAL_RADIUS = 35, GOAL_X = 0, GOAL_Y = 0;
let START_X = 0, START_Y = 0, START_RADIUS = 0;

const NUM_ROBOTS = 50;
let generation = 1;

let generationTimes = [];
let generationStartTime = performance.now();
let bestGenes = null;

const defaultGenes = {
  radius: 9,
  speed: 1.8,
  sensorLength: 95,
  sensorAngles: [-0.6, -0.25, 0, 0.25, 0.6],
  turnCooldownMax: 18,
  baseTurnAngle: 0.45,
  randomTurnRange: 0.9,
  hue: 200,
  colorTurnStrength: 0.06,
  glowIntensity: 1.0,
  colorWeights: {
    wall:  -1.2,
    goal:   1.0,
    start:  0.2,
    fuel:   0.9,   // preferencia por recarga (positivo = atraer, negativo = evitar)
    empty:  0.0
  },
  memoryFade: 0.025,
  memoryWeight: 0.9
};

let robots = [];

/* ---------- ENERGÍA y puntos de recarga ---------- */
const ENERGY_MAX = 100;
const ENERGY_DRAIN_PER_FRAME = 0.045;
const DEAD_GREY = { h: 0, s: 0, l: 55 };

const fuels = [];
let FUEL_RADIUS = 12;
const FUEL_COUNT = 34;
const FUEL_GAIN_PER_FRAME = 25;
const FUEL_ROBOT_COOLDOWN_FRAMES = 8;

/* ---------- Suavizado de glow (attack/release) ---------- */
const FUEL_GLOW_ATTACK = 0.18;     // subida suave
const FUEL_GLOW_RELEASE = 0.10;    // bajada suave
const ROBOT_REFUEL_ATTACK = 0.22;
const ROBOT_REFUEL_RELEASE = 0.14;

/* ---------- Utilidades geométricas ---------- */
function segmentIntersection(p0, p1, p2, p3) {
  const s1x = p1.x - p0.x, s1y = p1.y - p0.y;
  const s2x = p3.x - p2.x, s2y = p3.y - p2.y;
  const denom = (-s2x * s1y + s1x * s2y);
  if (denom === 0) return null;
  const s = (-s1y * (p0.x - p2.x) + s1x * (p0.y - p2.y)) / denom;
  const t = ( s2x * (p0.y - p2.y) - s2y * (p0.x - p2.x)) / denom;
  if (s >= 0 && s <= 1 && t >= 0 && t <= 1) {
    return { x: p0.x + (t * s1x), y: p0.y + (t * s1y), t, u: s };
  }
  return null;
}

function circleIntersectsRect(cx, cy, radius, rect) {
  const closestX = Math.max(rect.x, Math.min(cx, rect.x + rect.w));
  const closestY = Math.max(rect.y, Math.min(cy, rect.y + rect.h));
  const dx = cx - closestX, dy = cy - closestY;
  return (dx*dx + dy*dy) < (radius*radius);
}

function rayCircleIntersection(start, end, cx, cy, r) {
  const dx = end.x - start.x, dy = end.y - start.y;
  const fx = start.x - cx, fy = start.y - cy;
  const a = dx*dx + dy*dy;
  const b = 2 * (fx*dx + fy*dy);
  const c = fx*fx + fy*fy - r*r;
  const disc = b*b - 4*a*c;
  if (disc < 0) return null;
  const sqrtD = Math.sqrt(disc);
  const t1 = (-b - sqrtD) / (2*a);
  const t2 = (-b + sqrtD) / (2*a);
  let t = null;
  if (t1 >= 0 && t1 <= 1) t = t1;
  else if (t2 >= 0 && t2 <= 1) t = t2;
  if (t === null) return null;
  return { t, x: start.x + dx*t, y: start.y + dy*t };
}

function dist2(ax, ay, bx, by){
  const dx = ax - bx, dy = ay - by;
  return dx*dx + dy*dy;
}

/* ---------- Generación de laberinto (DFS) ---------- */
function createMaze() {
  walls.length = 0;

  const W = simCanvas.width, H = simCanvas.height;
  const targetCell = 80;
  const usableW = W - 2 * border;
  const usableH = H - 2 * border;

  cols = Math.max(1, Math.floor(usableW / targetCell));
  rows = Math.max(1, Math.floor(usableH / targetCell));

  cellSize = Math.min(usableW / cols, usableH / rows);

  const usedW = cols * cellSize;
  const usedH = rows * cellSize;
  border = 0.5 * (Math.min(W - usedW, H - usedH));

  const grid = [];
  for (let y = 0; y < rows; y++) {
    const row = [];
    for (let x = 0; x < cols; x++) {
      row.push({ x, y, visited:false, walls:{ top:true, right:true, bottom:true, left:true }});
    }
    grid.push(row);
  }

  function neighbours(cell) {
    const list = [];
    const {x,y} = cell;
    if (y > 0) list.push(grid[y-1][x]);
    if (x < cols-1) list.push(grid[y][x+1]);
    if (y < rows-1) list.push(grid[y+1][x]);
    if (x > 0) list.push(grid[y][x-1]);
    return list;
  }

  function removeWall(a,b){
    const dx = b.x - a.x, dy = b.y - a.y;
    if (dx === 1){ a.walls.right=false; b.walls.left=false; }
    else if (dx === -1){ a.walls.left=false; b.walls.right=false; }
    else if (dy === 1){ a.walls.bottom=false; b.walls.top=false; }
    else if (dy === -1){ a.walls.top=false; b.walls.bottom=false; }
  }

  const stack = [];
  const startCell = grid[0][0];
  startCell.visited = true;
  stack.push(startCell);

  while (stack.length) {
    const current = stack[stack.length-1];
    const neigh = neighbours(current).filter(n => !n.visited);
    if (!neigh.length) stack.pop();
    else {
      const next = neigh[Math.floor(Math.random()*neigh.length)];
      next.visited = true;
      removeWall(current,next);
      stack.push(next);
    }
  }

  const wallThickness = Math.max(4, cellSize * 0.14);
  function cellToX(c){ return border + c*cellSize; }
  function cellToY(r){ return border + r*cellSize; }

  GOAL_X = cellToX(cols-1) + cellSize/2;
  GOAL_Y = cellToY(rows-1) + cellSize/2;
  GOAL_RADIUS = cellSize*0.35;

  START_X = cellToX(0) + cellSize/2;
  START_Y = cellToY(0) + cellSize/2;
  START_RADIUS = cellSize*0.32;

  for (let y=0;y<rows;y++){
    for (let x=0;x<cols;x++){
      const c = grid[y][x];
      const cx = cellToX(x), cy = cellToY(y);

      if (c.walls.top && y===0) walls.push({x:cx,y:cy,w:cellSize,h:wallThickness});
      if (c.walls.left && x===0) walls.push({x:cx,y:cy,w:wallThickness,h:cellSize});

      if (c.walls.bottom && y<rows-1) walls.push({x:cx,y:cy+cellSize-wallThickness/2,w:cellSize,h:wallThickness});
      if (c.walls.right  && x<cols-1) walls.push({x:cx+cellSize-wallThickness/2,y:cy,w:wallThickness,h:cellSize});

      if (y===rows-1 && c.walls.bottom) walls.push({x:cx,y:cy+cellSize-wallThickness,w:cellSize,h:wallThickness});
      if (x===cols-1 && c.walls.right)  walls.push({x:cx+cellSize-wallThickness,y:cy,w:wallThickness,h:cellSize});
    }
  }

  createFuelPoints();
}

/* ---------- Puntos de recarga ---------- */
function createFuelPoints(){
  fuels.length = 0;
  const minD2FromStart = (cellSize*1.2)*(cellSize*1.2);
  const minD2FromGoal  = (cellSize*1.2)*(cellSize*1.2);

  const candidates = [];
  for (let y=0;y<rows;y++){
    for (let x=0;x<cols;x++){
      const cx = border + x*cellSize + cellSize/2;
      const cy = border + y*cellSize + cellSize/2;
      const d2s = dist2(cx,cy,START_X,START_Y);
      const d2g = dist2(cx,cy,GOAL_X,GOAL_Y);
      if (d2s > minD2FromStart && d2g > minD2FromGoal) candidates.push({x:cx,y:cy});
    }
  }

  for (let i=candidates.length-1;i>0;i--){
    const j = Math.floor(Math.random()*(i+1));
    [candidates[i],candidates[j]] = [candidates[j],candidates[i]];
  }

  const count = Math.min(FUEL_COUNT, candidates.length);
  FUEL_RADIUS = Math.max(10, cellSize*0.14);

  for (let i=0;i<count;i++){
    const p = candidates[i];

    let ok = true;
    for (const w of walls){
      if (circleIntersectsRect(p.x,p.y,FUEL_RADIUS*1.05,w)){ ok=false; break; }
    }
    if (!ok) continue;

    fuels.push({
      x: p.x,
      y: p.y,
      r: FUEL_RADIUS,
      activeGlow: 0,          // valor animado 0..1
      activeGlowTarget: 0     // objetivo por frame (se setea desde robots)
    });
  }
}

/* --- Fuel: NO idle flicker. Solo brilla si alguien recarga, con subida/bajada suave --- */
function drawFuels(){
  if (!fuels.length) return;

  simCtx.save();

  for (const f of fuels){
    // suavizado attack/release hacia target
    const a = (f.activeGlowTarget > f.activeGlow) ? FUEL_GLOW_ATTACK : FUEL_GLOW_RELEASE;
    f.activeGlow += (f.activeGlowTarget - f.activeGlow) * a;
    if (f.activeGlow < 0.0008) f.activeGlow = 0;

    // reset target para el siguiente frame (los robots lo reactivarán si procede)
    f.activeGlowTarget = 0;

    // base (sin glow)
    simCtx.globalAlpha = 1;
    simCtx.beginPath();
    simCtx.arc(f.x, f.y, f.r, 0, Math.PI*2);
    simCtx.fillStyle = "rgba(255, 216, 102, 0.10)";
    simCtx.fill();

    simCtx.lineWidth = 2;
    simCtx.strokeStyle = "rgba(255, 216, 102, 0.35)";
    simCtx.stroke();

    // icono base
    simCtx.globalAlpha = 0.55;
    simCtx.strokeStyle = "rgba(255, 240, 190, 0.55)";
    simCtx.lineWidth = 2;
    simCtx.beginPath();
    simCtx.moveTo(f.x - f.r*0.35, f.y);
    simCtx.lineTo(f.x + f.r*0.35, f.y);
    simCtx.moveTo(f.x, f.y - f.r*0.35);
    simCtx.lineTo(f.x, f.y + f.r*0.35);
    simCtx.stroke();

    // glow SOLO si activeGlow > 0
    if (f.activeGlow > 0.001){
      const g = f.activeGlow; // 0..1
      const haloR = f.r * (2.0 + 2.0*g);
      const grad = simCtx.createRadialGradient(f.x, f.y, f.r*0.2, f.x, f.y, haloR);
      grad.addColorStop(0, `rgba(255, 216, 102, ${0.75*g})`);
      grad.addColorStop(1, `rgba(255, 216, 102, 0)`);

      simCtx.globalAlpha = 1;
      simCtx.fillStyle = grad;
      simCtx.beginPath();
      simCtx.arc(f.x, f.y, haloR, 0, Math.PI*2);
      simCtx.fill();

      simCtx.globalAlpha = 0.95*g;
      simCtx.lineWidth = 2;
      simCtx.strokeStyle = "rgba(255, 216, 102, 0.95)";
      simCtx.beginPath();
      simCtx.arc(f.x, f.y, f.r, 0, Math.PI*2);
      simCtx.stroke();
    }
  }

  simCtx.restore();
}

/* ---------- Dibujo del entorno ---------- */
function drawBackgroundGrid(){
  simCtx.save();
  simCtx.globalAlpha = 0.15;
  simCtx.strokeStyle = "#1f2933";
  simCtx.lineWidth = 1;
  for (let x=0;x<=cols;x++){
    const gx = border + x*cellSize;
    simCtx.beginPath();
    simCtx.moveTo(gx,border);
    simCtx.lineTo(gx,border + rows*cellSize);
    simCtx.stroke();
  }
  for (let y=0;y<=rows;y++){
    const gy = border + y*cellSize;
    simCtx.beginPath();
    simCtx.moveTo(border,gy);
    simCtx.lineTo(border + cols*cellSize,gy);
    simCtx.stroke();
  }
  simCtx.restore();
}

function drawWalls(){
  simCtx.save();
  simCtx.shadowColor = "rgba(0, 0, 0, 0.8)";
  simCtx.shadowBlur = 8;
  simCtx.fillStyle = "#1f3b4d";
  for (const w of walls) simCtx.fillRect(w.x,w.y,w.w,w.h);
  simCtx.shadowBlur = 0;
  simCtx.globalAlpha = 0.4;
  simCtx.strokeStyle = "#56c7ff";
  simCtx.lineWidth = 1;
  for (const w of walls) simCtx.strokeRect(w.x,w.y,w.w,w.h);
  simCtx.restore();
}

function drawStart(){
  simCtx.save();
  simCtx.globalAlpha = 0.4;
  const haloR = START_RADIUS * 1.5;
  const grad = simCtx.createRadialGradient(START_X,START_Y,START_RADIUS*0.3, START_X,START_Y,haloR);
  grad.addColorStop(0,"rgba(120,220,255,0.6)");
  grad.addColorStop(1,"rgba(120,220,255,0)");
  simCtx.fillStyle = grad;
  simCtx.beginPath(); simCtx.arc(START_X,START_Y,haloR,0,Math.PI*2); simCtx.fill();

  simCtx.globalAlpha = 1;
  simCtx.beginPath(); simCtx.arc(START_X,START_Y,START_RADIUS,0,Math.PI*2);
  simCtx.fillStyle = "rgba(120,220,255,0.25)";
  simCtx.fill();
  simCtx.lineWidth = 2;
  simCtx.strokeStyle = "#7fe4ff";
  simCtx.stroke();

  simCtx.font="12px system-ui";
  simCtx.fillStyle="#bfefff";
  simCtx.textAlign="center";
  simCtx.fillText("INICIO",START_X,START_Y+4);
  simCtx.restore();
}

function drawGoal(){
  simCtx.save();
  simCtx.globalAlpha = 0.5;
  const haloR = GOAL_RADIUS * 1.7;
  const grad = simCtx.createRadialGradient(GOAL_X,GOAL_Y,GOAL_RADIUS*0.3, GOAL_X,GOAL_Y,haloR);
  grad.addColorStop(0,"rgba(80,255,160,0.7)");
  grad.addColorStop(1,"rgba(80,255,160,0)");
  simCtx.fillStyle = grad;
  simCtx.beginPath(); simCtx.arc(GOAL_X,GOAL_Y,haloR,0,Math.PI*2); simCtx.fill();

  simCtx.globalAlpha = 1;
  simCtx.beginPath(); simCtx.arc(GOAL_X,GOAL_Y,GOAL_RADIUS,0,Math.PI*2);
  simCtx.fillStyle="rgba(80,255,160,0.20)";
  simCtx.fill();
  simCtx.lineWidth=2;
  simCtx.strokeStyle="#5affb0";
  simCtx.stroke();

  simCtx.font="12px system-ui";
  simCtx.fillStyle="#caffde";
  simCtx.textAlign="center";
  simCtx.fillText("META",GOAL_X,GOAL_Y+4);
  simCtx.restore();
}

/* ---------- Clase Robot ---------- */
class Robot{
  constructor(x,y,genes){
    const g = genes || defaultGenes;

    this.x = x;
    this.y = y;
    this.radius = g.radius;
    this.angle = Math.random()*Math.PI*2;
    this.speed = g.speed;

    this.sensorLength = g.sensorLength;
    this.sensorAngles = g.sensorAngles.slice();
    this.sensorHits = [];

    this.turnCooldown = 0;
    this.turnCooldownMax = g.turnCooldownMax;
    this.baseTurnAngle = g.baseTurnAngle;
    this.randomTurnRange = g.randomTurnRange;

    this.colorWeights = { ...g.colorWeights };
    this.colorTurnStrength = g.colorTurnStrength;
    this.glowIntensity = g.glowIntensity;

    const baseHue = (g.hue !== undefined) ? g.hue : Math.random()*360;
    this.hue = (baseHue + (Math.random()*60 - 30) + 360) % 360;

    this.history = [];
    this.historyMax = 40;

    this.memory = [];
    this.memoryMax = 140;
    this.memoryFade = g.memoryFade ?? 0.025;
    this.memoryWeight = g.memoryWeight ?? 0.9;
    this.memoryDropInterval = 5;
    this.memoryDropCounter = 0;

    this.energy = ENERGY_MAX;
    this.dead = false;
    this.fuelCooldown = 0;

    // <<< NUEVO: glow de recarga suavizado 0..1
    this.refuelGlow = 0;
    this.refuelGlowTarget = 0;
  }

  die(){
    this.dead = true;
    this.energy = 0;
    this.speed = 0;
    this.glowIntensity = 0;
    this.colorTurnStrength = 0;
    this.refuelGlowTarget = 0;
  }

  tryRefuel(){
    if (this.dead) return;

    // por defecto: no recarga
    this.refuelGlowTarget = 0;

    if (this.fuelCooldown > 0){
      this.fuelCooldown--;
      return;
    }

    for (const f of fuels){
      const r = f.r * 1.35;
      const d2 = dist2(this.x, this.y, f.x, f.y);
      if (d2 <= r*r){
        this.energy = Math.min(ENERGY_MAX, this.energy + FUEL_GAIN_PER_FRAME);
        this.fuelCooldown = FUEL_ROBOT_COOLDOWN_FRAMES;

        // activar objetivos de glow (robot + punto)
        this.refuelGlowTarget = 1;
        f.activeGlowTarget = 1;

        break;
      }
    }
  }

  update(){
    if (this.dead){
      // muerto: mantiene sensores pero no se mueve
      this.checkSensors(true);

      // suavizar el glow de recarga hacia 0
      this.refuelGlow += (0 - this.refuelGlow) * ROBOT_REFUEL_RELEASE;
      if (this.refuelGlow < 0.0008) this.refuelGlow = 0;
      return;
    }

    this.energy -= ENERGY_DRAIN_PER_FRAME;
    if (this.energy <= 0){ this.die(); return; }

    const hits = this.checkSensors(false);

    const anyWallHit = hits.some(h => h.hit && h.colorType === "wall");
    if (anyWallHit && this.turnCooldown === 0){
      const direction = Math.random() < 0.5 ? -1 : 1;
      const angleChange = (this.baseTurnAngle + Math.random()*this.randomTurnRange) * direction;
      this.angle += angleChange;
      this.turnCooldown = this.turnCooldownMax;
    }

    if (this.turnCooldown > 0) this.turnCooldown--;

    let steer = 0;
    if (hits.length > 1){
      for (let i=0;i<hits.length;i++){
        const h = hits[i];
        const side = (i/(hits.length-1))*2 - 1;
        const w = this.colorWeights[h.colorType] || 0;
        steer += w * side;
      }
    }
    this.angle += steer * this.colorTurnStrength;

    if (hits.length > 1 && this.memoryWeight > 0){
      let memSteer = 0;
      for (let i=0;i<hits.length;i++){
        const h = hits[i];
        const side = (i/(hits.length-1))*2 - 1;
        memSteer += -h.memoryLevel * side;
      }
      this.angle += memSteer * this.memoryWeight;
    }

    const newX = this.x + Math.cos(this.angle)*this.speed;
    const newY = this.y + Math.sin(this.angle)*this.speed;

    let collided = false;
    for (const w of walls){
      if (circleIntersectsRect(newX,newY,this.radius,w)){ collided=true; break; }
    }

    if (!collided){
      this.x = newX; this.y = newY;
    } else {
      const backX = this.x - Math.cos(this.angle)*this.speed*2;
      const backY = this.y - Math.sin(this.angle)*this.speed*2;
      this.x = backX; this.y = backY;
      this.angle += (Math.random()-0.5)*Math.PI;
      this.turnCooldown = this.turnCooldownMax;
    }

    this.history.push({x:this.x,y:this.y});
    if (this.history.length > this.historyMax) this.history.shift();

    this.memoryDropCounter++;
    if (this.memoryDropCounter >= this.memoryDropInterval){
      this.memoryDropCounter = 0;
      this.memory.push({x:this.x,y:this.y,alpha:1});
      if (this.memory.length > this.memoryMax) this.memory.shift();
    }
    for (let i=this.memory.length-1;i>=0;i--){
      const m = this.memory[i];
      m.alpha -= this.memoryFade;
      if (m.alpha <= 0) this.memory.splice(i,1);
    }

    // recarga (setea targets)
    this.tryRefuel();

    // suavizado del glow de recarga hacia target (attack/release)
    const a = (this.refuelGlowTarget > this.refuelGlow) ? ROBOT_REFUEL_ATTACK : ROBOT_REFUEL_RELEASE;
    this.refuelGlow += (this.refuelGlowTarget - this.refuelGlow) * a;
    if (this.refuelGlow < 0.0008) this.refuelGlow = 0;
  }

  checkSensors(isDead){
    this.sensorHits = [];
    const memoryRadius = 32;
    const memoryRadius2 = memoryRadius*memoryRadius;

    for (const relAngle of this.sensorAngles){
      const sensorDir = this.angle + relAngle;
      const start = {x:this.x,y:this.y};
      const end = {x:this.x + Math.cos(sensorDir)*this.sensorLength,
                   y:this.y + Math.sin(sensorDir)*this.sensorLength};

      let bestT = Infinity;
      let bestPoint = null;
      let bestType = "empty";

      for (const w of walls){
        const edges = [
          {a:{x:w.x,y:w.y}, b:{x:w.x+w.w,y:w.y}},
          {a:{x:w.x,y:w.y+w.h}, b:{x:w.x+w.w,y:w.y+w.h}},
          {a:{x:w.x,y:w.y}, b:{x:w.x,y:w.y+w.h}},
          {a:{x:w.x+w.w,y:w.y}, b:{x:w.x+w.w,y:w.y+w.h}}
        ];
        for (const edge of edges){
          const result = segmentIntersection(start,end,edge.a,edge.b);
          if (result && result.t < bestT){
            bestT = result.t;
            bestPoint = {x:result.x,y:result.y};
            bestType = "wall";
          }
        }
      }

      const hitGoal = rayCircleIntersection(start,end,GOAL_X,GOAL_Y,GOAL_RADIUS);
      if (hitGoal && hitGoal.t < bestT){
        bestT = hitGoal.t; bestPoint = {x:hitGoal.x,y:hitGoal.y}; bestType="goal";
      }

      const hitStart = rayCircleIntersection(start,end,START_X,START_Y,START_RADIUS);
      if (hitStart && hitStart.t < bestT){
        bestT = hitStart.t; bestPoint = {x:hitStart.x,y:hitStart.y}; bestType="start";
      }

      for (const f of fuels){
        const hitFuel = rayCircleIntersection(start,end,f.x,f.y,f.r*1.05);
        if (hitFuel && hitFuel.t < bestT){
          bestT = hitFuel.t; bestPoint = {x:hitFuel.x,y:hitFuel.y}; bestType="fuel";
        }
      }

      const probePoint = bestPoint || end;
      let memoryLevel = 0;
      if (!isDead){
        for (const m of this.memory){
          const dx = m.x - probePoint.x;
          const dy = m.y - probePoint.y;
          const d2 = dx*dx + dy*dy;
          if (d2 <= memoryRadius2) memoryLevel = Math.max(memoryLevel, m.alpha);
        }
      }

      this.sensorHits.push({
        angle: sensorDir,
        hit: !!bestPoint,
        from: start,
        to: bestPoint || end,
        colorType: bestType,
        memoryLevel
      });
    }
    return this.sensorHits;
  }

  hasReachedGoal(){
    if (this.dead) return false;
    const d2 = dist2(this.x,this.y,GOAL_X,GOAL_Y);
    return d2 < (GOAL_RADIUS*GOAL_RADIUS);
  }

  drawTrail(ctx){
    if (this.dead) return;
    if (this.history.length < 2) return;
    ctx.save();
    for (let i=1;i<this.history.length;i++){
      const p0=this.history[i-1], p1=this.history[i];
      const t=i/(this.history.length-1);
      const alpha = 0.01 + 2*t;
      const lightness = 35 + 25*t;
      ctx.strokeStyle = `hsla(${this.hue}, 80%, ${lightness}%, ${alpha})`;
      ctx.lineWidth = 1 + 0.7*t;
      ctx.beginPath();
      ctx.moveTo(p0.x,p0.y); ctx.lineTo(p1.x,p1.y);
      ctx.stroke();
    }
    ctx.restore();
  }

  drawMemory(ctx){
    if (this.dead) return;
    if (!this.memory.length) return;
    ctx.save();
    for (const m of this.memory){
      const r = this.radius * 1.4;
      const grad = ctx.createRadialGradient(m.x,m.y,0, m.x,m.y,r*2.4);
      grad.addColorStop(0, `hsla(${this.hue}, 85%, 70%, ${0.35*m.alpha})`);
      grad.addColorStop(1, `hsla(${this.hue}, 60%, 35%, 0)`);
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(m.x,m.y,r*2.4,0,Math.PI*2);
      ctx.fill();
    }
    ctx.restore();
  }

  draw(ctx){
    this.drawMemory(ctx);

    const energyRatio = Math.max(0, Math.min(1, this.energy / ENERGY_MAX));
    const rg = this.refuelGlow; // 0..1 (suavizado)

    // Glow (normal + refuel overlay)
    if (!this.dead){
      // glow normal (azul/hue)
      ctx.save();
      const baseGlowR = this.radius * (1.1 + 0.5*this.glowIntensity);
      ctx.globalAlpha = 0.15 + 0.15*this.glowIntensity;
      ctx.shadowColor = `hsla(${this.hue}, 100%, 70%, 0.9)`;
      ctx.shadowBlur = 6 + 10*this.glowIntensity;
      ctx.beginPath();
      ctx.arc(this.x, this.y, baseGlowR, 0, Math.PI*2);
      ctx.fillStyle = `hsla(${this.hue}, 90%, 55%, 0.55)`;
      ctx.fill();
      ctx.restore();

      // glow de recarga (amarillo) con rampa suave
      if (rg > 0.001){
        ctx.save();
        const boostR = this.radius * (1.5 + 2.6*rg);
        ctx.globalAlpha = 0.10 + 0.60*rg;
        ctx.shadowColor = "rgba(255, 216, 102, 0.95)";
        ctx.shadowBlur  = 14 + 32*rg;
        ctx.beginPath();
        ctx.arc(this.x, this.y, boostR, 0, Math.PI*2);
        ctx.fillStyle = `rgba(255, 216, 102, ${0.25 + 0.55*rg})`;
        ctx.fill();
        ctx.restore();
      }
    }

    this.drawTrail(ctx);

    // Sensores
    ctx.save();
    ctx.globalAlpha = this.dead ? 0.18 : 0.4;
    for (const s of this.sensorHits){
      ctx.beginPath();
      ctx.moveTo(s.from.x,s.from.y);
      ctx.lineTo(s.to.x,s.to.y);

      let stroke;
      if (s.colorType === "wall") stroke = this.dead ? "rgba(160,160,160,0.35)" : `hsla(${this.hue}, 70%, 55%, 0.7)`;
      else if (s.colorType === "goal") stroke = "rgba(80, 255, 160, 0.9)";
      else if (s.colorType === "start") stroke = "rgba(120, 220, 255, 0.9)";
      else if (s.colorType === "fuel") stroke = "rgba(255, 216, 102, 0.95)";
      else stroke = this.dead ? "rgba(140,140,140,0.22)" : `hsla(${this.hue}, 40%, 40%, 0.45)`;

      ctx.strokeStyle = stroke;
      ctx.lineWidth = 1.4;
      ctx.stroke();
    }
    ctx.restore();

    // Cuerpo
    ctx.save();
    ctx.translate(this.x,this.y);
    ctx.rotate(this.angle);

    let fillStyle;
    if (this.dead){
      const {h,s,l} = DEAD_GREY;
      const innerGrad = ctx.createRadialGradient(0,0,this.radius*0.1, 0,0,this.radius);
      innerGrad.addColorStop(0, `hsl(${h}, ${s}%, ${Math.min(80,l+20)}%)`);
      innerGrad.addColorStop(1, `hsl(${h}, ${s}%, ${l}%)`);
      fillStyle = innerGrad;
    } else {
      // mezcla suave hacia amarillo cuando recarga
      const innerGrad = ctx.createRadialGradient(0,0,this.radius*0.1, 0,0,this.radius);

      // centro: mezcla entre blanco-azulado y blanco-amarillo
      const c0 = (rg > 0)
        ? `rgba(255, 245, 200, ${0.65*rg})`
        : `rgba(255,255,255,0)`;
      const n0 = `hsl(${this.hue}, 80%, 75%)`;

      // borde: mezcla entre hue normal y amarillo
      const c1 = (rg > 0)
        ? `rgba(255, 196, 70, ${0.85*rg})`
        : `rgba(255,255,255,0)`;
      const n1 = `hsl(${this.hue}, 60%, 35%)`;

      innerGrad.addColorStop(0, n0);
      innerGrad.addColorStop(0.001, n0);
      innerGrad.addColorStop(0.20, c0); // overlay centro
      innerGrad.addColorStop(1, n1);
      innerGrad.addColorStop(0.999, n1);
      innerGrad.addColorStop(1, c1);    // overlay borde

      fillStyle = innerGrad;
    }

    ctx.beginPath();
    ctx.arc(0,0,this.radius,0,Math.PI*2);
    ctx.fillStyle = fillStyle;
    ctx.fill();
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = this.dead ? "rgba(0,0,0,0.35)" : "rgba(0,0,0,0.7)";
    ctx.stroke();

    // bisel
    ctx.beginPath();
    ctx.arc(0,0,this.radius*0.65,-Math.PI*0.1,Math.PI*1.1);
    ctx.fillStyle = this.dead ? "rgba(255,255,255,0.08)" : "rgba(255,255,255,0.25)";
    ctx.fill();

    // frente
    ctx.beginPath();
    ctx.moveTo(this.radius*0.3,0);
    ctx.lineTo(this.radius*0.95,0);
    ctx.strokeStyle = this.dead ? "rgba(255,255,255,0.22)" : "#ffffff";
    ctx.lineWidth = 2;
    ctx.stroke();

    ctx.restore();

    // aro energía
    ctx.save();
    ctx.beginPath();
    ctx.arc(this.x, this.y, this.radius + 3.2, -Math.PI/2, -Math.PI/2 + Math.PI*2*energyRatio);
    ctx.strokeStyle = this.dead
      ? "rgba(180,180,180,0.25)"
      : (rg > 0.01 ? `rgba(255,216,102,${0.35 + 0.55*rg})` : `hsla(${this.hue}, 95%, 72%, 0.55)`);
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.restore();
  }
}

/* ---------- Evolución ---------- */
function mutateValue(value, factor, minVal, maxVal){
  const delta = (Math.random()*2 - 1)*factor;
  let v = value*(1+delta);
  if (minVal !== undefined) v = Math.max(minVal,v);
  if (maxVal !== undefined) v = Math.min(maxVal,v);
  return v;
}

function mutateHue(hue, range=40){
  let h = hue + (Math.random()*2 - 1)*range;
  h %= 360;
  if (h < 0) h += 360;
  return h;
}

function mutateColorWeights(parentWeights){
  const result = {};
  const keys = ["wall","goal","start","fuel","empty"];
  for (const k of keys){
    const base = (parentWeights[k] !== undefined) ? parentWeights[k] : 0;
    result[k] = mutateValue(base, 0.35, -3.0, 3.0);
  }
  return result;
}

function mutateGenes(parent){
  const g = {
    radius: mutateValue(parent.radius, 0.2, 4, 22),
    speed: mutateValue(parent.speed, 0.22, 0.5, 4.0),
    sensorLength: mutateValue(parent.sensorLength, 0.25, 40, 260),
    turnCooldownMax: Math.round(mutateValue(parent.turnCooldownMax, 0.3, 5, 80)),
    baseTurnAngle: mutateValue(parent.baseTurnAngle, 0.25, 0.08, 1.2),
    randomTurnRange: mutateValue(parent.randomTurnRange, 0.3, 0.2, 2.5),
    sensorAngles: parent.sensorAngles.slice(),
    hue: mutateHue(parent.hue !== undefined ? parent.hue : 200, 40),
    colorTurnStrength: mutateValue(parent.colorTurnStrength || 0.06, 0.3, 0.01, 0.2),
    glowIntensity: mutateValue(parent.glowIntensity || 1.0, 0.4, 0.1, 2.0),
    colorWeights: mutateColorWeights(parent.colorWeights || defaultGenes.colorWeights),
    memoryFade: mutateValue(parent.memoryFade || 0.025, 0.3, 0.005, 0.08),
    memoryWeight: mutateValue(parent.memoryWeight || 0.9, 0.35, 0.0, 1.5)
  };

  for (let i=0;i<g.sensorAngles.length;i++){
    g.sensorAngles[i] += (Math.random()*2 - 1)*0.09;
  }
  g.sensorAngles.sort((a,b)=>a-b);
  return g;
}

function extractGenesFromRobot(robot){
  return {
    radius: robot.radius,
    speed: robot.speed,
    sensorLength: robot.sensorLength,
    sensorAngles: robot.sensorAngles.slice(),
    turnCooldownMax: robot.turnCooldownMax,
    baseTurnAngle: robot.baseTurnAngle,
    randomTurnRange: robot.randomTurnRange,
    hue: robot.hue,
    colorTurnStrength: robot.colorTurnStrength,
    glowIntensity: robot.glowIntensity,
    colorWeights: { ...robot.colorWeights },
    memoryFade: robot.memoryFade,
    memoryWeight: robot.memoryWeight
  };
}

/* ---------- Colisiones robot-robot (no se solapan) ---------- */
function resolveRobotCollisions(){
  const cell = Math.max(18, cellSize * 0.35);
  const inv = 1 / cell;

  const buckets = new Map();
  function key(ix,iy){ return (ix<<16) ^ (iy & 0xffff); }

  for (let i=0;i<robots.length;i++){
    const r = robots[i];
    const ix = Math.floor(r.x * inv);
    const iy = Math.floor(r.y * inv);
    const k = key(ix,iy);
    if (!buckets.has(k)) buckets.set(k, []);
    buckets.get(k).push(i);
  }

  for (let i=0;i<robots.length;i++){
    const a = robots[i];
    const aix = Math.floor(a.x * inv);
    const aiy = Math.floor(a.y * inv);

    for (let dy=-1;dy<=1;dy++){
      for (let dx=-1;dx<=1;dx++){
        const k = key(aix+dx, aiy+dy);
        const list = buckets.get(k);
        if (!list) continue;

        for (const j of list){
          if (j <= i) continue;
          const b = robots[j];

          const minDist = a.radius + b.radius;
          const dxp = b.x - a.x;
          const dyp = b.y - a.y;
          const d2 = dxp*dxp + dyp*dyp;

          if (d2 === 0) continue;
          if (d2 >= minDist*minDist) continue;

          const d = Math.sqrt(d2);
          const overlap = (minDist - d);

          const nx = dxp / d;
          const ny = dyp / d;

          let axMove = 0, ayMove = 0, bxMove = 0, byMove = 0;

          if (a.dead && b.dead){
            continue;
          } else if (a.dead && !b.dead){
            bxMove = nx * overlap;
            byMove = ny * overlap;
          } else if (!a.dead && b.dead){
            axMove = -nx * overlap;
            ayMove = -ny * overlap;
          } else {
            axMove = -nx * (overlap * 0.5);
            ayMove = -ny * (overlap * 0.5);
            bxMove =  nx * (overlap * 0.5);
            byMove =  ny * (overlap * 0.5);
          }

          if (axMove || ayMove){
            const px = a.x, py = a.y;
            a.x += axMove; a.y += ayMove;
            let hitWall = false;
            for (const w of walls){
              if (circleIntersectsRect(a.x,a.y,a.radius,w)){ hitWall=true; break; }
            }
            if (hitWall){ a.x = px; a.y = py; }
          }

          if (bxMove || byMove){
            const px = b.x, py = b.y;
            b.x += bxMove; b.y += byMove;
            let hitWall = false;
            for (const w of walls){
              if (circleIntersectsRect(b.x,b.y,b.radius,w)){ hitWall=true; break; }
            }
            if (hitWall){ b.x = px; b.y = py; }
          }
        }
      }
    }
  }
}

/* ---------- Gestión de simulación ---------- */
function resetSimulation(){
  robots = [];
  const parentGenes = bestGenes || defaultGenes;

  createMaze();

  const startCellX = START_X;
  const startCellY = START_Y;
  const spread = cellSize * 0.25;

  for (let i=0;i<NUM_ROBOTS;i++){
    const genes = mutateGenes(parentGenes);
    const startX = startCellX + (Math.random()*2 - 1)*spread;
    const startY = startCellY + (Math.random()*2 - 1)*spread;
    robots.push(new Robot(startX,startY,genes));
  }

  generationStartTime = performance.now();
}

function updateInfo(){
  let alive = 0, dead = 0;
  for (const r of robots){ r.dead ? dead++ : alive++; }

  let text = `<strong>Generación:</strong> ${generation}
Robots: ${NUM_ROBOTS}  (vivos: ${alive}, muertos: ${dead})
Puntos recarga: ${fuels.length}`;

  if (bestGenes && generationTimes.length > 0){
    const lastTime = generationTimes[generationTimes.length-1];
    const bestTime = Math.min(...generationTimes);
    const cw = bestGenes.colorWeights || {};

    text += `

<strong>Mejores genes (ganador generación anterior):</strong>
· color (hue): ${bestGenes.hue.toFixed(1)}°
· radio: ${bestGenes.radius.toFixed(2)}
· velocidad: ${bestGenes.speed.toFixed(2)}
· longitud sensores: ${bestGenes.sensorLength.toFixed(1)}
· enfriamiento giro: ${bestGenes.turnCooldownMax}
· ángulo base giro: ${bestGenes.baseTurnAngle.toFixed(2)}
· rango giro aleatorio: ${bestGenes.randomTurnRange.toFixed(2)}
· fuerza giro por color: ${bestGenes.colorTurnStrength.toFixed(3)}
· glow: ${bestGenes.glowIntensity.toFixed(2)}
· memoria fade: ${bestGenes.memoryFade.toFixed(3)}
· peso memoria: ${bestGenes.memoryWeight.toFixed(2)}

<strong>Respuesta a colores:</strong>
· pared (wall): ${ (cw.wall ?? 0).toFixed(2) }
· meta  (goal): ${ (cw.goal ?? 0).toFixed(2) }
· inicio(start): ${ (cw.start ?? 0).toFixed(2) }
· recarga(fuel): ${ (cw.fuel ?? 0).toFixed(2) }
· vacío(empty): ${ (cw.empty ?? 0).toFixed(2) }

Tiempo última generación: ${lastTime.toFixed(2)} s
Mejor tiempo histórico: ${bestTime.toFixed(2)} s`;
  } else {
    text += `

<strong>Mejores genes:</strong> ninguno todavía (evolucionando...)`;
  }

  infoDiv.innerHTML = text;
}

/* ---------- Gráfico ---------- */
function drawChart(){
  chartCtx.clearRect(0,0,chartCanvas.width,chartCanvas.height);
  if (!generationTimes.length) return;

  const chartWidth  = chartCanvas.width;
  const chartHeight = chartCanvas.height;

  const padding = 10;
  const innerX = 40;
  const innerY = 26;
  const innerWidth  = chartWidth - innerX - padding;
  const innerHeight = chartHeight - innerY - 18;

  const bgGrad = chartCtx.createLinearGradient(0,0,0,chartHeight);
  bgGrad.addColorStop(0,"rgba(10,16,30,0.96)");
  bgGrad.addColorStop(1,"rgba(5,8,18,0.96)");
  chartCtx.fillStyle = bgGrad;
  chartCtx.fillRect(0,0,chartWidth,chartHeight);

  chartCtx.strokeStyle = "rgba(120,160,255,0.7)";
  chartCtx.lineWidth = 1;
  chartCtx.strokeRect(0.5,0.5,chartWidth-1,chartHeight-1);

  chartCtx.fillStyle = "#e5eeff";
  chartCtx.font = "11px system-ui";
  chartCtx.textAlign = "left";
  chartCtx.fillText("Tiempo hasta la meta (s)", 8, 16);

  const maxBars = 30;
  const data = generationTimes.slice(-maxBars);
  const maxTime = Math.max(...data);
  const minTime = Math.min(...data);
  const bestTime = Math.min(...generationTimes);

  chartCtx.strokeStyle = "rgba(255,255,255,0.08)";
  chartCtx.lineWidth = 1;
  const gridLines = 4;
  for (let i=0;i<=gridLines;i++){
    const gy = innerY + (innerHeight/gridLines)*i;
    chartCtx.beginPath();
    chartCtx.moveTo(innerX,gy);
    chartCtx.lineTo(innerX+innerWidth,gy);
    chartCtx.stroke();
  }

  chartCtx.strokeStyle = "rgba(200,220,255,0.6)";
  chartCtx.beginPath();
  chartCtx.moveTo(innerX,innerY);
  chartCtx.lineTo(innerX,innerY+innerHeight);
  chartCtx.lineTo(innerX+innerWidth,innerY+innerHeight);
  chartCtx.stroke();

  chartCtx.fillStyle = "#c5d7ff";
  chartCtx.textAlign = "right";
  chartCtx.fillText(maxTime.toFixed(1), innerX-4, innerY+9);
  chartCtx.fillText(minTime.toFixed(1), innerX-4, innerY+innerHeight);

  const barCount = data.length;
  const barGap = 2;
  const barWidth = Math.max(3, (innerWidth - barGap*(barCount-1))/barCount);

  chartCtx.textAlign = "center";
  for (let i=0;i<barCount;i++){
    const t = data[i];
    const norm = t / maxTime;
    const barH = norm * innerHeight;
    const x = innerX + i*(barWidth+barGap);
    const y = innerY + innerHeight - barH;

    const gGlobalIndex = generationTimes.length - data.length + i;
    const isBest = generationTimes[gGlobalIndex] === bestTime;

    const grad = chartCtx.createLinearGradient(x,y,x,y+barH);
    if (isBest){
      grad.addColorStop(0,"rgba(102,255,204,0.95)");
      grad.addColorStop(1,"rgba(46,204,113,0.85)");
    } else {
      grad.addColorStop(0,"rgba(80,190,255,0.95)");
      grad.addColorStop(1,"rgba(0,118,210,0.85)");
    }
    chartCtx.fillStyle = grad;
    chartCtx.fillRect(x,y,barWidth,barH);

    if ((i+1)%5===0 || i===barCount-1){
      const genIndex = generationTimes.length - data.length + i + 1;
      chartCtx.fillStyle = "#dde6ff";
      chartCtx.font = "9px system-ui";
      chartCtx.fillText(genIndex, x + barWidth/2, innerY + innerHeight + 11);
    }
  }
}

/* ---------- Bucle principal ---------- */
function loop(){
  simCtx.clearRect(0,0,simCanvas.width,simCanvas.height);

  drawBackgroundGrid();
  drawWalls();
  drawStart();
  drawGoal();
  drawFuels();

  let winner = null;

  for (const r of robots) r.update();
  resolveRobotCollisions();

  for (const r of robots){
    r.draw(simCtx);
    if (!winner && r.hasReachedGoal()) winner = r;
  }

  if (winner){
    const now = performance.now();
    const elapsedSeconds = (now - generationStartTime) / 1000.0;

    generationTimes.push(elapsedSeconds);
    bestGenes = extractGenesFromRobot(winner);
    generation++;

    resetSimulation();
    updateInfo();
  }

  drawChart();
  requestAnimationFrame(loop);
}

/* ---------- Inicio ---------- */
resetSimulation();
updateInfo();
loop();
</script>
</body>
</html>
```
## Entorno 3d mover camara
**Camara movimiento.html**
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Parallax 3d</title>

  <script src="https://aframe.io/releases/1.5.0/aframe.min.js"></script>
  <script src="https://cdn.jsdelivr.net/gh/feiss/aframe-environment-component/dist/aframe-environment-component.min.js"></script>

  <style>
    html, body {
      margin: 0;
      padding: 0;
      overflow: hidden;
      background: #000;
      font-family: sans-serif;
      color: #eee;
    }
    #video {
      position: fixed;
      bottom: 10px;
      right: 10px;
      width: 220px;
      transform: scaleX(-1);
      opacity: 0.4;
      z-index: 10;
      border: 2px solid #444;
      border-radius: 4px;
    }
    #ui {
      position: fixed;
      top: 10px;
      left: 10px;
      z-index: 20;
      background: rgba(0,0,0,0.6);
      padding: 8px 10px;
      border-radius: 6px;
      border: 1px solid #555;
      font-size: 14px;
    }
    #parallaxRange {
      width: 150px;
      vertical-align: middle;
    }
    label {
      margin-right: 4px;
    }
  </style>
</head>
<body>
  <div id="ui">
    <label for="parallaxRange">Parallax:</label>
    <input id="parallaxRange" type="range" min="0" max="5" step="0.05" value="1" />
    <span id="parallaxValue">1.00</span>
  </div>

  <video id="video" autoplay playsinline></video>

  <a-scene
    renderer="antialias: true; colorManagement: true; physicallyCorrectLights: true; shadowMap.enabled: true; shadowMap.type: pcfsoft"
  >
    <a-entity environment="
      preset: default;
      ground: flat;
      groundYScale: 1;
      groundTexture: none;
      groundColor: #303030;
      groundColor2: #404040;
      skyType: gradient;
      skyColor: #88ccee;
      horizonColor: #ffffff;
      lighting: none;
    "></a-entity>

    <a-plane position="0 0 0"
             rotation="-90 0 0"
             width="100"
             height="100"
             color="#404040"
             shadow="receive: true">
    </a-plane>

    <a-entity id="rig" position="0 1.6 0">
      <a-entity id="cam" camera look-controls="enabled: false"></a-entity>
    </a-entity>

    <a-entity id="sunTarget" position="0 0 0"></a-entity>

    <a-entity light="type: directional; intensity: 1.1; castShadow: true"
              position="4 8 6"
              target="#sunTarget">
    </a-entity>

    <a-entity light="type: ambient; intensity: 0.35; color: #ffffff"></a-entity>


    <a-sphere position="-2 0.5 -3"
              radius="0.5"
              color="#ff4444"
              shadow="cast: true; receive: true"></a-sphere>

    <a-box position="-0.8 0.4 -2.2"
           depth="0.6" height="0.6" width="0.6"
           color="#44ff44"
           shadow="cast: true; receive: true"></a-box>

    <a-cylinder position="0.6 0.5 -3.2"
                radius="0.3" height="1"
                color="#4444ff"
                shadow="cast: true; receive: true"></a-cylinder>

    <a-torus-knot position="1.8 0.9 -4"
                   radius="0.6"
                   radius-tubular="0.08"
                   color="#ffcc00"
                   shadow="cast: true; receive: true"></a-torus-knot>

    <a-dodecahedron position="3 0.7 -5"
                    radius="0.5"
                    color="#ff00aa"
                    shadow="cast: true; receive: true"></a-dodecahedron>

    <a-octahedron position="-3 0.7 -4.5"
                  radius="0.4"
                  color="#00ffcc"
                  shadow="cast: true; receive: true"></a-octahedron>

    <a-ring position="-1 0.01 -6"
            rotation="-90 0 0"
            radius-inner="0.3"
            radius-outer="0.6"
            color="#ffdddd"
            shadow="cast: true; receive: true"></a-ring>

    <a-cone position="1 0.9 -6.5"
            radius-bottom="0.5"
            radius-top="0.0"
            height="1.2"
            color="#ffddff"
            shadow="cast: true; receive: true"></a-cone>

    <a-torus position="0 0.8 -5.2"
             rotation="0 45 0"
             radius="0.7"
             radius-tubular="0.12"
             color="#88aaff"
             shadow="cast: true; receive: true"></a-torus>

    <a-sphere position="-1 0.2 -2.5" radius="0.12" color="#ffffff" shadow="cast: true; receive: true"></a-sphere>
    <a-sphere position="-0.5 0.2 -3.5" radius="0.12" color="#ffffff" shadow="cast: true; receive: true"></a-sphere>
    <a-sphere position="0 0.2 -4.5"   radius="0.12" color="#ffffff" shadow="cast: true; receive: true"></a-sphere>
    <a-sphere position="0.5 0.2 -5.5" radius="0.12" color="#ffffff" shadow="cast: true; receive: true"></a-sphere>
    <a-sphere position="1 0.2 -6.5"   radius="0.12" color="#ffffff" shadow="cast: true; receive: true"></a-sphere>
  </a-scene>

  <script type="module">
    import {
      FaceLandmarker,
      FilesetResolver
    } from "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.0/vision_bundle.js";

    const video          = document.getElementById("video");
    const parallaxRange  = document.getElementById("parallaxRange");
    const parallaxValue  = document.getElementById("parallaxValue");
    const rigEl          = document.getElementById("rig");

    let faceLandmarker   = null;
    let running          = false;
    let lastVideoTime    = -1;
    let parallaxFactor   = 1.0;

    const baseCam = { x: 0, y: 1.0, z: 0 };

    let baselineScale = null;

    parallaxRange.addEventListener("input", (e) => {
      parallaxFactor = parseFloat(e.target.value);
      parallaxValue.textContent = parallaxFactor.toFixed(2);
    });

    async function initCamera() {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480 }
      });
      video.srcObject = stream;
      return new Promise(resolve => {
        video.onloadedmetadata = () => resolve();
      });
    }

    async function initFaceLandmarker() {
      const filesetResolver = await FilesetResolver.forVisionTasks(
        "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.0/wasm"
      );

      faceLandmarker = await FaceLandmarker.createFromOptions(filesetResolver, {
        baseOptions: {
          modelAssetPath:
            "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task"
        },
        runningMode: "VIDEO",
        numFaces: 1
      });
    }

    function getHeadMetrics(landmarks) {
      if (!landmarks || !landmarks.length) return null;

      let sumX = 0;
      let sumY = 0;
      const n = landmarks.length;
      for (let i = 0; i < n; i++) {
        sumX += landmarks[i].x;
        sumY += landmarks[i].y;
      }
      const center = { x: sumX / n, y: sumY / n };

      let scale = 0.1;
      const leftIdx  = 33;
      const rightIdx = 263;
      if (landmarks[leftIdx] && landmarks[rightIdx]) {
        const lx = landmarks[leftIdx].x;
        const ly = landmarks[leftIdx].y;
        const rx = landmarks[rightIdx].x;
        const ry = landmarks[rightIdx].y;
        scale = Math.hypot(rx - lx, ry - ly);
      }

      return { center, scale };
    }


    function mapHeadToCamera(center, scale) {
      const nx = center.x * 2 - 1;
      const ny = center.y * 2 - 1;

      const baseMaxX = 0.5;
      const baseMaxY = 0.3;

      const maxX = baseMaxX * parallaxFactor;
      const maxY = baseMaxY * parallaxFactor;

      const dx = -nx * maxX;

      const dy = -ny * maxY;

      if (scale && !baselineScale) baselineScale = scale;
      let dz = 0;
      if (scale && baselineScale) {
        let rel = scale / baselineScale;
        rel = Math.min(Math.max(rel, 0.7), 1.3); 
        const delta = rel - 1.0;
        const maxDepthOffset = 0.8;              
        dz = -delta * maxDepthOffset * parallaxFactor;
      }

      return {
        x: baseCam.x + dx,
        y: baseCam.y + dy,
        z: baseCam.z + dz
      };
    }

    function smooth(prev, next, factor) {
      if (!prev) return next;
      return {
        x: prev.x + (next.x - prev.x) * factor,
        y: prev.y + (next.y - prev.y) * factor,
        z: prev.z + (next.z - prev.z) * factor
      };
    }

    let smoothedCamPos = null;

    async function processVideoFrame() {
      if (!running) return;

      const nowMs = performance.now();
      const videoTime = video.currentTime;

      if (videoTime === lastVideoTime) {
        requestAnimationFrame(processVideoFrame);
        return;
      }
      lastVideoTime = videoTime;

      const results = faceLandmarker.detectForVideo(video, nowMs);

      if (results.faceLandmarks && results.faceLandmarks.length > 0) {
        const landmarks = results.faceLandmarks[0];
        const metrics = getHeadMetrics(landmarks);

        if (metrics) {
          const camPos = mapHeadToCamera(metrics.center, metrics.scale);
          smoothedCamPos = smooth(smoothedCamPos, camPos, 0.18);

          rigEl.setAttribute(
            "position",
            `${smoothedCamPos.x} ${smoothedCamPos.y} ${smoothedCamPos.z}`
          );
        }
      }

      requestAnimationFrame(processVideoFrame);
    }

    (async function start() {
      try {
        await initCamera();
        await initFaceLandmarker();
        running = true;
        processVideoFrame();
      } catch (e) {
        console.error("Error initializing:", e);
      }
    })();
  </script>
</body>
</html>
```
## Informe
## Openstreetmap
**MapaManos.html**
```html
<!DOCTYPE html>
<html>
<head>
    <title>OpenStreetMap + MediaPipe Hands Demo</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet"
          href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
          integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
          crossorigin=""/>
    <script src="https://cdn.jsdelivr.net/npm/@mediapipe/hands/hands.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/@mediapipe/drawing_utils/drawing_utils.js"></script>
    <style>
        body {
            margin: 0;
            padding: 0;
            overflow: hidden;
        }
        #map {
            width: 100%;
            height: 100vh;
        }
        #webcam {
            position: absolute;
            bottom: 10px;
            right: 10px;
            width: 200px;
            height: 150px;
            border: 2px solid #333;
            border-radius: 5px;
            z-index: 1000;
        }
        #debugCanvas {
            position: absolute;
            bottom: 10px;
            right: 220px;
            width: 200px;
            height: 150px;
            border: 2px solid #333;
            border-radius: 5px;
            z-index: 1000;
        }
        #gestureStatus {
            position: absolute;
            top: 10px;
            right: 10px;
            background: rgba(0,0,0,0.7);
            color: white;
            padding: 10px;
            border-radius: 5px;
            z-index: 1000;
            font-family: monospace;
        }
    </style>
</head>
<body>
    <div id="map"></div>
    <div id="gestureStatus">Waiting for hand...</div>
    <video id="webcam" class="input_video" autoplay playsinline muted></video>
    <canvas id="debugCanvas"></canvas>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
            integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo="
            crossorigin=""></script>
    <script>
        // Initialize the map
        const map = L.map('map', {
            zoomSnap: 0,
            zoomDelta: 0.5,
            wheelDebounceTime: 0,
            wheelPxPerZoomLevel: 120
        }).setView([39.4759729, -0.418349], 13);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);
        L.marker([39.4759729, -0.418349]).addTo(map)
            .bindPopup('Valencia, Spain')
            .openPopup();

        const debugCanvas = document.getElementById('debugCanvas');
        const debugCtx = debugCanvas.getContext('2d');
        const gestureStatus = document.getElementById('gestureStatus');

        // State
        let isDragging = false;
        let isZooming = false;
        let lastHandX = 0;
        let lastHandY = 0;
        let filteredHandX = null;
        let filteredHandY = null;
        const dragSensitivity = 800;
        const PAN_SMOOTHING = 0.25; // 0–1, lower = smoother

        // ============ SMOOTH ZOOM SYSTEM ============
        const zoomSensitivity = 8;

        // Exponential moving average for distance smoothing
        let smoothedDistance = 0;
        let filteredDistance = null;
        const DISTANCE_SMOOTHING = 0.12; // 0–1, lower = smoother

        let initialZoomDistance = 0;
        let initialZoomLevel = 0;

        // Target zoom with interpolation
        let targetZoom = 13;
        let currentDisplayZoom = 13;
        const ZOOM_LERP_FACTOR = 0.1;   // How fast to interpolate (0-1, lower = smoother)
        const ZOOM_DEAD_ZONE = 0.01;    // Ignore tiny distance changes

        // Animation loop for smooth zoom interpolation
        function animateZoom() {
            if (Math.abs(targetZoom - currentDisplayZoom) > 0.001) {
                // Lerp towards target
                currentDisplayZoom += (targetZoom - currentDisplayZoom) * ZOOM_LERP_FACTOR;

                // Clamp to valid range
                if (!isFinite(currentDisplayZoom)) {
                    // hard reset if something went wrong
                    currentDisplayZoom = map.getZoom();
                    targetZoom = currentDisplayZoom;
                }
                currentDisplayZoom = Math.max(1, Math.min(18, currentDisplayZoom));

                // Apply to map (disable Leaflet animation, we already interpolate)
                map.setZoom(currentDisplayZoom, { animate: false });
            }
            requestAnimationFrame(animateZoom);
        }
        animateZoom();

        // Get smoothed distance using exponential smoothing (low-pass filter)
        function getSmoothedDistance(rawDistance) {
            if (filteredDistance === null) {
                filteredDistance = rawDistance;
            } else {
                filteredDistance += DISTANCE_SMOOTHING * (rawDistance - filteredDistance);
            }
            return filteredDistance;
        }
        // ============================================

        // MediaPipe Hands setup
        const videoElement = document.getElementById('webcam');
        const hands = new Hands({
            locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands@0.4.1646424915/${file}`
        });
        hands.setOptions({
            maxNumHands: 2,
            modelComplexity: 1,
            minDetectionConfidence: 0.5,
            minTrackingConfidence: 0.5
        });

        hands.onResults((results) => {
            // Draw landmarks
            debugCtx.clearRect(0, 0, debugCanvas.width, debugCanvas.height);
            debugCtx.drawImage(results.image, 0, 0, debugCanvas.width, debugCanvas.height);
            if (results.multiHandLandmarks) {
                for (const landmarks of results.multiHandLandmarks) {
                    drawConnectors(debugCtx, landmarks, HAND_CONNECTIONS, {color: '#00FF00', lineWidth: 2});
                    drawLandmarks(debugCtx, landmarks, {radius: 2, color: '#FF0000'});
                }
            }

            if (results.multiHandLandmarks && results.multiHandLandmarks.length > 0) {
                const numHands = results.multiHandLandmarks.length;

                // Check if hands are closed (thumb-index pinch)
                const areHandsClosed = [];
                for (let i = 0; i < numHands; i++) {
                    const landmarks = results.multiHandLandmarks[i];
                    const thumbTip = landmarks[4];
                    const indexTip = landmarks[8];
                    const distance = Math.sqrt(
                        Math.pow(thumbTip.x - indexTip.x, 2) +
                        Math.pow(thumbTip.y - indexTip.y, 2)
                    );
                    areHandsClosed.push(distance < 0.08);
                }

                // TWO HANDS CLOSED: Pinch to zoom
                if (numHands === 2 && areHandsClosed[0] && areHandsClosed[1]) {
                    const hand1 = results.multiHandLandmarks[0][4];
                    const hand2 = results.multiHandLandmarks[1][4];

                    const rawDistance = Math.sqrt(
                        Math.pow(hand1.x - hand2.x, 2) +
                        Math.pow(hand1.y - hand2.y, 2)
                    );

                    // Smoothed distance
                    smoothedDistance = getSmoothedDistance(rawDistance);

                    // Ensure we have a reasonable initial distance
                    if (!isZooming) {
                        isZooming = true;
                        isDragging = false;

                        if (!smoothedDistance || smoothedDistance <= 0) {
                            // Avoid zero / invalid initial distance
                            initialZoomDistance = 0.05;
                        } else {
                            initialZoomDistance = smoothedDistance;
                        }

                        initialZoomLevel = map.getZoom();
                        targetZoom = initialZoomLevel;
                        currentDisplayZoom = initialZoomLevel;

                        gestureStatus.textContent = "🔍 ZOOM MODE";
                    } else {
                        // Compute zoom only if initial distance is valid
                        if (initialZoomDistance > 0) {
                            const distanceRatio = smoothedDistance / initialZoomDistance;
                            const distanceDelta = smoothedDistance - initialZoomDistance;

                            if (isFinite(distanceRatio) && distanceRatio > 0) {
                                // Apply dead zone to prevent jitter
                                if (Math.abs(distanceDelta) > ZOOM_DEAD_ZONE) {
                                    // INVERTED LOGIC:
                                    // Hands apart (ratio > 1) => zoom IN
                                    // Hands together (ratio < 1) => zoom OUT
                                    const zoomChange = Math.log2(distanceRatio) * zoomSensitivity;
                                    let newTarget = initialZoomLevel + zoomChange;

                                    if (!isFinite(newTarget)) {
                                        // Guard against NaN / Infinity
                                        newTarget = initialZoomLevel;
                                    }

                                    // Clamp the target zoom
                                    targetZoom = Math.max(1, Math.min(18, newTarget));
                                }

                                gestureStatus.innerHTML =
                                    `🔍 ZOOM: ${currentDisplayZoom.toFixed(2)}<br>` +
                                    `Target: ${targetZoom.toFixed(2)}<br>` +
                                    `Ratio: ${distanceRatio.toFixed(3)}`;
                            }
                        }
                    }
                }
                // ONE HAND CLOSED: Drag to pan
                else if (numHands >= 1 && areHandsClosed[0]) {
                    const landmarks = results.multiHandLandmarks[0];
                    const thumbTip = landmarks[4];

                    if (!isDragging) {
                        isDragging = true;
                        isZooming = false;

                        // Initialise hand filters
                        filteredHandX = thumbTip.x;
                        filteredHandY = thumbTip.y;
                        lastHandX = filteredHandX;
                        lastHandY = filteredHandY;

                        // Reset zoom smoothing state
                        filteredDistance = null;

                        gestureStatus.textContent = "✋ DRAG MODE";
                    } else {
                        // Smooth hand position
                        filteredHandX += PAN_SMOOTHING * (thumbTip.x - filteredHandX);
                        filteredHandY += PAN_SMOOTHING * (thumbTip.y - filteredHandY);

                        const deltaX = (filteredHandX - lastHandX) * dragSensitivity;
                        const deltaY = (filteredHandY - lastHandY) * dragSensitivity;

                        if (Math.abs(deltaX) > 1 || Math.abs(deltaY) > 1) {
                            map.panBy([deltaX, -deltaY], { animate: false });
                            gestureStatus.innerHTML =
                                `✋ DRAG<br>` +
                                `ΔX: ${deltaX.toFixed(1)} ΔY: ${deltaY.toFixed(1)}`;
                        }

                        lastHandX = filteredHandX;
                        lastHandY = filteredHandY;
                    }
                } else {
                    gestureStatus.textContent = "👋 Hand open";
                    isDragging = false;
                    isZooming = false;
                    filteredDistance = null;
                    filteredHandX = null;
                    filteredHandY = null;
                }
            } else {
                gestureStatus.textContent = "Waiting for hand...";
                isDragging = false;
                isZooming = false;
                filteredDistance = null;
                filteredHandX = null;
                filteredHandY = null;
            }
        });

        const camera = new Camera(videoElement, {
            onFrame: async () => {
                await hands.send({ image: videoElement });
            },
            width: 640,
            height: 480
        });
        camera.start();
    </script>
</body>
</html> 
```
## Python Blender
**PythonBlender.py**
```python
import bpy
import bmesh
import math
from mathutils import Vector, Euler
from mathutils.noise import noise as perlin_noise

# =====================================================
# FULL SCENE WIPE (objects + datablocks)
# =====================================================
def full_wipe_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False, confirm=False)

    for col in list(bpy.data.collections):
        try:
            bpy.data.collections.remove(col)
        except:
            pass

    for block in (
        bpy.data.meshes,
        bpy.data.materials,
        bpy.data.textures,
        bpy.data.images,
        bpy.data.lights,
        bpy.data.cameras,
        bpy.data.curves,
        bpy.data.worlds,
    ):
        for datablock in list(block):
            try:
                block.remove(datablock)
            except:
                pass

    for _ in range(5):
        try:
            bpy.ops.outliner.orphans_purge(do_recursive=True, do_local_ids=True, do_linked_ids=True)
        except:
            try:
                bpy.ops.outliner.orphans_purge(do_recursive=True)
            except:
                break


# =====================================================
# TERRAIN CONFIG
# =====================================================
GRID_X = 200
GRID_Y = 200
CELL_SIZE = 1.0

NOISE_SCALE = 0.035
HEIGHT = 10.0
OCTAVES = 6
LACUNARITY = 2.0
GAIN = 0.5

CENTER_GRID = True

TERRAIN_NAME = "Terrain"
TERRAIN_COLLECTION = "Terrain"

SEA_LEVEL = 0.0

# Color bands (RGBA)
COLOR_DEEP_WATER  = (0.02, 0.08, 0.25, 1.0)
COLOR_SHALLOW     = (0.08, 0.25, 0.55, 1.0)
COLOR_SAND        = (0.78, 0.72, 0.52, 1.0)
COLOR_MOUNTAIN    = (0.22, 0.28, 0.20, 1.0)
COLOR_SNOW        = (0.95, 0.95, 0.95, 1.0)

SUBSURF_LEVEL = 1

# Camera
CAM_LOC = (100.0, 0.0, 3.5)
CAM_ROT_DEG = (90.0, 0.0, 90.0)

# Water volume box
WATER_MARGIN = 25.0
WATER_DEPTH = 20.0           # how deep the water volume goes below SEA_LEVEL
WATER_SURFACE_THICKNESS = 0.0  # set >0 if you want a "cap" slab; 0 uses only volume
WATER_IOR = 1.333
WATER_DENSITY = 0.08         # overall scattering density (inside-water look)
WATER_ANISOTROPY = 0.65      # forward scattering
WATER_ABS_COLOR = (0.02, 0.10, 0.16, 1.0)  # absorption tint
WATER_ABS_DENSITY = 0.35

# Clouds
CLOUD_ALTITUDE = 5.0
CLOUD_SIZE = 520.0
CLOUD_THICKNESS = 55.0

CLOUD_THIN_Z = CLOUD_ALTITUDE + 10.0
CLOUD_THIN_THICKNESS = 0.7
CLOUD_THIN_SUBDIV = 6
CLOUD_THIN_DISP_STRENGTH = 1.2
CLOUD_THIN_NOISE_SCALE = 30.0

CLOUD_DENSITY = 0.06
CLOUD_ANISOTROPY = 0.35
CLOUD_DETAIL_SCALE = 6.0
CLOUD_BASE_SCALE = 0.01
CLOUD_THRESHOLD = 0.52
CLOUD_SOFTNESS = 0.22


# =====================================================
# UTIL
# =====================================================
def lerp(a, b, t):
    return a + (b - a) * t

def lerp4(c1, c2, t):
    return (
        lerp(c1[0], c2[0], t),
        lerp(c1[1], c2[1], t),
        lerp(c1[2], c2[2], t),
        lerp(c1[3], c2[3], t),
    )

def clamp01(x):
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)

def safe_set_input(bsdf, key_candidates, value):
    keys = set(bsdf.inputs.keys())
    for k in key_candidates:
        if k in keys and bsdf.inputs.get(k) is not None:
            bsdf.inputs[k].default_value = value
            return True
    return False

def fbm(x, y):
    amp = 1.0
    freq = 1.0
    total = 0.0
    norm = 0.0
    for _ in range(OCTAVES):
        n = perlin_noise(Vector((x * NOISE_SCALE * freq,
                                 y * NOISE_SCALE * freq,
                                 0.0)))
        total += n * amp
        norm += amp
        amp *= GAIN
        freq *= LACUNARITY
    return total / norm if norm else 0.0


# =====================================================
# HEIGHT -> COLOR
# =====================================================
def color_from_height(h, hmin, hmax):
    t_sea   = SEA_LEVEL
    t_shal  = lerp(hmin, t_sea, 0.55)
    t_deep  = hmin
    t_mtn   = lerp(t_sea, hmax, 0.55)
    t_snow  = lerp(t_sea, hmax, 0.82)

    if h <= t_shal:
        t = clamp01((h - t_deep) / (t_shal - t_deep + 1e-9))
        return lerp4(COLOR_DEEP_WATER, COLOR_SHALLOW, t)
    elif h <= t_sea:
        t = clamp01((h - t_shal) / (t_sea - t_shal + 1e-9))
        return lerp4(COLOR_SHALLOW, COLOR_SAND, t)
    elif h <= t_mtn:
        t = clamp01((h - t_sea) / (t_mtn - t_sea + 1e-9))
        return lerp4(COLOR_SAND, COLOR_MOUNTAIN, t)
    elif h <= t_snow:
        t = clamp01((h - t_mtn) / (t_snow - t_mtn + 1e-9))
        return lerp4(COLOR_MOUNTAIN, COLOR_SNOW, t)
    else:
        return COLOR_SNOW


# =====================================================
# MATERIALS
# =====================================================
def make_terrain_material(color_attr_name="terrain_col"):
    mat = bpy.data.materials.new("MAT_Terrain")
    mat.use_nodes = True
    nt = mat.node_tree
    nodes = nt.nodes
    links = nt.links

    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (520, 0)

    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (240, 0)

    attr = nodes.new("ShaderNodeAttribute")
    attr.location = (-380, 40)
    attr.attribute_name = color_attr_name
    if attr.outputs.get("Color") and bsdf.inputs.get("Base Color"):
        links.new(attr.outputs["Color"], bsdf.inputs["Base Color"])

    # subtle bump
    texcoord = nodes.new("ShaderNodeTexCoord")
    texcoord.location = (-900, -160)

    mapping = nodes.new("ShaderNodeMapping")
    mapping.location = (-700, -160)
    mapping.inputs["Scale"].default_value = (2.0, 2.0, 2.0)

    noise = nodes.new("ShaderNodeTexNoise")
    noise.location = (-500, -160)
    noise.inputs["Scale"].default_value = 10.0
    noise.inputs["Detail"].default_value = 8.0
    noise.inputs["Roughness"].default_value = 0.55

    bump = nodes.new("ShaderNodeBump")
    bump.location = (-140, -260)
    bump.inputs["Strength"].default_value = 0.25
    bump.inputs["Distance"].default_value = 0.2

    links.new(texcoord.outputs["Object"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    safe_set_input(bsdf, ["Roughness"], 0.9)
    safe_set_input(bsdf, ["Specular", "Specular IOR Level"], 0.12)
    return mat


def setup_world_sky(strength=0.5):
    world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True

    nt = world.node_tree
    nodes = nt.nodes
    links = nt.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputWorld")
    out.location = (400, 0)

    bg = nodes.new("ShaderNodeBackground")
    bg.location = (150, 0)
    bg.inputs["Strength"].default_value = strength

    sky = nodes.new("ShaderNodeTexSky")
    sky.location = (-150, 0)

    for candidate in ("MULTIPLE_SCATTERING", "PREETHAM", "HOSEK_WILKIE", "SINGLE_SCATTERING"):
        try:
            sky.sky_type = candidate
            break
        except:
            continue

    links.new(sky.outputs["Color"], bg.inputs["Color"])
    links.new(bg.outputs["Background"], out.inputs["Surface"])


def make_water_volume_material():
    """
    Volume-only water material:
    - Surface: optional Principled BSDF (for refraction / surface response)
    - Volume: Volume Scatter + Volume Absorption (camera-inside-water friendly)
    """
    mat = bpy.data.materials.new("MAT_WaterVolume")
    mat.use_nodes = True
    nt = mat.node_tree
    nodes = nt.nodes
    links = nt.links

    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (650, 0)

    # Optional surface (helps when camera is outside / near surface)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (220, 140)

    safe_set_input(bsdf, ["Base Color"], (0.02, 0.07, 0.10, 1.0))
    safe_set_input(bsdf, ["Roughness"], 0.02)
    safe_set_input(bsdf, ["IOR"], WATER_IOR)
    safe_set_input(bsdf, ["Transmission", "Transmission Weight"], 1.0)
    safe_set_input(bsdf, ["Specular", "Specular IOR Level"], 0.5)

    # Small normal ripple for surface cue
    texcoord = nodes.new("ShaderNodeTexCoord")
    texcoord.location = (-900, 260)
    mapping = nodes.new("ShaderNodeMapping")
    mapping.location = (-700, 260)
    mapping.inputs["Scale"].default_value = (2.0, 2.0, 2.0)
    noise = nodes.new("ShaderNodeTexNoise")
    noise.location = (-500, 260)
    noise.inputs["Scale"].default_value = 10.0
    noise.inputs["Detail"].default_value = 6.0
    noise.inputs["Roughness"].default_value = 0.5
    bump = nodes.new("ShaderNodeBump")
    bump.location = (-150, 120)
    bump.inputs["Strength"].default_value = 0.15
    bump.inputs["Distance"].default_value = 0.1

    links.new(texcoord.outputs["Object"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    # Volume scatter + absorption
    vscatter = nodes.new("ShaderNodeVolumeScatter")
    vscatter.location = (220, -120)
    vscatter.inputs["Density"].default_value = WATER_DENSITY
    vscatter.inputs["Anisotropy"].default_value = WATER_ANISOTROPY

    vabs = nodes.new("ShaderNodeVolumeAbsorption")
    vabs.location = (220, -300)
    vabs.inputs["Density"].default_value = WATER_ABS_DENSITY
    vabs.inputs["Color"].default_value = WATER_ABS_COLOR

    addv = nodes.new("ShaderNodeAddShader")
    addv.location = (460, -210)
    links.new(vscatter.outputs["Volume"], addv.inputs[0])
    links.new(vabs.outputs["Volume"], addv.inputs[1])

    # Hook outputs
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    links.new(addv.outputs["Shader"], out.inputs["Volume"])

    # Eevee refraction friendliness
    try:
        mat.use_screen_refraction = True
    except:
        pass
    try:
        mat.blend_method = 'BLEND'
    except:
        pass

    return mat


def make_cloud_volume_material():
    """
    Procedural cloud volume:
    - Noise-based density (thin & thick in one material)
    - Volume Scatter for "scattering"
    """
    mat = bpy.data.materials.new("MAT_Clouds")
    mat.use_nodes = True
    nt = mat.node_tree
    nodes = nt.nodes
    links = nt.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (760, 0)

    texcoord = nodes.new("ShaderNodeTexCoord")
    texcoord.location = (-980, 0)

    mapping = nodes.new("ShaderNodeMapping")
    mapping.location = (-780, 0)
    mapping.inputs["Scale"].default_value = (CLOUD_BASE_SCALE, CLOUD_BASE_SCALE, CLOUD_BASE_SCALE)

    # Big shapes
    noise_big = nodes.new("ShaderNodeTexNoise")
    noise_big.location = (-560, 80)
    noise_big.inputs["Scale"].default_value = 0.9
    noise_big.inputs["Detail"].default_value = 2.0
    noise_big.inputs["Roughness"].default_value = 0.55

    # Fine details
    noise_small = nodes.new("ShaderNodeTexNoise")
    noise_small.location = (-560, -120)
    noise_small.inputs["Scale"].default_value = CLOUD_DETAIL_SCALE
    noise_small.inputs["Detail"].default_value = 8.0
    noise_small.inputs["Roughness"].default_value = 0.6

    # Combine + remap to density
    mult = nodes.new("ShaderNodeMath")
    mult.location = (-300, -40)
    mult.operation = 'MULTIPLY'
    mult.inputs[1].default_value = 1.0

    # Threshold (controls thick vs thin)
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.location = (-80, -40)
    # Smooth-ish ramp
    try:
        ramp.color_ramp.elements[0].position = max(0.0, min(1.0, CLOUD_THRESHOLD - CLOUD_SOFTNESS))
        ramp.color_ramp.elements[1].position = max(0.0, min(1.0, CLOUD_THRESHOLD + CLOUD_SOFTNESS))
        ramp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
        ramp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
    except:
        pass

    dens_mul = nodes.new("ShaderNodeMath")
    dens_mul.location = (160, -40)
    dens_mul.operation = 'MULTIPLY'
    dens_mul.inputs[1].default_value = CLOUD_DENSITY

    vscatter = nodes.new("ShaderNodeVolumeScatter")
    vscatter.location = (420, -40)
    vscatter.inputs["Density"].default_value = 1.0  # driven
    vscatter.inputs["Anisotropy"].default_value = CLOUD_ANISOTROPY
    vscatter.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)

    vabs = nodes.new("ShaderNodeVolumeAbsorption")
    vabs.location = (420, -220)
    vabs.inputs["Density"].default_value = 0.02
    vabs.inputs["Color"].default_value = (0.95, 0.97, 1.0, 1.0)

    addv = nodes.new("ShaderNodeAddShader")
    addv.location = (620, -120)

    # Wiring
    links.new(texcoord.outputs["Object"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], noise_big.inputs["Vector"])
    links.new(mapping.outputs["Vector"], noise_small.inputs["Vector"])

    # multiply big * small
    links.new(noise_big.outputs["Fac"], mult.inputs[0])
    links.new(noise_small.outputs["Fac"], mult.inputs[1])

    links.new(mult.outputs["Value"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], dens_mul.inputs[0])

    # drive scatter density
    links.new(dens_mul.outputs["Value"], vscatter.inputs["Density"])

    links.new(vscatter.outputs["Volume"], addv.inputs[0])
    links.new(vabs.outputs["Volume"], addv.inputs[1])

    links.new(addv.outputs["Shader"], out.inputs["Volume"])

    return mat


# =====================================================
# RENDER SETTINGS (volumetrics)
# =====================================================
def enable_volumetrics():
    scn = bpy.context.scene

    # Eevee (if active)
    try:
        ee = scn.eevee
        if hasattr(ee, "use_volumetric_lights"):
            ee.use_volumetric_lights = True
        if hasattr(ee, "use_volumetric_shadows"):
            ee.use_volumetric_shadows = True

        # quality vs speed (keep moderate)
        if hasattr(ee, "volumetric_tile_size"):
            ee.volumetric_tile_size = '4'  # '2','4','8' depending on version
        if hasattr(ee, "volumetric_samples"):
            ee.volumetric_samples = 64
        if hasattr(ee, "volumetric_sample_distribution"):
            ee.volumetric_sample_distribution = 0.8
        if hasattr(ee, "volumetric_light_clamp"):
            ee.volumetric_light_clamp = 0.0

        if hasattr(ee, "use_ssr"):
            ee.use_ssr = True
        if hasattr(ee, "use_ssr_refraction"):
            ee.use_ssr_refraction = True
        if hasattr(ee, "ssr_thickness"):
            ee.ssr_thickness = 2.0
    except:
        pass


# =====================================================
# TERRAIN MESH (single mesh)
# =====================================================
def create_terrain_mesh():
    col = bpy.data.collections.new(TERRAIN_COLLECTION)
    bpy.context.scene.collection.children.link(col)

    mesh = bpy.data.meshes.new(TERRAIN_NAME)
    obj = bpy.data.objects.new(TERRAIN_NAME, mesh)
    col.objects.link(obj)

    bm = bmesh.new()

    ox = -(GRID_X - 1) * CELL_SIZE * 0.5 if CENTER_GRID else 0.0
    oy = -(GRID_Y - 1) * CELL_SIZE * 0.5 if CENTER_GRID else 0.0

    verts = [[None] * GRID_Y for _ in range(GRID_X)]
    hmin =  1e9
    hmax = -1e9

    for x in range(GRID_X):
        for y in range(GRID_Y):
            wx = ox + x * CELL_SIZE
            wy = oy + y * CELL_SIZE
            wz = fbm(x, y) * HEIGHT
            hmin = min(hmin, wz)
            hmax = max(hmax, wz)
            verts[x][y] = bm.verts.new((wx, wy, wz))

    bm.verts.ensure_lookup_table()

    for x in range(GRID_X - 1):
        for y in range(GRID_Y - 1):
            v1 = verts[x][y]
            v2 = verts[x + 1][y]
            v3 = verts[x + 1][y + 1]
            v4 = verts[x][y + 1]
            try:
                bm.faces.new((v1, v2, v3, v4))
            except:
                pass

    bm.faces.ensure_lookup_table()
    bm.to_mesh(mesh)
    bm.free()

    for p in mesh.polygons:
        p.use_smooth = True

    color_attr_name = "terrain_col"
    color_attr = None
    try:
        if hasattr(mesh, "color_attributes"):
            if color_attr_name in mesh.color_attributes:
                mesh.color_attributes.remove(mesh.color_attributes[color_attr_name])
            color_attr = mesh.color_attributes.new(
                name=color_attr_name,
                type='BYTE_COLOR',
                domain='CORNER'
            )
        else:
            if not mesh.vertex_colors:
                mesh.vertex_colors.new(name=color_attr_name)
            color_attr = mesh.vertex_colors[color_attr_name]
    except:
        color_attr = None

    if color_attr is not None:
        loops = mesh.loops
        polys = mesh.polygons
        data = color_attr.data

        for poly in polys:
            for li in poly.loop_indices:
                vi = loops[li].vertex_index
                z = mesh.vertices[vi].co.z
                c = color_from_height(z, hmin, hmax)
                try:
                    data[li].color = c
                except:
                    data[li].color = (c[0], c[1], c[2], c[3])

    mat = make_terrain_material(color_attr_name=color_attr_name)
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)

    try:
        mod = obj.modifiers.new(name="Subsurf", type='SUBSURF')
        mod.levels = SUBSURF_LEVEL
        mod.render_levels = SUBSURF_LEVEL
        mod.subdivision_type = 'CATMULL_CLARK'
        # Do NOT apply (keeps it faster + stable)
    except:
        pass

    return obj, (hmin, hmax), (ox, oy)


# =====================================================
# WATER BOX (volume)
# =====================================================
def create_water_box(terrain_bounds, water_z=SEA_LEVEL, margin=WATER_MARGIN, depth=WATER_DEPTH):
    (ox, oy) = terrain_bounds

    width = (GRID_X - 1) * CELL_SIZE + margin * 2.0
    depth_xy = (GRID_Y - 1) * CELL_SIZE + margin * 2.0

    cx = ox + (GRID_X - 1) * CELL_SIZE * 0.5
    cy = oy + (GRID_Y - 1) * CELL_SIZE * 0.5

    # Build a box volume: top at water_z, bottom at water_z - depth
    z_top = water_z + max(0.0, WATER_SURFACE_THICKNESS)
    z_bot = water_z - depth
    cz = (z_top + z_bot) * 0.5
    hz = (z_top - z_bot) * 0.5

    mesh = bpy.data.meshes.new("WaterBox")
    obj = bpy.data.objects.new("WaterBox", mesh)
    bpy.context.scene.collection.objects.link(obj)

    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    # scale cube to desired dimensions
    for v in bm.verts:
        v.co.x *= width * 0.5
        v.co.y *= depth_xy * 0.5
        v.co.z *= hz if hz > 1e-6 else 0.01

    # translate to position
    for v in bm.verts:
        v.co.x += cx
        v.co.y += cy
        v.co.z += cz

    bm.to_mesh(mesh)
    bm.free()

    for p in mesh.polygons:
        p.use_smooth = True

    mat = make_water_volume_material()
    obj.data.materials.append(mat)

    # for volume objects: render both sides
    try:
        obj.data.use_auto_smooth = False
    except:
        pass

    return obj


# =====================================================
# CLOUDS
# =====================================================
def create_cloud_volume():
    mesh = bpy.data.meshes.new("CloudVolume")
    obj = bpy.data.objects.new("CloudVolume", mesh)
    bpy.context.scene.collection.objects.link(obj)

    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)

    # scale to big volume
    for v in bm.verts:
        v.co.x *= CLOUD_SIZE * 0.5
        v.co.y *= CLOUD_SIZE * 0.5
        v.co.z *= CLOUD_THICKNESS * 0.5

    # lift it
    for v in bm.verts:
        v.co.z += CLOUD_ALTITUDE

    bm.to_mesh(mesh)
    bm.free()

    mat = make_cloud_volume_material()
    obj.data.materials.append(mat)

    return obj


def create_thin_cloud_sheet():
    """
    Thin displaced sheet layer:
    - plane with subdiv + displacement modifier (geometry displacement)
    - material is still volumetric-ish? For a sheet, we do alpha+principled with soft mask.
    """
    mesh = bpy.data.meshes.new("CloudSheet")
    obj = bpy.data.objects.new("CloudSheet", mesh)
    bpy.context.scene.collection.objects.link(obj)

    bm = bmesh.new()
    v1 = bm.verts.new((-CLOUD_SIZE * 0.5, -CLOUD_SIZE * 0.5, CLOUD_THIN_Z))
    v2 = bm.verts.new(( CLOUD_SIZE * 0.5, -CLOUD_SIZE * 0.5, CLOUD_THIN_Z))
    v3 = bm.verts.new(( CLOUD_SIZE * 0.5,  CLOUD_SIZE * 0.5, CLOUD_THIN_Z))
    v4 = bm.verts.new((-CLOUD_SIZE * 0.5,  CLOUD_SIZE * 0.5, CLOUD_THIN_Z))
    bm.faces.new((v1, v2, v3, v4))
    bm.to_mesh(mesh)
    bm.free()

    for p in mesh.polygons:
        p.use_smooth = True

    # Subdivide (modifier) for displacement
    try:
        sub = obj.modifiers.new(name="Subdiv", type='SUBSURF')
        sub.levels = CLOUD_THIN_SUBDIV
        sub.render_levels = CLOUD_THIN_SUBDIV
        sub.subdivision_type = 'SIMPLE'
    except:
        pass

    # Displace modifier using procedural texture
    tex = bpy.data.textures.new("TEX_CloudDisp", type='CLOUDS')
    tex.noise_scale = CLOUD_THIN_NOISE_SCALE

    try:
        disp = obj.modifiers.new(name="Displace", type='DISPLACE')
        disp.texture = tex
        disp.strength = CLOUD_THIN_DISP_STRENGTH
        disp.mid_level = 0.0
    except:
        pass

    # Sheet material (soft alpha)
    mat = bpy.data.materials.new("MAT_CloudSheet")
    mat.use_nodes = True
    nt = mat.node_tree
    nodes = nt.nodes
    links = nt.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (620, 0)

    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (280, 40)
    safe_set_input(bsdf, ["Base Color"], (1.0, 1.0, 1.0, 1.0))
    safe_set_input(bsdf, ["Roughness"], 0.9)
    safe_set_input(bsdf, ["Specular", "Specular IOR Level"], 0.05)

    texcoord = nodes.new("ShaderNodeTexCoord")
    texcoord.location = (-860, 0)

    mapping = nodes.new("ShaderNodeMapping")
    mapping.location = (-660, 0)
    mapping.inputs["Scale"].default_value = (1.0, 1.0, 1.0)

    noise = nodes.new("ShaderNodeTexNoise")
    noise.location = (-420, 0)
    noise.inputs["Scale"].default_value = 0.01
    noise.inputs["Detail"].default_value = 8.0
    noise.inputs["Roughness"].default_value = 0.6

    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.location = (-160, 0)
    try:
        ramp.color_ramp.elements[0].position = 0.48
        ramp.color_ramp.elements[1].position = 0.62
        ramp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
        ramp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
    except:
        pass

    # Use ramp as alpha mask
    safe_set_input(bsdf, ["Alpha"], 1.0)

    links.new(texcoord.outputs["Object"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    # drive alpha
    if bsdf.inputs.get("Alpha") and ramp.outputs.get("Color"):
        links.new(ramp.outputs["Color"], bsdf.inputs["Alpha"])

    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    obj.data.materials.append(mat)

    # Enable blend for alpha
    try:
        mat.blend_method = 'BLEND'
        mat.shadow_method = 'HASHED'
    except:
        pass

    return obj


# =====================================================
# CAMERA
# =====================================================
def create_camera(loc=(0, 0, 0), rot_deg=(0, 0, 0), name="Camera"):
    cam_data = bpy.data.cameras.new(name)
    cam_obj = bpy.data.objects.new(name, cam_data)
    bpy.context.scene.collection.objects.link(cam_obj)

    cam_obj.location = Vector(loc)
    cam_obj.rotation_mode = 'XYZ'
    cam_obj.rotation_euler = Euler(
        (math.radians(rot_deg[0]), math.radians(rot_deg[1]), math.radians(rot_deg[2])),
        'XYZ'
    )

    bpy.context.scene.camera = cam_obj
    return cam_obj


# =====================================================
# RUN
# =====================================================
full_wipe_scene()

enable_volumetrics()

terrain_obj, (hmin, hmax), (ox, oy) = create_terrain_mesh()
setup_world_sky(strength=0.1)

# Water as a BOX volume (camera-inside friendly)
water_obj = create_water_box((ox, oy), water_z=SEA_LEVEL, margin=WATER_MARGIN, depth=WATER_DEPTH)

# Cloud layers:
# 1) Thick volumetric block
cloud_vol = create_cloud_volume()
# 2) Thin displaced sheet (geometry displacement)
cloud_sheet = create_thin_cloud_sheet()

cam_obj = create_camera(loc=CAM_LOC, rot_deg=CAM_ROT_DEG, name="Camera")

print("Done. Terrain min/max height:", hmin, hmax)
```
## TPS multijugador
**Multi.html**
```html
<!DOCTYPE html>
<html lang="en">

<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Three.js Scene</title>
  <style>
    body {
      margin: 0;
      overflow: hidden;
    }

    canvas {
      display: block;
    }
  </style>
</head>

<body>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
  <script src="https://cdn.jsdelivr.net/gh/mrdoob/three.js@r128/examples/js/loaders/GLTFLoader.js"></script>

  <script>
    // =========================
    // Scene setup
    // =========================
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x87CEEB);

    const camera = new THREE.PerspectiveCamera(
      75, window.innerWidth / window.innerHeight, 0.1, 1000
    );
    camera.position.set(0, 5, 3);
    camera.rotation.x = -Math.PI / 4;

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    document.body.appendChild(renderer.domElement);

    // =========================
    // Helpers
    // =========================
    function lerp(a, b, t) { return a + (b - a) * t; }

    function lerpAngle(a, b, t) {
      let diff = b - a;
      while (diff < -Math.PI) diff += Math.PI * 2;
      while (diff > Math.PI) diff -= Math.PI * 2;
      return a + diff * t;
    }

    function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

    // =========================
    // GLTF Loader / Player
    // =========================
    const loader = new THREE.GLTFLoader();

    const player = new THREE.Object3D();
    player.position.set(0, 0, 0);
    scene.add(player);

    loader.load('robot.glb', (gltf) => {
      const playerModel = gltf.scene;
      playerModel.position.set(0, 0, 0);
      playerModel.traverse((child) => {
        if (child.isMesh) child.castShadow = true;
      });
      player.add(playerModel);
    });

    // =========================
    // Floor
    // =========================
    const floorGeometry = new THREE.PlaneGeometry(20, 20);
    const textureLoader = new THREE.TextureLoader();
    const gridTexture = textureLoader.load('grid.jpg');
    gridTexture.wrapS = THREE.RepeatWrapping;
    gridTexture.wrapT = THREE.RepeatWrapping;
    gridTexture.repeat.set(10, 10);

    const floorMaterial = new THREE.MeshStandardMaterial({
      map: gridTexture,
      side: THREE.DoubleSide
    });
    const floor = new THREE.Mesh(floorGeometry, floorMaterial);
    floor.rotation.x = -Math.PI / 2;
    floor.position.y = 0;
    floor.receiveShadow = true;
    scene.add(floor);

    // =========================
    // Lights
    // =========================
    const spotLight = new THREE.SpotLight(0xffffff, 1);
    spotLight.position.set(3, 8, 3);
    spotLight.target = player;
    spotLight.angle = Math.PI / 4;
    spotLight.penumbra = 0.1;
    spotLight.castShadow = true;
    spotLight.shadow.mapSize.width = 1024;
    spotLight.shadow.mapSize.height = 1024;
    scene.add(spotLight);

    const ambientLight = new THREE.AmbientLight(0xffffff, 0.2);
    scene.add(ambientLight);

    // =========================
    // Other players
    // =========================
    const otherPlayers = {};

    function updateOtherPlayers(players) {
      players.forEach(p => {
        if (!otherPlayers[p.id]) {
          const container = new THREE.Object3D();
          container.position.set(p.x, p.y, p.z);
          scene.add(container);

          otherPlayers[p.id] = {
            mesh: container,
            targetPos: { x: p.x, y: p.y, z: p.z }
          };

          loader.load('robot.glb', (gltf) => {
            const model = gltf.scene;
            model.position.set(0, 0, 0);
            model.traverse((child) => {
              if (child.isMesh) child.castShadow = true;
            });
            container.add(model);
          });
        } else {
          otherPlayers[p.id].targetPos = { x: p.x, y: p.y, z: p.z };
        }
      });

      const activeIds = players.map(p => p.id);
      Object.keys(otherPlayers).forEach(id => {
        if (!activeIds.includes(id)) {
          scene.remove(otherPlayers[id].mesh);
          delete otherPlayers[id];
        }
      });
    }

    function interpolateOtherPlayers() {
      const lerpFactor = 0.1;
      Object.values(otherPlayers).forEach(p => {
        const oldX = p.mesh.position.x;
        const oldZ = p.mesh.position.z;

        p.mesh.position.x += (p.targetPos.x - p.mesh.position.x) * lerpFactor;
        p.mesh.position.y += (p.targetPos.y - p.mesh.position.y) * lerpFactor;
        p.mesh.position.z += (p.targetPos.z - p.mesh.position.z) * lerpFactor;

        const dx = p.mesh.position.x - oldX;
        const dz = p.mesh.position.z - oldZ;
        if (Math.abs(dx) > 0.001 || Math.abs(dz) > 0.001) {
          const angle = Math.atan2(dx, dz);
          p.mesh.rotation.y = angle;
        }
      });
    }

    // =========================
    // Bullets (local + network)
    // =========================
    const BULLET_SPEED = 7.5;     // units/sec
    const BULLET_TTL_MS = 2000;   // keep bullets alive ~2s
    const BULLET_RADIUS = 0.12;

    const bulletGeometry = new THREE.SphereGeometry(BULLET_RADIUS, 12, 12);
    const myBulletMaterial = new THREE.MeshStandardMaterial({ color: 0xffdd33 });
    const otherBulletMaterial = new THREE.MeshStandardMaterial({ color: 0xff3333 });

    // Local bullets (for immediate feel)
    const myBullets = []; // {id, mesh, vx, vy, vz, bornMs}

    // Network bullets (rendered from server)
    const otherBullets = {}; // id -> {mesh, targetPos:{x,y,z}}

    function spawnLocalBullet() {
      // Spawn a bit above floor
      const start = new THREE.Vector3(player.position.x, 0.35, player.position.z);

      // IMPORTANT: your rotation convention makes "forward" aligned with +Z
      // (because angle = atan2(dx, dz)). So base forward is (0,0,1).
      const forward = new THREE.Vector3(0, 0, 1)
        .applyAxisAngle(new THREE.Vector3(0, 1, 0), player.rotation.y)
        .normalize();

      // Spawn slightly in front of player
      start.add(forward.clone().multiplyScalar(0.6));

      const vx = forward.x * BULLET_SPEED;
      const vy = 0;
      const vz = forward.z * BULLET_SPEED;

      const bullet = new THREE.Mesh(bulletGeometry, myBulletMaterial);
      bullet.position.copy(start);
      bullet.castShadow = true;
      scene.add(bullet);

      const id = `${Date.now()}_${Math.floor(Math.random() * 1e9)}`;

      myBullets.push({
        id,
        mesh: bullet,
        vx, vy, vz,
        bornMs: Date.now()
      });

      // Send to server (so others can see it)
      sendShotToServer({ id, x: start.x, y: start.y, z: start.z, vx, vy, vz, created: Math.floor(Date.now() / 1000) });
    }

    function updateLocalBullets(dt) {
      const now = Date.now();
      for (let i = myBullets.length - 1; i >= 0; i--) {
        const b = myBullets[i];

        b.mesh.position.x += b.vx * dt;
        b.mesh.position.y += b.vy * dt;
        b.mesh.position.z += b.vz * dt;

        // Remove if TTL exceeded or out of arena bounds (slightly larger than floor)
        const out =
          Math.abs(b.mesh.position.x) > 15 ||
          Math.abs(b.mesh.position.z) > 15;

        if (now - b.bornMs > BULLET_TTL_MS || out) {
          scene.remove(b.mesh);
          myBullets.splice(i, 1);
        }
      }
    }

    function updateNetworkBullets(bulletsFromServer) {
      // Create/update
      bulletsFromServer.forEach(b => {
        if (!otherBullets[b.id]) {
          const m = new THREE.Mesh(bulletGeometry, otherBulletMaterial);
          m.position.set(b.x, b.y, b.z);
          m.castShadow = true;
          scene.add(m);
          otherBullets[b.id] = {
            mesh: m,
            targetPos: { x: b.x, y: b.y, z: b.z }
          };
        } else {
          otherBullets[b.id].targetPos = { x: b.x, y: b.y, z: b.z };
        }
      });

      // Remove stale (server is source of truth)
      const activeIds = new Set(bulletsFromServer.map(b => b.id));
      Object.keys(otherBullets).forEach(id => {
        if (!activeIds.has(id)) {
          scene.remove(otherBullets[id].mesh);
          delete otherBullets[id];
        }
      });
    }

    function interpolateNetworkBullets() {
      const lerpFactor = 0.35; // a bit snappier than players
      Object.values(otherBullets).forEach(b => {
        b.mesh.position.x += (b.targetPos.x - b.mesh.position.x) * lerpFactor;
        b.mesh.position.y += (b.targetPos.y - b.mesh.position.y) * lerpFactor;
        b.mesh.position.z += (b.targetPos.z - b.mesh.position.z) * lerpFactor;
      });
    }

    // =========================
    // Input: WASD + mouse click
    // =========================
    const keys = {};
    const moveSpeed = 0.1;

    window.addEventListener('keydown', (e) => { keys[e.key.toLowerCase()] = true; });
    window.addEventListener('keyup', (e) => { keys[e.key.toLowerCase()] = false; });

    // Prevent context menu (right click)
    window.addEventListener('contextmenu', (e) => e.preventDefault());

    // Left click shoots
    window.addEventListener('mousedown', (e) => {
      if (e.button === 0) { // left
        spawnLocalBullet();
      }
    });

    function updatePlayerMovement() {
      const oldX = player.position.x;
      const oldZ = player.position.z;

      if (keys['w']) player.position.z -= moveSpeed;
      if (keys['s']) player.position.z += moveSpeed;
      if (keys['a']) player.position.x -= moveSpeed;
      if (keys['d']) player.position.x += moveSpeed;

      player.position.x = clamp(player.position.x, -9.5, 9.5);
      player.position.z = clamp(player.position.z, -9.5, 9.5);

      const dx = player.position.x - oldX;
      const dz = player.position.z - oldZ;
      if (dx !== 0 || dz !== 0) {
        const targetAngle = Math.atan2(dx, dz);
        const rotationSpeed = 0.15;
        player.rotation.y = lerpAngle(player.rotation.y, targetAngle, rotationSpeed);
      }

      // Camera follows
      camera.position.x = player.position.x;
      camera.position.z = player.position.z + 3;

      // Spotlight follows
      spotLight.position.x = player.position.x + 3;
      spotLight.position.z = player.position.z + 3;
    }

    // =========================
    // Resize
    // =========================
    window.addEventListener('resize', () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    });

    // =========================
    // Networking
    // =========================
    const ENDPOINT = 'https://ramon-servidor.com/moba/';

    async function sendShotToServer(shot) {
      try {
        // Send shot immediately (also updates position)
        await fetch(ENDPOINT, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            x: player.position.x,
            y: player.position.y,
            z: player.position.z,
            shot
          })
        });
      } catch (err) {
        console.error('Shot send error:', err);
      }
    }

    // Heartbeat: send position, receive players + bullets
    setInterval(async () => {
      try {
        const response = await fetch(ENDPOINT, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            x: player.position.x,
            y: player.position.y,
            z: player.position.z
          })
        });

        const data = await response.json();
        // Expect: { players:[...], bullets:[...] }
        updateOtherPlayers(data.players || []);
        updateNetworkBullets(data.bullets || []);
      } catch (error) {
        console.error('Sync error:', error);
      }
    }, 250); // smoother bullets than 1000ms

    // =========================
    // Main loop (dt-based)
    // =========================
    let lastT = performance.now();
    function animate() {
      requestAnimationFrame(animate);

      const now = performance.now();
      const dt = (now - lastT) / 1000; // seconds
      lastT = now;

      updatePlayerMovement();
      interpolateOtherPlayers();

      updateLocalBullets(dt);
      interpolateNetworkBullets();

      renderer.render(scene, camera);
    }
    animate();
  </script>
</body>

</html>
```