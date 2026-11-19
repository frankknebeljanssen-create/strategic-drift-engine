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
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Strategic Drift Engine</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700&family=IBM+Plex+Mono:wght@400;500;600&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{
  --s1:8px; --s2:16px; --s3:24px; --s4:32px; --gutter:28px;
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
.wrap{max-width:1600px; margin:0 auto; padding:var(--s4) var(--gutter) 64px}

.eyebrow{font-family:var(--mono); font-size:12px; letter-spacing:.28em;
  text-transform:uppercase; color:var(--teal); margin-bottom:var(--s1)}
.byline{font-size:12.5px; color:var(--faint); margin:-8px 0 16px}
.byline a{color:var(--muted); text-decoration:none; border-bottom:1px solid rgba(130,152,164,.35)}
.byline a:hover{color:var(--ink); border-bottom-color:var(--amber)}
h1{font-family:var(--disp); font-weight:700; font-size:clamp(26px,3.2vw,38px);
  line-height:1.05; letter-spacing:-.01em; margin:0 0 var(--s1)}
.sub{color:var(--muted); font-size:15px; max-width:110ch; margin:0}

.head-row{display:flex; justify-content:space-between; align-items:flex-start; gap:var(--s3); flex-wrap:wrap}
.head-text{flex:1 1 560px; min-width:0}
.tile-group{flex:0 0 auto; display:flex; gap:var(--s1); margin-top:var(--s2); flex-wrap:wrap}
.tile{font-family:var(--body); display:flex; align-items:center; gap:12px; width:206px; height:64px; padding:0 14px;
  background:var(--panel); border:1px solid var(--line); border-radius:12px; color:var(--ink); cursor:pointer; text-align:left;
  transition:border-color .14s ease, background .14s ease}
.tile:hover{border-color:var(--amber); background:var(--panel2)}
.tile:focus-visible{outline:2px solid var(--ink); outline-offset:2px}
.tile-ico{flex:none; width:30px; height:30px; border-radius:50%; display:flex; align-items:center; justify-content:center;
  font-family:var(--mono); font-size:14px; font-weight:600; color:var(--teal); border:1.5px solid var(--teal)}
.tile-txt{display:flex; flex-direction:column; gap:3px; min-width:0}
.tile-title{font-family:var(--disp); font-weight:600; font-size:14.5px; line-height:1.15}
.tile-sub{font-family:var(--mono); font-size:11px; color:var(--muted)}
.tile.primary{border-color:var(--amber); background:rgba(230,174,67,.1)}
.tile.primary:hover{background:rgba(230,174,67,.2)}
.tile.primary .tile-title{color:var(--amber)}
.tile.primary .tile-ico{color:var(--ground); background:var(--amber); border-color:var(--amber); font-size:11px}
.info-panel{max-width:660px; padding:var(--s4)}
.info-panel .modal-title{margin-bottom:var(--s2)}
.info-text{font-size:16px; line-height:1.65; color:var(--ink); opacity:.94; margin:0 0 var(--s3)}
.info-list{list-style:none; margin:0 0 var(--s3); padding:0; display:flex; flex-direction:column; gap:14px}
.info-list li{display:flex; align-items:flex-start; gap:12px; font-size:16px; line-height:1.55}
.info-list li::before{content:"\2713"; flex:none; color:var(--teal); font-weight:700; margin-top:1px}
.info-links{display:flex; flex-wrap:wrap; gap:10px}
.info-link{font-family:var(--mono); font-size:13px; color:var(--ink); text-decoration:none; padding:10px 14px;
  border:1px solid var(--line); border-radius:9px; background:var(--panel2)}
.info-link:hover{border-color:var(--amber); color:var(--amber)}
.reading{margin-top:var(--s3); padding:var(--s2) var(--s3); border-left:3px solid var(--amber);
  background:linear-gradient(90deg, rgba(230,174,67,.08), transparent 80%);
  border-radius:0 10px 10px 0; font-size:15px; display:flex; align-items:center;
  justify-content:space-between; gap:var(--s2) var(--s4); flex-wrap:wrap}
.reading-text{flex:1 1 420px; max-width:92ch; line-height:1.55}
.reading-viz{flex:0 0 auto; width:540px; max-width:100%; background:var(--panel2); border:1px solid var(--line);
  border-radius:12px; padding:var(--s2); display:grid; grid-template-columns:auto minmax(0,1fr);
  gap:10px var(--s3); align-items:center}
@media(max-width:900px){.reading-viz{width:100%; grid-template-columns:1fr}}
.rv-title,.rv-legend{grid-column:1 / -1}
.rv-title{font-family:var(--mono); font-size:10.5px; letter-spacing:.08em; text-transform:uppercase; color:var(--muted)}
.rv-main{display:flex; align-items:center; gap:14px; max-width:260px}
.rv-expl{font-size:12px; color:var(--muted); line-height:1.4}
.rv-legend{font-size:11.5px; color:var(--muted); line-height:1.5; border-top:1px solid var(--line); padding-top:10px; margin-top:2px}
.rv-legend b{color:var(--ink); font-weight:600}
.rv-delta{font-family:var(--mono); font-weight:600; font-size:34px; line-height:1; letter-spacing:-.02em}
.rv-delta small{font-size:12px; margin-left:4px; opacity:.8; letter-spacing:0}
.rv-one{width:100%}
.rv-cap{display:flex; justify-content:space-between; font-family:var(--mono); font-size:11px;
  color:var(--muted); margin-bottom:10px}
.rv-cap b{color:var(--ink); font-weight:600}
.rv-bar{position:relative; height:8px; border-radius:4px; background:rgba(255,255,255,.12)}
.rv-fill{position:absolute; left:0; top:0; bottom:0; border-radius:4px}
.reading b{font-family:var(--disp); font-weight:700}
.reading .r-num{font-family:var(--mono); color:var(--amber)}

.board{display:grid; grid-template-columns:minmax(0,1fr) 580px; gap:var(--s3); margin-top:var(--s3);
  align-items:stretch; min-height:clamp(620px, calc(100vh - 300px), 980px)}
@media(max-width:1280px){.board{grid-template-columns:minmax(0,1fr) 440px}}
@media(max-width:900px){
  .board{grid-template-columns:1fr; min-height:0}
  .drill{min-height:0}
  .drill-in{position:static}
  .ev-list{flex:none; max-height:60vh}
}
.panel{background:var(--panel); border:1px solid var(--line); border-radius:14px}
.heatmap-panel{padding:var(--s3); display:flex; flex-direction:column}

.hm-head{display:flex; align-items:center; justify-content:space-between; margin-bottom:var(--s2); gap:12px}
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


.legend{display:flex; flex-wrap:wrap; align-items:center; gap:14px var(--s3); margin-bottom:var(--s2)}
.scale{display:flex; align-items:center; gap:10px}
.scale-bar{width:140px; height:10px; border-radius:6px;
  background:linear-gradient(90deg,var(--rust),var(--neutral),var(--teal))}
.scale-label{font-family:var(--mono); font-size:11px; color:var(--faint)}
.legend-soll{display:flex; align-items:center; gap:8px; font-size:12px; color:var(--muted)}
.tgt-legend{width:15px; height:15px; flex:none}
.soll-w{color:var(--amber)}

.grid{display:grid; gap:var(--s1)}
#grid{flex:1}
.ghead{display:grid; gap:8px}
.corner{font-family:var(--mono); font-size:11.5px; color:var(--ink); font-weight:600;
  align-self:end; letter-spacing:.04em; text-transform:uppercase; padding-bottom:6px}
.whead{font-family:var(--mono); font-size:12px; color:var(--muted); text-align:center;
  padding-bottom:6px; border-bottom:1px solid var(--line)}
.whead .wspan{color:var(--ink)}
.row{display:grid; gap:8px; align-items:stretch}
.rlabel{display:flex; flex-direction:column; justify-content:center; padding-right:8px}
.rlabel .rtitle{font-family:var(--disp); font-weight:500; font-size:15px; line-height:1.15;
  color:var(--ink)}
.rlabel .rsoll{font-family:var(--mono); font-size:11.5px; font-weight:600; color:var(--ink); margin-top:5px}
.rlabel .spark{margin-top:8px}

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
.tgt{position:absolute; top:50%; width:15px; height:15px; transform:translate(-50%,-50%);
  pointer-events:none; filter:drop-shadow(0 0 3px rgba(0,0,0,.5))}

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
.tb-ctrl .tb-exit{color:var(--muted)}
.tb-ctrl .tb-exit:hover{color:var(--ink)}
.tb-ctrl .prim{background:var(--amber); color:var(--ground); border-color:var(--amber); font-weight:600}

.drill{position:relative; min-height:520px}
.drill-in{position:absolute; inset:0; padding:var(--s3); display:flex; flex-direction:column; min-height:0}
.drill-head .d-pillar{font-family:var(--disp); font-weight:700; font-size:19px; line-height:1.1}
.drill-head .d-win{font-family:var(--mono); font-size:12px; color:var(--muted); margin-top:4px}
.d-box{background:var(--panel2); border:1px solid var(--line); border-radius:12px; padding:var(--s3); margin:var(--s2) 0}
.d-box-title{font-family:var(--disp); font-weight:600; font-size:15px}
.d-box-sub{font-size:12.5px; color:var(--muted); margin:6px 0 var(--s3); line-height:1.5}
.d-box-body{display:flex; gap:var(--s3); align-items:center}
.d-ring{width:200px; height:auto; flex:0 0 auto}
.d-stats{display:grid; grid-template-columns:1fr 1fr; gap:var(--s3) var(--s2); flex:1; min-width:0}
.d-stat{cursor:help}
.d-stat .k{font-family:var(--mono); font-size:11.5px; letter-spacing:.08em; text-transform:uppercase; color:var(--faint)}
.d-stat .v{font-family:var(--mono); font-size:25px; font-weight:600; margin-top:4px; line-height:1.1}
.d-stat .s{font-size:12.5px; color:var(--muted); margin-top:5px; line-height:1.45}
.d-evhead{font-family:var(--mono); font-size:11px; letter-spacing:.06em; text-transform:uppercase; color:var(--muted); margin-bottom:12px}
.ev-list{display:flex; flex-direction:column; gap:12px; flex:1; min-height:0; overflow-y:auto; padding-right:4px}
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

footer{margin-top:var(--s4); color:var(--faint); font-size:12px; font-family:var(--mono); letter-spacing:.02em}
footer .dot{color:var(--line); margin:0 8px}
footer .note{color:var(--faint); opacity:.85}

@media(prefers-reduced-motion:reduce){*{transition:none!important}}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="head-row"><div class="head-text">
    <div class="eyebrow">Strategic Drift Engine</div>
    <h1>Wohin die Aufmerksamkeit wirklich floss</h1>
    <p class="sub">Jede Zelle vergleicht die gemessene Aufmerksamkeit auf eine strategische Säule mit ihrem Soll über die Zeit. Die Zielmarke markiert das Soll. Eine Zelle wählen, um die Nachrichten zu sehen, aus denen der Wert entstanden ist.</p>
    </div>
    <div class="tile-group">
      <button class="tile" id="demoBtn" aria-haspopup="dialog"><span class="tile-ico" aria-hidden="true">i</span><span class="tile-txt"><span class="tile-title">Demoprojekt</span><span class="tile-sub">Synthetische Daten</span></span></button>
      <button class="tile" id="govBtn" aria-haspopup="dialog"><span class="tile-ico" aria-hidden="true">&#10003;</span><span class="tile-txt"><span class="tile-title">Governance-Regeln</span><span class="tile-sub">4 Grundsätze</span></span></button>
      <button class="tile primary" id="tourBtn"><span class="tile-ico" aria-hidden="true">&#9654;</span><span class="tile-txt"><span class="tile-title" id="tourBtnLabel">Geführte Tour starten</span><span class="tile-sub" id="tourCtaSub"></span></span></button>
    </div></div>
    <div class="reading" id="reading"></div>
  </header>

  <div class="board">
    <section class="panel heatmap-panel">
      <div class="hm-head">
        <div class="hm-title">Aufmerksamkeit im Zeitverlauf</div>
        <div class="hm-actions">
          <button class="ghost-btn" id="strategyBtn">Strategie</button>
        </div>
      </div>
      <div class="legend">
        <div class="scale">
          <span class="scale-label">unter Soll</span>
          <span class="scale-bar"></span>
          <span class="scale-label">über Soll</span>
        </div>
        <div class="legend-soll"><span id="legendTgt" style="display:inline-flex"></span> Zielmarke = Soll je Säule</div>
      </div>
      <div id="grid" class="grid"></div>
      <div class="tourbar" id="tourbar" hidden>
        <span class="tb-step" id="tbStep"></span>
        <div class="tb-body"><div class="tb-title" id="tbTitle"></div><div class="tb-text" id="tbText"></div></div>
        <div class="tb-ctrl">
          <button id="tbPrev">Zurück</button>
          <button id="tbNext" class="prim">Weiter</button>
          <button id="tbEnd" class="tb-exit">&#10005; Tour verlassen</button>
        </div>
      </div>
    </section>

    <aside class="panel drill" id="drill"></aside>
  </div>

  <footer id="foot"></footer>
</div>

<div class="modal-overlay" id="strategyModal" hidden role="dialog" aria-modal="true" aria-labelledby="strategyTitle">
  <div class="modal-panel">
    <button class="modal-close" id="strategyClose" aria-label="Schließen">×</button>
    <h2 class="modal-title" id="strategyTitle">Strategie-Steckbrief</h2>
    <div id="strategyBody"></div>
  </div>
</div>

<div class="modal-overlay" id="demoModal" hidden role="dialog" aria-modal="true" aria-labelledby="demoTitle">
  <div class="modal-panel info-panel">
    <button class="modal-close" id="demoClose" aria-label="Schließen">×</button>
    <div class="eyebrow">Demoprojekt</div>
    <h2 class="modal-title" id="demoTitle">Strategic Drift Engine</h2>
    <p class="info-text">Ein Workflow aus vier Agenten misst die Lücke zwischen Strategie und tatsächlicher Kommunikation.</p>
    <p class="info-text">Alle Daten sind synthetisch: ein fiktives Unternehmen, TechCo, mit erfundenen Personen, Nachrichten und Kalendereinträgen. Es gibt keine echten Daten und keine echten Personen.</p>
    <div class="info-links">
      <a class="info-link" href="bauprozess.html" target="_blank" rel="noopener">So wurde das gebaut</a>
      <a class="info-link" href="https://github.com/frankknebeljanssen-create/strategic-drift-engine" target="_blank" rel="noopener">Quellcode auf GitHub</a>
    </div>
  </div>
</div>

<div class="modal-overlay" id="govModal" hidden role="dialog" aria-modal="true" aria-labelledby="govTitle">
  <div class="modal-panel info-panel">
    <button class="modal-close" id="govClose" aria-label="Schließen">×</button>
    <div class="eyebrow">Datenschutz und Mitbestimmung</div>
    <h2 class="modal-title" id="govTitle">Governance-Regeln</h2>
    <ul class="info-list">
      <li>Nur Opt-in auf Kanalebene</li>
      <li>Nur öffentliche Kanäle, nie Direktnachrichten</li>
      <li>Aggregiert auf Säulenebene, nie Einzelbewertung</li>
      <li>Betriebsrat und Datenschutzbeauftragte von Anfang an eingebunden, nicht erst nachträglich</li>
    </ul>
    <div class="info-links">
      <a class="info-link" href="https://github.com/frankknebeljanssen-create/strategic-drift-engine#governance-und-datenschutz" target="_blank" rel="noopener">Mehr dazu im README</a>
    </div>
  </div>
</div>

<script>
const DATA = __DATA__;
const STRATEGY = __STRATEGY__;

// Zielmarke als Fadenkreuz: Kreis mit durchgehendem Kreuz, das ueber den Rand hinausragt.
// Einzige Quelle fuer das Symbol, alle Soll-Positionen (Zellen, Ring, Kernaussage, Legende) nutzen sie.
const TGT_INNER = '<circle cx="8" cy="8" r="4.8" fill="#0F1E27" fill-opacity=".6" stroke="#E6AE43" stroke-width="1.5"/>'+
  '<path d="M8 .8V15.2M.8 8H15.2" stroke="#E6AE43" stroke-width="1.5" stroke-linecap="round" fill="none"/>';
function tgtSvg(cls, style){return '<svg class="'+cls+'"'+(style?' style="'+style+'"':'')+' viewBox="0 0 16 16" aria-hidden="true">'+TGT_INNER+'</svg>';}
function tgtAt(leftPct){return tgtSvg("tgt", "left:"+leftPct+"%");}

// Das Wort "Soll" immer in der Farbe der Zielmarke (Amber), ausser in den Beleg-Texten aus den Daten.
function colorSoll(root){
  const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {acceptNode:n=>
    (/\bSoll\b/.test(n.nodeValue) && !n.parentElement.closest(".soll-w,.ev-list,script,style")) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT});
  const nodes = []; while(w.nextNode()) nodes.push(w.currentNode);
  nodes.forEach(n=>{
    const frag = document.createDocumentFragment();
    n.nodeValue.split(/(\bSoll\b)/).forEach(part=>{
      if(part==="Soll"){const sp=document.createElement("span"); sp.className="soll-w"; sp.textContent=part; frag.appendChild(sp);}
      else if(part){frag.appendChild(document.createTextNode(part));}
    });
    n.parentNode.replaceChild(frag, n);
  });
}
function ring(c){
  // Potentiometer-Skala: 270 Grad, Oeffnung unten. Winkel in Grad im Uhrzeigersinn ab 12 Uhr:
  // 0% = 225 Grad (unten links), 50% = 360 Grad (oben), 100% = 495 Grad (unten rechts).
  const cx=90, cy=80, R=62, SW=12;
  const clamp=v=>Math.max(0,Math.min(1,v));
  const ist=clamp(c.ist_anteil), soll=clamp(c.soll_anteil);
  const col = c.drift<0 ? "#C85434" : "#2E90B4";
  const ang = f => (225 + 270*f)*Math.PI/180;
  const pt = (f, r) => [cx + r*Math.sin(ang(f)), cy - r*Math.cos(ang(f))];
  const arc = f => {const a=pt(0,R), b=pt(f,R); return "M"+a[0].toFixed(2)+" "+a[1].toFixed(2)+" A"+R+" "+R+" 0 "+(270*f>180?1:0)+" 1 "+b[0].toFixed(2)+" "+b[1].toFixed(2);};
  const ticks = [0.25,0.5,0.75].map(f=>{const a=pt(f,R+SW/2+3), b=pt(f,R+SW/2+9);
    return '<line x1="'+a[0].toFixed(2)+'" y1="'+a[1].toFixed(2)+'" x2="'+b[0].toFixed(2)+'" y2="'+b[1].toFixed(2)+'" stroke="rgba(255,255,255,.4)" stroke-width="1.6" stroke-linecap="round"/>';}).join("");
  const s0=pt(0,R), s1=pt(1,R), m=pt(soll,R);
  const lab = (x,y,t)=>'<text x="'+x.toFixed(1)+'" y="'+y.toFixed(1)+'" text-anchor="middle" font-family="IBM Plex Mono, monospace" font-size="12" font-weight="600" fill="#8298A4">'+t+'</text>';
  return '<svg class="d-ring" viewBox="0 0 180 156" role="img" aria-label="Ist '+Math.round(ist*100)+' Prozent, Soll '+Math.round(soll*100)+' Prozent, Skala 0 bis 100 Prozent">'+
    '<path d="'+arc(1)+'" fill="none" stroke="rgba(255,255,255,.12)" stroke-width="'+SW+'" stroke-linecap="round"/>'+
    (ist>0.004 ? '<path d="'+arc(ist)+'" fill="none" stroke="'+col+'" stroke-width="'+SW+'" stroke-linecap="round"/>' : '')+
    ticks+
    '<g transform="translate('+m[0].toFixed(2)+' '+m[1].toFixed(2)+') scale(1.2) translate(-8 -8)">'+TGT_INNER+'</g>'+
    lab(s0[0]-10, s0[1]+24, "0%")+lab(s1[0]+10, s1[1]+24, "100%")+
    '<text x="'+cx+'" y="'+(cy+8)+'" text-anchor="middle" font-family="IBM Plex Mono, monospace" font-size="32" font-weight="600" fill="#EAF1F4">'+Math.round(ist*100)+'%</text>'+
    '<text x="'+cx+'" y="'+(cy+26)+'" text-anchor="middle" font-family="IBM Plex Mono, monospace" font-size="10.5" letter-spacing="1.5" fill="#8298A4">IST</text></svg>';
}

