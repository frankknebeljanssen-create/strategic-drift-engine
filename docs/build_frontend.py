"""Builds a self-contained, interactive heat-map frontend.

Reads drift_data.json and writes index.html with the data embedded. Contains an
automatic reading, per-pillar trend sparklines, a guided tour of the drift
story, the heat map, a drill-down, and a strategy briefing modal (Steckbrief
and derived pillars). No server, no build chain: runs in any browser.
"""
import json
from pathlib import Path

here = Path(__file__).parent
data = json.load(open(here / "drift_data.json", encoding="utf-8"))
data_js = json.dumps(data, ensure_ascii=False)

# Strategie-Steckbrief zur Bauzeit einbetten (self-contained Seite).
steckbrief_path = here.parent / "synthetic_data" / "strategy" / "techco_steckbrief_2026.md"
strategy = {
    "steckbrief_markdown": steckbrief_path.read_text(encoding="utf-8") if steckbrief_path.exists() else "",
    "pillars": data.get("pillars", []),
}
strategy_js = json.dumps(strategy, ensure_ascii=False)

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Strategic Drift Engine</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700&family=IBM+Plex+Mono:wght@400;500;600&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{
  --ground:#0F1E27; --panel:#152833; --panel2:#0C1920; --line:#263B45;
  --ink:#EAF1F4; --muted:#8298A4; --faint:#5A7480;
  --amber:#E6AE43; --rust:#C85434; --teal:#2E90B4; --neutral:#21343E;
  --disp:"Bricolage Grotesque",system-ui,sans-serif;
  --mono:"IBM Plex Mono",ui-monospace,SFMono-Regular,monospace;
  --body:"Inter",system-ui,sans-serif;
}
*{box-sizing:border-box}
html,body{margin:0}
body{
  background:var(--ground); color:var(--ink); font-family:var(--body);
  -webkit-font-smoothing:antialiased; line-height:1.5;
  background-image:radial-gradient(1200px 600px at 80% -10%, rgba(46,144,180,0.10), transparent 60%);
}
.wrap{max-width:1600px; margin:0 auto; padding:40px 28px 64px}

.eyebrow{font-family:var(--mono); font-size:12px; letter-spacing:.28em;
  text-transform:uppercase; color:var(--teal); margin-bottom:14px}
.byline{font-size:12.5px; color:var(--faint); margin:-8px 0 16px}
.byline a{color:var(--muted); text-decoration:none; border-bottom:1px solid rgba(130,152,164,.35)}
.byline a:hover{color:var(--ink); border-bottom-color:var(--amber)}
h1{font-family:var(--disp); font-weight:700; font-size:clamp(28px,4.4vw,46px);
  line-height:1.02; letter-spacing:-.01em; margin:0 0 12px; max-width:16ch}
.sub{color:var(--muted); font-size:15px; max-width:82ch; margin:0}

.reading{margin-top:22px; padding:15px 18px; border-left:3px solid var(--amber);
  background:linear-gradient(90deg, rgba(230,174,67,.08), transparent 80%);
  border-radius:0 10px 10px 0; font-size:15px; max-width:92ch}
.reading b{font-family:var(--disp); font-weight:700}
.reading .r-num{font-family:var(--mono); color:var(--amber)}

.board{display:grid; grid-template-columns:1fr 460px; gap:24px; margin-top:26px; align-items:start}
@media(max-width:900px){.board{grid-template-columns:1fr}}
.panel{background:var(--panel); border:1px solid var(--line); border-radius:14px}
.heatmap-panel{padding:18px 20px 22px}

.hm-head{display:flex; align-items:center; justify-content:space-between; margin-bottom:16px; gap:12px}
.hm-title{font-family:var(--disp); font-weight:500; font-size:16px}
.hm-actions{display:flex; gap:8px}
.tour-btn{font-family:var(--mono); font-size:12px; color:var(--ground); background:var(--amber);
  border:none; border-radius:7px; padding:8px 13px; cursor:pointer; font-weight:600; letter-spacing:.02em;
  transition:filter .14s ease}
.tour-btn:hover{filter:brightness(1.08)}
.tour-btn:focus-visible{outline:2px solid var(--ink); outline-offset:2px}
.ghost-btn{font-family:var(--mono); font-size:12px; color:var(--ink); background:transparent;
  border:1px solid var(--line); border-radius:7px; padding:8px 13px; cursor:pointer; font-weight:500;
  letter-spacing:.02em; transition:border-color .14s ease, color .14s ease}
.ghost-btn:hover{border-color:var(--amber); color:var(--amber)}
.ghost-btn:focus-visible{outline:2px solid var(--amber); outline-offset:2px}

.modal-overlay{position:fixed; inset:0; background:rgba(0,0,0,.72); backdrop-filter:blur(3px);
  z-index:50; display:flex; align-items:flex-start; justify-content:center; padding:60px 20px 40px; overflow-y:auto}
.modal-overlay[hidden]{display:none}
.modal-panel{background:var(--panel); border:1px solid var(--line); border-radius:14px;
  max-width:780px; width:100%; padding:28px 32px 32px; position:relative; box-shadow:0 30px 60px rgba(0,0,0,.5)}