const MON = ["Jan","Feb","Mrz","Apr","Mai","Jun","Jul","Aug","Sep","Okt","Nov","Dez"];
function fdate(iso){const [y,m,d]=iso.split("-").map(Number); return d+". "+MON[m-1];}
function frange(w){return fdate(w.start)+" – "+fdate(w.end);}
function fdatefull(iso){const [y,m,d]=iso.split("-").map(Number); return d+". "+MON[m-1]+" "+y;}

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
  grid.style.gridTemplateRows = "auto repeat("+pillars.length+", minmax(116px,1fr))";
  const head = document.createElement("div");
  head.className="ghead"; head.style.gridTemplateColumns=cols;
  head.innerHTML = '<div class="corner">Säule &nbsp;\\&nbsp; Zeitraum</div>' +
    windows.map(w=>'<div class="whead"><span class="wspan">'+frange(w)+'</span></div>').join("");
  grid.appendChild(head);

  pillars.forEach(p=>{
    const row = document.createElement("div");
    row.className="row"; row.style.gridTemplateColumns=cols;
    const label = document.createElement("div");
    label.className="rlabel";
    label.innerHTML = '<div class="rtitle">'+p.title+'</div><div class="rsoll">Soll '+pct(p.soll_anteil)+'</div>'+sparkline(p.key);
    row.appendChild(label);
    windows.forEach(w=>{
      const c = cellMap[w.index+":"+p.key];
      const btn = document.createElement("button");
      btn.className="cell"; btn.style.background=driftColor(c.drift);
      btn.setAttribute("aria-label", p.title+", "+frange(w)+": Ist "+pct(c.ist_anteil)+", Abweichung "+signed(c.drift)+" Prozentpunkte");
      const fill = Math.max(0,Math.min(100, c.ist_anteil*100));
      const tick = Math.max(0,Math.min(100, c.soll_anteil*100));
      btn.innerHTML =
        '<div class="cell-ist">'+pct(c.ist_anteil)+'</div>'+
        '<div class="cell-bar"><div class="cell-fill" style="width:'+fill+'%"></div>'+
          tgtAt(tick)+'</div>'+
        '<div class="cell-drift">'+signed(c.drift)+' PP</div>';
      btn.dataset.key = w.index+":"+p.key;
      btn.addEventListener("click",()=>{ if(tour.active) endTour(); select(w.index,p.key); });
      row.appendChild(btn);
    });
    grid.appendChild(row);
  });
}

const TYPE_LABEL = {slack:"Slack", mail:"Mail", meeting_note:"Besprechung", meeting:"Besprechung", calendar:"Kalender"};
function trSignal(s){
  let m;
  if((m=s.match(/^scores: (.*)$/))) return "Werte: "+m[1];
  if((m=s.match(/^chosen: (.*) \(score (-?\d+)\)$/))) return "gewählt: "+m[1]+" (Wert "+m[2]+")";
  if((m=s.match(/^reduces (.*?): (.*)$/))) return "senkt "+m[1]+": "+m[2];
  if((m=s.match(/^calendar category: (.*?) \(no pillar mapping\)$/))) return "Kalender-Kategorie: "+m[1]+" (keiner Säule zugeordnet)";
  if((m=s.match(/^calendar category: (.*?) -> (.*)$/))) return "Kalender-Kategorie: "+m[1]+" -> "+m[2];
  return s;
}
function trContribution(s){
  let m, base = s, tail = "";
  const rm = s.match(/^(.*) and reduces (.+)\.$/);
  if(rm){ base = rm[1]+"."; tail = " Zugleich senkt die Nachricht "+rm[2]+"."; }
  if((m=base.match(/^Contributes to (.+?): keywords (.+) outweigh other signals\.$/))) return "Trägt zu "+m[1]+" bei: Die Schlüsselwörter "+m[2]+" überwiegen die anderen Signale."+tail;
  if((m=base.match(/^Contributes to (.+?): calendar event categorized as '(.+)'\.$/))) return "Trägt zu "+m[1]+" bei: Kalendertermin der Kategorie '"+m[2]+"'."+tail;
  if((m=base.match(/^Contributes to (.+?) on keyword scoring\.$/))) return "Trägt zu "+m[1]+" bei (Schlüsselwort-Bewertung)."+tail;
  return s;
}
const TYPE_BADGE = {slack:"b-slack", mail:"b-mail", meeting:"b-meeting", meeting_note:"b-meeting", calendar:"b-calendar"};