.modal-close{position:absolute; top:14px; right:14px; background:transparent; color:var(--muted);
  border:1px solid var(--line); border-radius:6px; width:30px; height:30px; font-size:18px;
  cursor:pointer; line-height:1; display:flex; align-items:center; justify-content:center}
.modal-close:hover{color:var(--ink); border-color:var(--amber)}
.modal-title{font-family:var(--disp); font-weight:700; font-size:22px; margin:0 0 20px; letter-spacing:-.005em}
.md-body h2{font-family:var(--disp); font-weight:500; font-size:17px; margin:22px 0 8px}
.md-body h2:first-child{margin-top:0}
.md-body h3{font-family:var(--disp); font-weight:500; font-size:14px; margin:18px 0 6px; color:var(--muted)}
.md-body p{margin:6px 0 10px; line-height:1.55; color:var(--ink)}
.md-body ul{margin:6px 0 12px; padding-left:20px}
.md-body li{margin:3px 0; color:var(--ink); opacity:.94}
.md-body strong{color:var(--ink); font-weight:600}
.modal-sep{border-top:1px solid var(--line); margin:26px 0 22px}
.derived-title{font-family:var(--mono); font-size:11px; letter-spacing:.06em; text-transform:uppercase;
  color:var(--muted); margin-bottom:14px}
.p-cards{display:grid; grid-template-columns:1fr 1fr; gap:12px}
@media(max-width:640px){.p-cards{grid-template-columns:1fr}}
.p-card{background:var(--panel2); border:1px solid var(--line); border-radius:10px; padding:14px}
.p-card-head{display:flex; align-items:baseline; justify-content:space-between; gap:10px; margin-bottom:10px}
.p-card-title{font-family:var(--disp); font-weight:600; font-size:15px; line-height:1.15}
.p-card-w{font-family:var(--mono); font-size:11px; color:var(--ground); background:var(--amber);
  padding:2px 7px; border-radius:5px; font-weight:600; white-space:nowrap}
.p-card-k{font-family:var(--mono); font-size:10px; letter-spacing:.06em; text-transform:uppercase;
  color:var(--faint); margin:10px 0 4px}
.p-card-p{font-size:13px; line-height:1.5; color:var(--ink); opacity:.92}
.p-card ul{margin:4px 0 0; padding-left:16px}
.p-card li{font-size:12.5px; color:var(--ink); opacity:.88; margin:2px 0; line-height:1.45}

.welcome-panel{max-width:560px}
.welcome-panel .eyebrow{margin-bottom:12px}
.welcome-panel .modal-title{margin-bottom:14px}
.welcome-text{font-size:14.5px; line-height:1.6; color:var(--ink); opacity:.92; margin:0 0 22px}
.welcome-actions{display:flex; gap:10px; flex-wrap:wrap}
.welcome-actions .tour-btn,.welcome-actions .ghost-btn{padding:10px 16px; font-size:13px}
.welcome-foot{margin-top:20px; font-family:var(--mono); font-size:11.5px}
.welcome-foot a{color:var(--faint); text-decoration:none; border-bottom:1px solid rgba(130,152,164,.3)}
.welcome-foot a:hover{color:var(--teal); border-bottom-color:var(--teal)}

.legend{display:flex; flex-wrap:wrap; align-items:center; gap:14px 24px; margin-bottom:18px}
.scale{display:flex; align-items:center; gap:10px}
.scale-bar{width:140px; height:10px; border-radius:6px;
  background:linear-gradient(90deg,var(--rust),var(--neutral),var(--teal))}
.scale-label{font-family:var(--mono); font-size:11px; color:var(--faint)}
.legend-soll{display:flex; align-items:center; gap:8px; font-size:12px; color:var(--muted)}
.soll-mark{width:2px; height:16px; background:var(--amber); border-radius:2px; box-shadow:0 0 6px rgba(230,174,67,.5)}

.grid{display:grid; gap:8px}
.ghead{display:grid; gap:8px}
.corner{font-family:var(--mono); font-size:10.5px; color:var(--faint);
  align-self:end; letter-spacing:.04em; text-transform:uppercase; padding-bottom:6px}
.whead{font-family:var(--mono); font-size:12px; color:var(--muted); text-align:center;
  padding-bottom:6px; border-bottom:1px solid var(--line)}
.whead .wspan{color:var(--ink)}
.row{display:grid; gap:8px; align-items:stretch}
.rlabel{display:flex; flex-direction:column; justify-content:center; padding-right:8px}
.rlabel .rtitle{font-family:var(--disp); font-weight:500; font-size:15px; line-height:1.15}
.rlabel .rsoll{font-family:var(--mono); font-size:10.5px; color:var(--faint); margin-top:3px}
.rlabel .spark{margin-top:7px}

.cell{position:relative; border:1px solid rgba(255,255,255,.06); border-radius:10px;
  padding:12px 12px 11px; min-height:116px; cursor:pointer; text-align:left;
  color:var(--ink); font-family:inherit; display:flex; flex-direction:column;
  justify-content:space-between; transition:transform .14s ease, box-shadow .14s ease, border-color .14s ease, opacity .18s ease}
.cell:hover{transform:translateY(-2px); box-shadow:0 8px 22px rgba(0,0,0,.32)}
.cell:focus-visible{outline:none; border-color:var(--amber); box-shadow:0 0 0 2px rgba(230,174,67,.6)}
.cell.sel{border-color:var(--amber); box-shadow:0 0 0 2px rgba(230,174,67,.85), 0 10px 26px rgba(0,0,0,.4)}
.grid.touring .cell:not(.sel){opacity:.4}
.cell-ist{font-family:var(--mono); font-weight:600; font-size:26px; letter-spacing:-.02em; line-height:1}
.cell-drift{font-family:var(--mono); font-size:12px; opacity:.92}
.cell-bar{position:relative; height:6px; border-radius:4px; background:rgba(255,255,255,.14); margin:10px 0 2px; overflow:visible}
.cell-fill{position:absolute; left:0; top:0; bottom:0; border-radius:4px; background:rgba(255,255,255,.82)}
.cell-tick{position:absolute; top:-3px; bottom:-3px; width:2px; background:var(--amber); border-radius:2px; box-shadow:0 0 5px rgba(230,174,67,.7)}

.tourbar{margin-top:16px; border:1px solid var(--amber); border-radius:12px;
  background:linear-gradient(180deg, rgba(230,174,67,.09), rgba(230,174,67,.03));
  padding:14px 16px; display:flex; align-items:center; gap:16px}
.tourbar[hidden]{display:none}
.tb-step{font-family:var(--mono); font-size:11px; color:var(--amber); letter-spacing:.06em; white-space:nowrap}
.tb-body{flex:1}
.tb-title{font-family:var(--disp); font-weight:700; font-size:14px; margin-bottom:2px}
.tb-text{font-size:13px; color:var(--ink); opacity:.9}
.tb-ctrl{display:flex; gap:7px}
.tb-ctrl button{font-family:var(--mono); font-size:12px; background:transparent; color:var(--ink);
  border:1px solid var(--line); border-radius:7px; padding:7px 11px; cursor:pointer; transition:border-color .14s}
.tb-ctrl button:hover{border-color:var(--amber)}
.tb-ctrl button:disabled{opacity:.4; cursor:default}
.tb-ctrl .prim{background:var(--amber); color:var(--ground); border-color:var(--amber); font-weight:600}

.drill{padding:20px; position:sticky; top:22px}
.drill-head .d-pillar{font-family:var(--disp); font-weight:700; font-size:19px; line-height:1.1}
.drill-head .d-win{font-family:var(--mono); font-size:12px; color:var(--muted); margin-top:4px}
.d-stats{display:flex; gap:18px; margin:16px 0 18px; padding:14px 0; border-top:1px solid var(--line); border-bottom:1px solid var(--line)}
.d-stat .k{font-family:var(--mono); font-size:10px; letter-spacing:.08em; text-transform:uppercase; color:var(--faint)}
.d-stat .v{font-family:var(--mono); font-size:19px; font-weight:600; margin-top:3px}
.d-evhead{font-family:var(--mono); font-size:11px; letter-spacing:.06em; text-transform:uppercase; color:var(--muted); margin-bottom:12px}
.ev-list{display:flex; flex-direction:column; gap:12px; max-height:min(58vh,560px); overflow-y:auto; padding-right:4px}
.ev-list::-webkit-scrollbar{width:8px}
.ev-list::-webkit-scrollbar-thumb{background:var(--line); border-radius:4px}
.ev{background:var(--panel2); border:1px solid var(--line); border-radius:10px; padding:11px 12px}
.ev-top{display:flex; align-items:center; justify-content:space-between; gap:8px; margin-bottom:7px}
.badge{font-family:var(--mono); font-size:10px; letter-spacing:.03em; padding:2px 7px; border-radius:5px;
  text-transform:uppercase; border:1px solid transparent; white-space:nowrap}