function select(wi, pkey){
  selected = wi+":"+pkey;
  document.querySelectorAll(".cell").forEach(c=>c.classList.toggle("sel", c.dataset.key===selected));
  renderDrill(wi, pkey);
  colorSoll(document.body);
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
  if(c >= 0.9) return "sehr hoch";
  if(c >= 0.75) return "hoch";
  if(c >= 0.5) return "mittel";
  return "niedrig";
}

function evidenceCard(e){
  const badge = TYPE_BADGE[e.type]||"b-calendar";
  const chan = (TYPE_LABEL[e.type]||e.type) + (e.channel? " · "+e.channel : "");
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
    .map(s=>'<li class="'+signalClass(s)+'">'+escapeHtml(trSignal(s))+"</li>")
    .join("");
  const contribution = trContribution(e.contribution || e.rationale || "");

  return '<div class="ev">'+
    '<div class="ev-top"><span class="badge '+badge+'">'+chan+'</span>'+
    '<span class="ev-meta">'+(e.author||"-")+' · '+fdate(e.ts.slice(0,10))+'</span></div>'+
    '<div class="ev-snip" data-preview="'+escapeHtml(preview)+'" data-full="'+escapeHtml(rawFull)+'">'+
      escapeHtml(preview)+'</div>'+
    (needsToggle ? '<button class="ev-toggle" type="button">Ganze Nachricht anzeigen</button>' : '')+
    '<div class="ev-eng">'+
      '<div class="ev-eng-title">So hat die Engine das gelesen</div>'+
      (contribution ? '<div class="ev-eng-row"><span class="ev-eng-k">Beitrag</span>'+
        '<span class="ev-eng-v">'+escapeHtml(contribution)+'</span></div>' : '')+
      (signals ? '<div class="ev-eng-row"><span class="ev-eng-k">Erkannte Signale</span>'+
        '<ul class="ev-signals">'+signals+'</ul></div>' : '')+
      '<div class="ev-eng-row"><span class="ev-eng-k">Konfidenz</span>'+
        '<div class="ev-conf"><span class="conf-track">'+
        '<span class="conf-fill" style="width:'+conf+'%"></span></span>'+
        '<span class="conf-num">'+confNum+'</span>'+
        (cLabel ? '<span class="conf-label">'+cLabel+'</span>' : '')+
        '</div>'+
        '<div class="conf-scale">0 niedrig · 1 maximal</div>'+
      '</div>'+
    '</div>'+
  '</div>';
}