.b-slack{color:#7ED0C7; background:rgba(126,208,199,.10); border-color:rgba(126,208,199,.28)}
.b-mail{color:#E6AE43; background:rgba(230,174,67,.10); border-color:rgba(230,174,67,.28)}
.b-meeting{color:#B79CE0; background:rgba(183,156,224,.10); border-color:rgba(183,156,224,.28)}
.b-calendar{color:#8298A4; background:rgba(130,152,164,.10); border-color:rgba(130,152,164,.28)}
.ev-meta{font-family:var(--mono); font-size:11px; color:var(--muted); text-align:right}
.ev-snip{font-size:13px; color:var(--ink); opacity:.92}
.ev-snip.full{white-space:pre-wrap; max-height:340px; overflow-y:auto; padding-right:4px}
.ev-toggle{background:transparent; border:none; color:var(--teal); font-family:var(--mono);
  font-size:11px; cursor:pointer; padding:5px 0 0; margin-top:2px; letter-spacing:.02em;
  text-decoration:underline; text-underline-offset:2px; opacity:.85}
.ev-toggle:hover{opacity:1; color:var(--amber)}
.ev-toggle:focus-visible{outline:1px solid var(--amber); outline-offset:2px; border-radius:2px}

.ev-eng{margin-top:11px; padding:10px 12px 11px; background:rgba(230,174,67,.06);
  border-left:2px solid rgba(230,174,67,.55); border-radius:0 8px 8px 0}
.ev-eng-title{font-family:var(--mono); font-size:10px; letter-spacing:.06em; text-transform:uppercase;
  color:var(--amber); margin-bottom:8px; opacity:.95}
.ev-eng-row{margin-bottom:8px}
.ev-eng-row:last-child{margin-bottom:0}
.ev-eng-k{display:block; font-family:var(--mono); font-size:9.5px; letter-spacing:.06em;
  text-transform:uppercase; color:var(--faint); margin-bottom:3px}
.ev-eng-v{display:block; font-size:12.5px; color:var(--ink); opacity:.92; line-height:1.45}
.ev-signals{margin:0; padding:0; list-style:none}
.ev-signals li{font-family:var(--mono); font-size:11px; color:var(--ink); opacity:.82;
  margin:3px 0; padding:2px 8px 2px 22px; border-left:1px solid rgba(255,255,255,.1);
  border-radius:0 4px 4px 0; line-height:1.55; word-break:break-word; position:relative}
.ev-signals li::before{position:absolute; left:6px; top:2px; font-family:var(--mono);
  font-size:11px; line-height:1.55; font-weight:600}
.sig-pos{background:rgba(126,208,199,.07); border-left-color:rgba(126,208,199,.45)}
.sig-pos::before{content:"+"; color:#7ED0C7}
.sig-neg{background:rgba(200,84,52,.09); border-left-color:rgba(200,84,52,.5)}
.sig-neg::before{content:"\2212"; color:var(--rust)}
.sig-scores{opacity:.6}
.sig-scores::before{content:"·"; color:var(--faint); font-size:14px; top:-1px}
.sig-chosen{color:var(--amber); font-weight:600; opacity:1;
  background:rgba(230,174,67,.08); border-left-color:rgba(230,174,67,.55)}
.sig-chosen::before{content:"\2192"; color:var(--amber)}

.ev-conf{display:flex; align-items:center; gap:8px; flex-wrap:wrap}
.conf-track{width:80px; height:5px; border-radius:3px; background:rgba(255,255,255,.12); overflow:hidden}
.conf-fill{height:100%; background:var(--teal)}
.conf-num{font-family:var(--mono); font-size:11px; color:var(--ink); opacity:.9}
.conf-label{font-family:var(--mono); font-size:11px; color:var(--muted); letter-spacing:.02em}
.conf-scale{font-family:var(--mono); font-size:9.5px; letter-spacing:.05em; color:var(--faint);
  opacity:.55; margin-top:4px}
/* Legacy-Klassen, aktuell ungenutzt: */
.ev-foot{display:flex; align-items:center; gap:8px; margin-top:9px}
.ev-rat{font-family:var(--mono); font-size:11px; color:var(--faint); margin-left:auto}

footer{margin-top:30px; color:var(--faint); font-size:12px; font-family:var(--mono); letter-spacing:.02em}
footer .dot{color:var(--line); margin:0 8px}
footer .note{color:var(--faint); opacity:.85}

@media(prefers-reduced-motion:reduce){*{transition:none!important}}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="eyebrow">Strategic Drift Engine</div>
    <div class="byline">A demo project by <a href="https://github.com/frankknebeljanssen-create/strategic-drift-engine" target="_blank" rel="noopener">Frank Knebel-Janssen</a></div>
    <h1>Where attention actually went</h1>
    <p class="sub">Each cell compares the measured attention on a strategic pillar with its target over time. The amber mark shows the target. Select a cell to see the messages the number came from.</p>
    <div class="reading" id="reading"></div>
  </header>

  <div class="board">
    <section class="panel heatmap-panel">
      <div class="hm-head">
        <div class="hm-title">Attention over time</div>
        <div class="hm-actions">
          <button class="ghost-btn" id="strategyBtn">Strategy</button>
          <button class="tour-btn" id="tourBtn">Guided Tour</button>
        </div>
      </div>
      <div class="legend">
        <div class="scale">
          <span class="scale-label">below target</span>
          <span class="scale-bar"></span>
          <span class="scale-label">above target</span>
        </div>
        <div class="legend-soll"><span class="soll-mark"></span> Target per pillar</div>
      </div>
      <div id="grid" class="grid"></div>
      <div class="tourbar" id="tourbar" hidden>
        <span class="tb-step" id="tbStep"></span>
        <div class="tb-body"><div class="tb-title" id="tbTitle"></div><div class="tb-text" id="tbText"></div></div>
        <div class="tb-ctrl">
          <button id="tbPrev">Back</button>
          <button id="tbNext" class="prim">Next</button>
          <button id="tbEnd">Done</button>
        </div>
      </div>
    </section>

    <aside class="panel drill" id="drill"></aside>
  </div>

  <footer id="foot"></footer>
</div>

<div class="modal-overlay" id="strategyModal" hidden role="dialog" aria-modal="true" aria-labelledby="strategyTitle">
  <div class="modal-panel">
    <button class="modal-close" id="strategyClose" aria-label="Close">×</button>
    <h2 class="modal-title" id="strategyTitle">Strategy briefing</h2>
    <div id="strategyBody"></div>
  </div>
</div>

<div class="modal-overlay" id="welcomeModal" role="dialog" aria-modal="true" aria-labelledby="welcomeTitle">
  <div class="modal-panel welcome-panel">
    <div class="eyebrow">Demo Project</div>
    <h2 class="modal-title" id="welcomeTitle">Strategic Drift Engine</h2>
    <p class="welcome-text">A multi-agent system that measures the gap between a company's stated strategy and what its internal communication actually shows. Everything here runs on a synthetic dataset for a fictional company, TechCo, so feel free to click around.</p>
    <div class="welcome-actions">
      <button class="tour-btn" id="welcomeTour">Start guided tour</button>
      <button class="ghost-btn" id="welcomeExplore">Explore on my own</button>
    </div>
    <div class="welcome-foot"><a href="https://github.com/frankknebeljanssen-create/strategic-drift-engine" target="_blank" rel="noopener">View the source on GitHub</a></div>
  </div>
</div>

<script>
const DATA = __DATA__;
const STRATEGY = __STRATEGY__;

const MON = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
function fdate(iso){const [y,m,d]=iso.split("-").map(Number); return MON[m-1]+" "+d;}
function frange(w){return fdate(w.start)+" – "+fdate(w.end);}
function fdatefull(iso){const [y,m,d]=iso.split("-").map(Number); return MON[m-1]+" "+d+", "+y;}

const pillars = DATA.pillars;
const windows = DATA.windows;
const cellMap = {};
DATA.cells.forEach(c=>{cellMap[c.window_index+":"+c.pillar_key]=c;});
function pillarTitle(k){return (pillars.find(p=>p.key===k)||{}).title||k;}

function driftColor(drift){
  const t = Math.max(-1, Math.min(1, drift/0.25));
  const neutral=[33,52,62], rust=[200,84,52], teal=[46,144,180];
  const target = t<0?rust:teal, k=Math.abs(t);
  const c = neutral.map((n,i)=>Math.round(n+(target[i]-n)*k));
  return "rgb("+c[0]+","+c[1]+","+c[2]+")";
}
function pct(x){return Math.round(x*100)+"%";}
function signed(x){const v=Math.round(x*100); return (v>0?"+":"")+v;}
function escapeHtml(s){return (s||"").replace(/[&<>"]/g,ch=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[ch]));}

let selected = null;

function sparkline(pkey){
  const vals = windows.map(w=>cellMap[w.index+":"+pkey].ist_anteil);
  const soll = (pillars.find(p=>p.key===pkey)||{}).soll_anteil||0;
  const W=132,H=28,pad=4;
  const maxv = Math.max(Math.max(...vals), soll)*1.12 || 1;
  const x=i=> pad + i*(W-2*pad)/(Math.max(1,vals.length-1));
  const y=v=> H-pad - (v/maxv)*(H-2*pad);
  const pts = vals.map((v,i)=>x(i).toFixed(1)+","+y(v).toFixed(1)).join(" ");
  const sy = y(soll).toFixed(1);
  const lastDrift = cellMap[(windows.length-1)+":"+pkey].drift;
  const stroke = driftColor(lastDrift);
  const dots = vals.map((v,i)=>'<circle cx="'+x(i).toFixed(1)+'" cy="'+y(v).toFixed(1)+'" r="1.9" fill="'+stroke+'"/>').join("");
  return '<svg class="spark" width="'+W+'" height="'+H+'" viewBox="0 0 '+W+' '+H+'" aria-hidden="true">'+
    '<line x1="0" y1="'+sy+'" x2="'+W+'" y2="'+sy+'" stroke="#E6AE43" stroke-width="1" stroke-dasharray="3 3" opacity="0.7"/>'+
    '<polyline points="'+pts+'" fill="none" stroke="'+stroke+'" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>'+
    dots+'</svg>';
}

function renderGrid(){
  const grid = document.getElementById("grid");
  const cols = "210px repeat("+windows.length+", 1fr)";
  grid.innerHTML = "";
  const head = document.createElement("div");
  head.className="ghead"; head.style.gridTemplateColumns=cols;
  head.innerHTML = '<div class="corner">Pillar &nbsp;\\&nbsp; Period</div>' +
    windows.map(w=>'<div class="whead"><span class="wspan">'+frange(w)+'</span></div>').join("");
  grid.appendChild(head);

  pillars.forEach(p=>{
    const row = document.createElement("div");
    row.className="row"; row.style.gridTemplateColumns=cols;
    const label = document.createElement("div");
    label.className="rlabel";
    label.innerHTML = '<div class="rtitle">'+p.title+'</div><div class="rsoll">Target '+pct(p.soll_anteil)+'</div>'+sparkline(p.key);
    row.appendChild(label);
    windows.forEach(w=>{
      const c = cellMap[w.index+":"+p.key];
      const btn = document.createElement("button");
      btn.className="cell"; btn.style.background=driftColor(c.drift);
      btn.setAttribute("aria-label", p.title+", "+frange(w)+": actual "+pct(c.ist_anteil)+", deviation "+signed(c.drift)+" percentage points");
      const fill = Math.max(0,Math.min(100, c.ist_anteil*100));
      const tick = Math.max(0,Math.min(100, c.soll_anteil*100));
      btn.innerHTML =
        '<div class="cell-ist">'+pct(c.ist_anteil)+'</div>'+
        '<div class="cell-bar"><div class="cell-fill" style="width:'+fill+'%"></div>'+
          '<div class="cell-tick" style="left:'+tick+'%"></div></div>'+
        '<div class="cell-drift">'+signed(c.drift)+' pp</div>';
      btn.dataset.key = w.index+":"+p.key;
      btn.addEventListener("click",()=>{ if(tour.active) endTour(); select(w.index,p.key); });
      row.appendChild(btn);
    });
    grid.appendChild(row);
  });
}

const TYPE_BADGE = {slack:"b-slack", mail:"b-mail", meeting:"b-meeting", meeting_note:"b-meeting", calendar:"b-calendar"};

function select(wi, pkey){
  selected = wi+":"+pkey;
  document.querySelectorAll(".cell").forEach(c=>c.classList.toggle("sel", c.dataset.key===selected));
  renderDrill(wi, pkey);
  if(window.matchMedia("(max-width:900px)").matches && !tour.active){
    document.getElementById("drill").scrollIntoView({behavior:"smooth", block:"start"});
  }
}

const PREVIEW_LEN = 180;

function signalClass(s){
  if(s.startsWith("scores:")) return "sig-scores";
  if(s.startsWith("chosen:")) return "sig-chosen";
  if(s.startsWith("reduces ")) return "sig-neg";
  return "sig-pos";  // Pillar-Signale + Kalender-Kategorie
}

function confLabel(c){
  if(c==null) return "";
  if(c >= 0.9) return "very high";
  if(c >= 0.75) return "high";
  if(c >= 0.5) return "moderate";
  return "low";
}

function evidenceCard(e){
  const badge = TYPE_BADGE[e.type]||"b-calendar";
  const chan = e.type + (e.channel? " · "+e.channel : "");
  const conf = Math.round((e.confidence||0)*100);
  const confNum = e.confidence!=null ? e.confidence.toFixed(2) : "–";
  const cLabel = confLabel(e.confidence);
  const rawFull = (e.text_full!=null && e.text_full!=="") ? e.text_full : (e.snippet||"");
  const collapsed = rawFull.replace(/\s+/g," ").trim();
  const preview = collapsed.length > PREVIEW_LEN
    ? collapsed.slice(0, PREVIEW_LEN).trimEnd() + "…"
    : collapsed;
  const needsToggle = rawFull.length > PREVIEW_LEN;

  const signals = (e.signals||[])
    .map(s=>'<li class="'+signalClass(s)+'">'+escapeHtml(s)+"</li>")
    .join("");
  const contribution = e.contribution || e.rationale || "";

  return '<div class="ev">'+
    '<div class="ev-top"><span class="badge '+badge+'">'+chan+'</span>'+
    '<span class="ev-meta">'+(e.author||"—")+' · '+fdate(e.ts.slice(0,10))+'</span></div>'+
    '<div class="ev-snip" data-preview="'+escapeHtml(preview)+'" data-full="'+escapeHtml(rawFull)+'">'+
      escapeHtml(preview)+'</div>'+
    (needsToggle ? '<button class="ev-toggle" type="button">Show full message</button>' : '')+
    '<div class="ev-eng">'+
      '<div class="ev-eng-title">How the engine read this</div>'+
      (contribution ? '<div class="ev-eng-row"><span class="ev-eng-k">Contribution</span>'+
        '<span class="ev-eng-v">'+escapeHtml(contribution)+'</span></div>' : '')+
      (signals ? '<div class="ev-eng-row"><span class="ev-eng-k">Signals detected</span>'+
        '<ul class="ev-signals">'+signals+'</ul></div>' : '')+
      '<div class="ev-eng-row"><span class="ev-eng-k">Confidence</span>'+
        '<div class="ev-conf"><span class="conf-track">'+
        '<span class="conf-fill" style="width:'+conf+'%"></span></span>'+
        '<span class="conf-num">'+confNum+'</span>'+
        (cLabel ? '<span class="conf-label">'+cLabel+'</span>' : '')+
        '</div>'+
        '<div class="conf-scale">0 low · 1 max</div>'+
      '</div>'+
    '</div>'+
  '</div>';
}

// Event-Delegation fuer Show-full/Show-less-Toggle.
document.addEventListener("click", (ev)=>{
  const btn = ev.target;
  if(!(btn instanceof HTMLElement) || !btn.classList.contains("ev-toggle")) return;
  const snip = btn.previousElementSibling;
  if(!snip || !snip.classList.contains("ev-snip")) return;
  const expanded = snip.classList.toggle("full");
  if(expanded){
    snip.textContent = snip.dataset.full || "";
    btn.textContent = "Show less";
  } else {
    snip.textContent = snip.dataset.preview || "";
    btn.textContent = "Show full message";
  }
});

function renderDrill(wi, pkey){
  const drill = document.getElementById("drill");
  const p = pillars.find(x=>x.key===pkey);
  const w = windows[wi];
  const c = cellMap[wi+":"+pkey];
  const ev = (DATA.evidence[wi+":"+pkey]||[]);
  const driftCol = c.drift<0 ? "var(--rust)" : "var(--teal)";
  const items = ev.map(e=>evidenceCard(e)).join("");
  drill.innerHTML =
    '<div class="drill-head"><div class="d-pillar">'+p.title+'</div>'+
      '<div class="d-win">'+fdatefull(w.start)+' – '+fdatefull(w.end)+'</div></div>'+
    '<div class="d-stats">'+
      '<div class="d-stat"><div class="k">Actual</div><div class="v">'+pct(c.ist_anteil)+'</div></div>'+
      '<div class="d-stat"><div class="k">Target</div><div class="v" style="color:var(--amber)">'+pct(c.soll_anteil)+'</div></div>'+
      '<div class="d-stat"><div class="k">Drift</div><div class="v" style="color:'+driftCol+'">'+signed(c.drift)+' pp</div></div>'+
      '<div class="d-stat"><div class="k">Sources</div><div class="v">'+c.n_sources+'</div></div>'+
    '</div><div class="d-evhead">Messages behind this number</div>'+
    '<div class="ev-list">'+(items||'<div style="color:var(--faint);padding:20px 0">No sources in this cell.</div>')+'</div>';
}

function renderReading(){
  const peak = DATA.cells.reduce((a,b)=>Math.abs(a.drift)>Math.abs(b.drift)?a:b);
  const w = windows[peak.window_index];
  const wcells = pillars.map(p=>cellMap[peak.window_index+":"+p.key]);
  const low = wcells.reduce((a,b)=>a.drift<b.drift?a:b);
  const verb = peak.drift>0 ? "draws the most attention" : "is most neglected";
  let txt = '<b>'+pillarTitle(peak.pillar_key)+'</b> '+verb+' in the period <span class="r-num">'+frange(w)+
    '</span>, at <span class="r-num">'+pct(peak.ist_anteil)+'</span> against a target of <span class="r-num">'+pct(peak.soll_anteil)+'</span>.';
  if(low.pillar_key!==peak.pillar_key && low.drift<0){
    txt += ' In the same window, <b>'+pillarTitle(low.pillar_key)+'</b> drops to <span class="r-num">'+pct(low.ist_anteil)+'</span>.';
  }
  document.getElementById("reading").innerHTML = txt;
}

function buildTour(){
  const steps=[]; const lastW=windows.length-1;
  const w0 = pillars.map(p=>cellMap["0:"+p.key]);
  const near0 = w0.reduce((a,b)=>Math.abs(a.drift)<Math.abs(b.drift)?a:b);
  steps.push({wi:0, pkey:near0.pillar_key, title:"What you're looking at",
    text:"TechCo's leadership defined three strategic pillars in a one-page brief. The heat map shows how much real attention each pillar got, week by week, against that target. Click Strategy at the top anytime to see the original brief."});
  steps.push({wi:0, pkey:near0.pillar_key, title:"Baseline",
    text:"In the first window, the pillars stay close to their targets. "+pillarTitle(near0.pillar_key)+" hits its target almost exactly."});
  const peak = DATA.cells.reduce((a,b)=>Math.abs(a.drift)>Math.abs(b.drift)?a:b);
  steps.push({wi:peak.window_index, pkey:peak.pillar_key, title:"Largest deviation",
    text:pillarTitle(peak.pillar_key)+" reaches "+pct(peak.ist_anteil)+" against a target of "+pct(peak.soll_anteil)+" ("+signed(peak.drift)+" pp). On the right you can see the messages the value came from."});
  const wc = pillars.map(p=>cellMap[peak.window_index+":"+p.key]);
  const opp = wc.reduce((a,b)=>a.drift<b.drift?a:b);
  if(opp.pillar_key!==peak.pillar_key){
    steps.push({wi:peak.window_index, pkey:opp.pillar_key, title:"The flip side",
      text:"In the same window, "+pillarTitle(opp.pillar_key)+" falls to "+pct(opp.ist_anteil)+" ("+signed(opp.drift)+" pp). What one pillar gains, another loses."});
  }
  const wl = pillars.map(p=>cellMap[lastW+":"+p.key]);
  const nearL = wl.reduce((a,b)=>Math.abs(a.drift)<Math.abs(b.drift)?a:b);
  const spread = Math.round(Math.max(...wl.map(c=>Math.abs(c.drift)))*100);
  steps.push({wi:lastW, pkey:nearL.pillar_key, title:"By the end",
    text:"In the final window, the pillars converge again. The largest remaining deviation is "+spread+" percentage points."});
  steps.push({wi:peak.window_index, pkey:peak.pillar_key, title:"How to check any number",
    text:"Click any cell, then click a message and expand it. The panel below shows exactly which words the engine picked up on, and whether they support or work against a pillar. That's the full trail from claim to evidence."});
  return steps;
}

const tour = {active:false, i:0, steps:[]};
function startTour(){
  tour.active=true; tour.i=0; tour.steps=buildTour();
  document.getElementById("grid").classList.add("touring");
  document.getElementById("tourbar").hidden=false;
  document.getElementById("tourBtn").textContent="Tour running";
  showTourStep();
}
function showTourStep(){
  const s=tour.steps[tour.i];
  select(s.wi, s.pkey);
  document.getElementById("tbStep").textContent="Step "+(tour.i+1)+" / "+tour.steps.length;
  document.getElementById("tbTitle").textContent=s.title;
  document.getElementById("tbText").textContent=s.text;
  document.getElementById("tbPrev").disabled = tour.i===0;
  document.getElementById("tbNext").textContent = tour.i===tour.steps.length-1 ? "Restart" : "Next";
}
function endTour(){
  tour.active=false;
  document.getElementById("grid").classList.remove("touring");
  document.getElementById("tourbar").hidden=true;
  document.getElementById("tourBtn").textContent="Guided Tour";
}
document.getElementById("tourBtn").addEventListener("click",()=>{ tour.active?endTour():startTour(); });
document.getElementById("tbPrev").addEventListener("click",()=>{ if(tour.i>0){tour.i--; showTourStep();} });
document.getElementById("tbNext").addEventListener("click",()=>{ tour.i=(tour.i+1)%tour.steps.length; showTourStep(); });
document.getElementById("tbEnd").addEventListener("click", endTour);

function inlineMd(s){return escapeHtml(s).replace(/\*\*(.+?)\*\*/g,"<strong>$1</strong>");}
function renderMarkdown(md){
  const lines = (md||"").split("\n");
  let html = "", inList = false, para = [];
  const flushPara = ()=>{ if(para.length){ html += "<p>"+inlineMd(para.join(" "))+"</p>"; para = []; } };
  const closeList = ()=>{ if(inList){ html += "</ul>"; inList = false; } };
  for(const raw of lines){
    const t = raw.replace(/\r$/,"").trim();
    if(!t){ flushPara(); closeList(); continue; }
    if(t.startsWith("## ")){ flushPara(); closeList(); html += "<h2>"+escapeHtml(t.slice(3))+"</h2>"; continue; }
    if(t.startsWith("### ")){ flushPara(); closeList(); html += "<h3>"+escapeHtml(t.slice(4))+"</h3>"; continue; }
    if(t.startsWith("- ")){ flushPara(); if(!inList){ html += "<ul>"; inList = true; } html += "<li>"+inlineMd(t.slice(2))+"</li>"; continue; }
    para.push(t);
  }
  flushPara(); closeList();
  return html;
}

function pillarCard(p){
  const w = p.soll_gewicht!=null ? Math.round(p.soll_gewicht*100)+"%" : "—";
  const kris = (p.kriterien||[]).map(k=>"<li>"+escapeHtml(k)+"</li>").join("");
  return '<div class="p-card">'+
    '<div class="p-card-head"><div class="p-card-title">'+escapeHtml(p.title||p.key)+'</div>'+
      '<span class="p-card-w" title="Target weight">'+w+'</span></div>'+
    (p.grundsatz ? '<div class="p-card-k">Principle</div><div class="p-card-p">'+escapeHtml(p.grundsatz)+'</div>' : '')+
    (kris ? '<div class="p-card-k">Criteria</div><ul>'+kris+'</ul>' : '')+
  '</div>';
}

function openStrategy(){
  const md = renderMarkdown(STRATEGY.steckbrief_markdown||"");
  const cards = (STRATEGY.pillars||[]).map(pillarCard).join("");
  document.getElementById("strategyBody").innerHTML =
    '<div class="md-body">'+md+'</div>'+
    '<div class="modal-sep"></div>'+
    '<div class="derived-title">Derived pillars</div>'+
    '<div class="p-cards">'+cards+'</div>';
  document.getElementById("strategyModal").hidden = false;
  document.body.style.overflow = "hidden";
  document.getElementById("strategyClose").focus();
}
function closeStrategy(){
  document.getElementById("strategyModal").hidden = true;
  document.body.style.overflow = "";
}
document.getElementById("strategyBtn").addEventListener("click", openStrategy);
document.getElementById("strategyClose").addEventListener("click", closeStrategy);
document.getElementById("strategyModal").addEventListener("click", e=>{
  if(e.target.id==="strategyModal") closeStrategy();
});
document.addEventListener("keydown", e=>{
  if(e.key==="Escape"){
    if(!document.getElementById("welcomeModal").hidden) closeWelcome();
    else if(tour.active) endTour();
    else if(!document.getElementById("strategyModal").hidden) closeStrategy();
  }
});

// Willkommens-Overlay: erscheint bei jedem Laden (kein localStorage).
function closeWelcome(){
  document.getElementById("welcomeModal").hidden = true;
  document.body.style.overflow = "";
}
document.getElementById("welcomeExplore").addEventListener("click", closeWelcome);
document.getElementById("welcomeTour").addEventListener("click", ()=>{ closeWelcome(); startTour(); });
document.getElementById("welcomeModal").addEventListener("click", e=>{
  if(e.target.id==="welcomeModal") closeWelcome();
});

function renderFoot(){
  const tot = Object.values(DATA.evidence).reduce((a,v)=>a+v.length,0);
  document.getElementById("foot").innerHTML =
    '<span class="note">Synthetic demo dataset, fictional company TechCo.</span>' + '<span class="dot">•</span>' +
    windows.length+" windows" + '<span class="dot">•</span>' + pillars.length+" pillars" +
    '<span class="dot">•</span>' + tot+" linked sources" + '<span class="dot">•</span>' + "run "+DATA.run_id;
}

renderGrid(); renderReading(); renderFoot();
(function(){
  const best = DATA.cells.reduce((a,b)=>Math.abs(a.drift)>Math.abs(b.drift)?a:b);
  select(best.window_index, best.pillar_key);
  // Welcome-Overlay ist beim Laden offen -> Body-Scroll sperren.
  if(!document.getElementById("welcomeModal").hidden) document.body.style.overflow = "hidden";
})();
</script>
</body>
</html>"""

out = HTML.replace("__DATA__", data_js).replace("__STRATEGY__", strategy_js)
(here / "index.html").write_text(out, encoding="utf-8")
print(f"index.html written ({len(out)} characters)")