// Event-Delegation für Show-full/Show-less-Toggle.
document.addEventListener("click", (ev)=>{
  const btn = ev.target;
  if(!(btn instanceof HTMLElement) || !btn.classList.contains("ev-toggle")) return;
  const snip = btn.previousElementSibling;
  if(!snip || !snip.classList.contains("ev-snip")) return;
  const expanded = snip.classList.toggle("full");
  if(expanded){
    snip.textContent = snip.dataset.full || "";
    btn.textContent = "Weniger anzeigen";
  } else {
    snip.textContent = snip.dataset.preview || "";
    btn.textContent = "Ganze Nachricht anzeigen";
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
  drill.innerHTML = '<div class="drill-in">'+
    '<div class="drill-head"><div class="d-pillar">'+p.title+'</div>'+
      '<div class="d-win">'+fdatefull(w.start)+' – '+fdatefull(w.end)+'</div></div>'+
    '<div class="d-box">'+
      '<div class="d-box-title">Diese Zelle im Überblick</div>'+
      '<div class="d-box-sub">Gemessene gegen geplante Aufmerksamkeit für diese Säule in diesem Zeitfenster. 0% unten links, im Uhrzeigersinn bis 100% unten rechts. Der Bogen zeigt den Ist-Anteil, die Zielmarke markiert den Soll-Wert auf derselben Skala.</div>'+
      '<div class="d-box-body">'+ring(c)+
        '<div class="d-stats">'+
          '<div class="d-stat" title="Ist: Anteil der zugeordneten Nachrichten dieses Zeitfensters, der auf diese Säule entfällt."><div class="k">Ist</div><div class="v">'+pct(c.ist_anteil)+'</div><div class="s">gemessener Anteil</div></div>'+
          '<div class="d-stat" title="Soll: Gewichtung dieser Säule laut Strategie."><div class="k">Soll</div><div class="v" style="color:var(--amber)">'+pct(c.soll_anteil)+'</div><div class="s">geplanter Anteil</div></div>'+
          '<div class="d-stat" title="Drift: Ist minus Soll in Prozentpunkten. Positiv heißt mehr Aufmerksamkeit als geplant."><div class="k">Drift</div><div class="v" style="color:'+driftCol+'">'+signed(c.drift)+' PP</div><div class="s">Ist minus Soll, in Prozentpunkten</div></div>'+
          '<div class="d-stat" title="Belege: Anzahl der Nachrichten, die in diese Zelle eingeflossen sind."><div class="k">Belege</div><div class="v">'+c.n_sources+'</div><div class="s">Nachrichten in dieser Zelle</div></div>'+
        '</div></div></div>'+
    '<div class="d-evhead">Nachrichten hinter dieser Zahl</div>'+
    '<div class="ev-list">'+(items||'<div style="color:var(--faint);padding:20px 0">Keine Belege in dieser Zelle.</div>')+'</div></div>';
}

function renderReading(){
  const peak = DATA.cells.reduce((a,b)=>Math.abs(a.drift)>Math.abs(b.drift)?a:b);
  const w = windows[peak.window_index];
  const wcells = pillars.map(p=>cellMap[peak.window_index+":"+p.key]);
  const low = wcells.reduce((a,b)=>a.drift<b.drift?a:b);
  const verb = peak.drift>0 ? "zieht die meiste Aufmerksamkeit auf sich" : "wird am stärksten vernachlässigt";
  let txt = '<b>'+pillarTitle(peak.pillar_key)+'</b> '+verb+' im Zeitraum <span class="r-num">'+frange(w)+
    '</span> mit <span class="r-num">'+pct(peak.ist_anteil)+'</span> gegen ein Soll von <span class="r-num">'+pct(peak.soll_anteil)+'</span>.';
  if(low.pillar_key!==peak.pillar_key && low.drift<0){
    txt += ' Im selben Fenster fällt <b>'+pillarTitle(low.pillar_key)+'</b> auf <span class="r-num">'+pct(low.ist_anteil)+'</span>.';
  }
  const col = peak.drift<0 ? "var(--rust)" : "var(--teal)";
  const istW = Math.max(0,Math.min(100,peak.ist_anteil*100)), sollW = Math.max(0,Math.min(100,peak.soll_anteil*100));
  const more = peak.drift>0 ? "mehr" : "weniger";
  const viz =
    '<div class="reading-viz" role="group" aria-label="Ist '+Math.round(peak.ist_anteil*100)+' Prozent gegen Soll '+
      Math.round(peak.soll_anteil*100)+' Prozent, Abweichung '+signed(peak.drift)+' Prozentpunkte">'+
      '<div class="rv-title">Abweichung vom Soll</div>'+
      '<div class="rv-main">'+
        '<div class="rv-delta" style="color:'+col+'">'+signed(peak.drift)+'<small>PP</small></div>'+
        '<div class="rv-expl">Prozentpunkte '+more+' Aufmerksamkeit als geplant</div>'+
      '</div>'+
      '<div class="rv-one">'+
        '<div class="rv-cap"><span>Ist <b>'+pct(peak.ist_anteil)+'</b></span><span>Soll <b>'+pct(peak.soll_anteil)+'</b></span></div>'+
        '<div class="rv-bar"><span class="rv-fill" style="width:'+istW+'%;background:'+col+'"></span>'+tgtAt(sollW)+'</div>'+
      '</div>'+
      '<div class="rv-legend"><b>Ist</b>: gemessener Anteil dieser Säule an allen zugeordneten Nachrichten im Zeitfenster. '+
        '<b>Soll</b> (Zielmarke): geplanter Anteil laut Strategie. <b>PP</b> = Prozentpunkte, Ist minus Soll.</div>'+
    '</div>';
  document.getElementById("reading").innerHTML = '<div class="reading-text">'+txt+'</div>'+viz;
}

function buildTour(){
  const steps=[]; const lastW=windows.length-1;
  const w0 = pillars.map(p=>cellMap["0:"+p.key]);
  const near0 = w0.reduce((a,b)=>Math.abs(a.drift)<Math.abs(b.drift)?a:b);
  steps.push({wi:0, pkey:near0.pillar_key, title:"Was hier zu sehen ist",
    text:"Die Führung von TechCo hat in einem einseitigen Steckbrief drei strategische Säulen festgelegt. Die Heat-Map zeigt, wie viel Aufmerksamkeit jede Säule tatsächlich bekam, Zeitfenster für Zeitfenster, gemessen an diesem Soll. Über den Button Strategie oben rechts lässt sich jederzeit der ursprüngliche Steckbrief ansehen."});
  steps.push({wi:0, pkey:near0.pillar_key, title:"Ausgangslage",
    text:"Im ersten Zeitfenster liegen die Säulen nahe am Soll. "+pillarTitle(near0.pillar_key)+" trifft den Zielwert fast genau."});
  const peak = DATA.cells.reduce((a,b)=>Math.abs(a.drift)>Math.abs(b.drift)?a:b);
  steps.push({wi:peak.window_index, pkey:peak.pillar_key, title:"Größte Abweichung",
    text:pillarTitle(peak.pillar_key)+" erreicht "+pct(peak.ist_anteil)+" gegen ein Soll von "+pct(peak.soll_anteil)+" ("+signed(peak.drift)+" PP). Rechts stehen die Nachrichten, aus denen dieser Wert entstand."});
  const wc = pillars.map(p=>cellMap[peak.window_index+":"+p.key]);
  const opp = wc.reduce((a,b)=>a.drift<b.drift?a:b);
  if(opp.pillar_key!==peak.pillar_key){
    steps.push({wi:peak.window_index, pkey:opp.pillar_key, title:"Die Kehrseite",
      text:"Im selben Fenster fällt "+pillarTitle(opp.pillar_key)+" auf "+pct(opp.ist_anteil)+" ("+signed(opp.drift)+" PP). Was eine Säule gewinnt, verliert eine andere."});
  }
  const wl = pillars.map(p=>cellMap[lastW+":"+p.key]);
  const nearL = wl.reduce((a,b)=>Math.abs(a.drift)<Math.abs(b.drift)?a:b);
  const spread = Math.round(Math.max(...wl.map(c=>Math.abs(c.drift)))*100);
  steps.push({wi:lastW, pkey:nearL.pillar_key, title:"Zum Ende",
    text:"Im letzten Fenster nähern sich die Säulen wieder an. Die größte verbleibende Abweichung beträgt "+spread+" Prozentpunkte."});
  steps.push({wi:peak.window_index, pkey:peak.pillar_key, title:"So lässt sich jede Zahl prüfen",
    text:"Eine Zelle anklicken, dann eine Nachricht aufklappen. Der Block darunter zeigt genau, welche Wörter die Engine erkannt hat und ob sie eine Säule stützen oder ihr entgegenwirken. Das ist die lückenlose Spur von der Behauptung zum Beleg."});
  return steps;
}

const tour = {active:false, i:0, steps:[]};
function startTour(){
  tour.active=true; tour.i=0; tour.steps=buildTour();
  document.getElementById("grid").classList.add("touring");
  document.getElementById("tourbar").hidden=false;
  document.getElementById("tourBtnLabel").textContent="Tour läuft";
  showTourStep();
}
function showTourStep(){
  const s=tour.steps[tour.i];
  select(s.wi, s.pkey);
  document.getElementById("tbStep").textContent="Schritt "+(tour.i+1)+" / "+tour.steps.length;
  document.getElementById("tbTitle").textContent=s.title;
  document.getElementById("tbText").textContent=s.text;
  colorSoll(document.getElementById("tbText"));
  document.getElementById("tbPrev").disabled = tour.i===0;
  document.getElementById("tbNext").textContent = tour.i===tour.steps.length-1 ? "Von vorn" : "Weiter";
  document.getElementById("tourbar").scrollIntoView({block:"nearest", behavior:"smooth"});
}
function peakCell(){return DATA.cells.reduce((a,b)=>Math.abs(a.drift)>Math.abs(b.drift)?a:b);}
// reset=true: komplett zurueck zur normalen Dashboard-Ansicht (Standardauswahl, Seitenanfang).
function endTour(reset){
  tour.active=false;
  document.getElementById("grid").classList.remove("touring");
  document.getElementById("tourbar").hidden=true;
  document.getElementById("tourBtnLabel").textContent="Geführte Tour starten";
  if(reset===true){
    const best = peakCell();
    select(best.window_index, best.pillar_key);
    window.scrollTo({top:0, behavior:"smooth"});
  }
}
document.getElementById("tourBtn").addEventListener("click",()=>{ tour.active?endTour(true):startTour(); });
document.getElementById("tbPrev").addEventListener("click",()=>{ if(tour.i>0){tour.i--; showTourStep();} });
document.getElementById("tbNext").addEventListener("click",()=>{ tour.i=(tour.i+1)%tour.steps.length; showTourStep(); });
document.getElementById("tbEnd").addEventListener("click", ()=>endTour(true));

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
  const w = p.soll_gewicht!=null ? Math.round(p.soll_gewicht*100)+"%" : "-";
  const kris = (p.kriterien||[]).map(k=>"<li>"+escapeHtml(k)+"</li>").join("");
  return '<div class="p-card">'+
    '<div class="p-card-head"><div class="p-card-title">'+escapeHtml(p.title||p.key)+'</div>'+
      '<span class="p-card-w" title="Sollgewicht">'+w+'</span></div>'+
    (p.grundsatz ? '<div class="p-card-k">Grundsatz</div><div class="p-card-p">'+escapeHtml(p.grundsatz)+'</div>' : '')+
    (kris ? '<div class="p-card-k">Kriterien</div><ul>'+kris+'</ul>' : '')+
  '</div>';
}

function openStrategy(){
  const md = renderMarkdown(STRATEGY.steckbrief_markdown||"");
  const cards = (STRATEGY.pillars||[]).map(pillarCard).join("");
  document.getElementById("strategyBody").innerHTML =
    '<div class="md-body">'+md+'</div>'+
    '<div class="modal-sep"></div>'+
    '<div class="derived-title">Abgeleitete Säulen</div>'+
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
// Info-Modals (Demoprojekt, Governance): X, Klick daneben und Escape schliessen.
const INFO_MODALS = ["demoModal","govModal"];
function openInfo(id){
  document.getElementById(id).hidden = false;
  document.body.style.overflow = "hidden";
  document.getElementById(id).querySelector(".modal-close").focus();
}
function closeAnyModal(){
  for(const id of ["demoModal","govModal","strategyModal"]){
    const m = document.getElementById(id);
    if(!m.hidden){ m.hidden = true; document.body.style.overflow = ""; return true; }
  }
  return false;
}
document.getElementById("demoBtn").addEventListener("click", ()=>openInfo("demoModal"));
document.getElementById("govBtn").addEventListener("click", ()=>openInfo("govModal"));
INFO_MODALS.forEach(id=>{
  const m = document.getElementById(id);
  m.querySelector(".modal-close").addEventListener("click", closeAnyModal);
  m.addEventListener("click", e=>{ if(e.target===m) closeAnyModal(); });
});
document.addEventListener("keydown", e=>{
  if(e.key==="Escape"){
    if(!closeAnyModal() && tour.active) endTour(true);
  }
});

function renderFoot(){
  const tot = Object.values(DATA.evidence).reduce((a,v)=>a+v.length,0);
  document.getElementById("foot").innerHTML =
    '<span class="note">Synthetischer Demo-Datensatz, fiktives Unternehmen TechCo.</span>' + '<span class="dot">•</span>' +
    windows.length+" Zeitfenster" + '<span class="dot">•</span>' + pillars.length+" Säulen" +
    '<span class="dot">•</span>' + tot+" verknüpfte Belege" + '<span class="dot">•</span>' + "Lauf "+DATA.run_id +
    '<span class="dot">•</span>' + '<a href="bauprozess.html" target="_blank" rel="noopener" style="color:inherit; text-decoration:underline; text-underline-offset:2px">So wurde das gebaut</a>' +
    '<span class="dot">•</span>' + 'Ein Demoprojekt von <a href="https://github.com/frankknebeljanssen-create/strategic-drift-engine" target="_blank" rel="noopener" style="color:inherit; text-decoration:underline; text-underline-offset:2px">Frank Knebel-Janssen</a>';
}

document.getElementById("legendTgt").innerHTML = tgtSvg("tgt-legend");
renderGrid(); renderReading(); renderFoot();
document.getElementById("tourCtaSub").textContent = buildTour().length+" Schritte";
(function(){
  const best = peakCell();
  select(best.window_index, best.pillar_key);
})();
</script>
</body>
</html>"""

out = HTML.replace("__DATA__", data_js).replace("__STRATEGY__", strategy_js)
(here / "index.html").write_text(out, encoding="utf-8")
print(f"index.html written ({len(out)} characters)")
