#!/usr/bin/env python3
"""
FitOut Post — Admin Server
==========================
Run:    python admin.py
Opens:  http://localhost:5050

Tabs:
  α Edge (AlphaEdge) — manage curated articles
  β Edge (BetaEdge)  — manage polls and view results

Voting API (used by betaedge.html):
  GET  /api/polls          — all polls with live vote counts
  POST /api/vote           — submit registration + vote
  GET  /api/votes/{id}     — admin: votes for one poll
"""

import json, hashlib, webbrowser, threading, sys, re
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

BASE           = Path(__file__).parent
ALPHAEDGE_FILE  = BASE / "alphaedge.json"
POLLS_FILE      = BASE / "polls.json"
VOTES_FILE      = BASE / "votes.json"
GAMMAEDGE_FILE  = BASE / "gammaedge.json"
INTEL_FILE      = BASE / "intelligence.json"
BUILD_PY       = BASE / "build.py"
PORT           = 5050

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("⚠  Run: pip install -r requirements.txt --break-system-packages")
    sys.exit(1)

HEADERS = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

DOMAIN_NAMES = {
    "ft.com":"Financial Times","wsj.com":"Wall Street Journal","bloomberg.com":"Bloomberg",
    "reuters.com":"Reuters","bbc.co.uk":"BBC","bbc.com":"BBC","theguardian.com":"The Guardian",
    "nytimes.com":"New York Times","economist.com":"The Economist","cnbc.com":"CNBC",
    "forbes.com":"Forbes","hbr.org":"Harvard Business Review","mckinsey.com":"McKinsey",
    "pwc.com":"PwC","deloitte.com":"Deloitte","ey.com":"EY","kpmg.com":"KPMG",
    "jll.com":"JLL","cbre.com":"CBRE","cushmanwakefield.com":"Cushman & Wakefield",
    "savills.com":"Savills","knightfrank.com":"Knight Frank","colliers.com":"Colliers",
    "arcadis.com":"Arcadis","arup.com":"Arup","aecom.com":"AECOM","gensler.com":"Gensler",
    "arabianbusiness.com":"Arabian Business","zawya.com":"Zawya","meed.com":"MEED",
    "constructionweekonline.com":"Construction Week","thenationalnews.com":"The National",
    "architectsjournal.co.uk":"Architects Journal","dezeen.com":"Dezeen",
    "interiordesign.net":"Interior Design","contractdesign.com":"Contract Design",
    "businessinsider.com":"Business Insider",
}


# ── Article fetching ──────────────────────────────────────────────────────────
def fetch_article_meta(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        resp.raise_for_status()
    except Exception as e:
        raise ValueError(f"Could not fetch URL: {e}")
    soup = BeautifulSoup(resp.content, "html.parser")
    def og(p): t=soup.find("meta",property=p) or soup.find("meta",attrs={"name":p}); return (t.get("content") or "").strip() if t else ""
    title   = og("og:title") or og("twitter:title") or (soup.title.string.strip() if soup.title else "") or url
    summary = og("og:description") or og("description") or og("twitter:description")
    if not summary:
        for p in soup.find_all("p"):
            txt = p.get_text(" ",strip=True)
            if len(txt)>100: summary=txt; break
    summary = summary[:600] if summary else ""
    pub = og("article:published_time") or og("og:article:published_time") or og("datePublished")
    if not pub:
        for s in soup.find_all("script",type="application/ld+json"):
            try:
                ld=json.loads(s.string or "")
                if isinstance(ld,list): ld=ld[0]
                pub=ld.get("datePublished","")
                if pub: break
            except: pass
    domain = urlparse(url).netloc.lower().removeprefix("www.")
    return {"title":title,"summary":summary,"published":pub,
            "source":DOMAIN_NAMES.get(domain,domain),"url":url,
            "accessed":datetime.now(timezone.utc).isoformat()}


# ── Data helpers ──────────────────────────────────────────────────────────────
def load(path, default):
    if path.exists():
        try: return json.loads(path.read_text("utf-8"))
        except: pass
    return default

def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")

def save_alphaedge(data):
    data["last_updated"]=datetime.now(timezone.utc).isoformat()
    data["total_articles"]=len(data["articles"])
    ALPHAEDGE_FILE.write_text(json.dumps(data,ensure_ascii=False,indent=2),"utf-8")
    _rebuild_alphaedge()

def save_polls(data): POLLS_FILE.write_text(json.dumps(data,ensure_ascii=False,indent=2),"utf-8")
def save_votes(data): VOTES_FILE.write_text(json.dumps(data,ensure_ascii=False,indent=2),"utf-8")

def _rebuild_alphaedge():
    try:
        import importlib.util
        spec=importlib.util.spec_from_file_location("build",BUILD_PY)
        mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        mod.build_alphaedge()
    except Exception as e: print(f"⚠  AlphaEdge rebuild: {e}")

def _rebuild_betaedge():
    try:
        import importlib.util
        spec=importlib.util.spec_from_file_location("build",BUILD_PY)
        mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        mod.build_betaedge()
    except Exception as e: print(f"⚠  BetaEdge rebuild: {e}")

def save_gammaedge(data):
    data["last_updated"] = datetime.now(timezone.utc).isoformat()
    data["total_games"]  = len(data.get("games",[]))
    GAMMAEDGE_FILE.write_text(json.dumps(data,ensure_ascii=False,indent=2),"utf-8")
    _rebuild_gammaedge()

def _rebuild_gammaedge():
    try:
        import importlib.util
        spec=importlib.util.spec_from_file_location("build",BUILD_PY)
        mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        mod.build_gammaedge()
    except Exception as e: print(f"⚠  GammaEdge rebuild: {e}")

def save_intelligence(data):
    data["last_updated"]     = datetime.now(timezone.utc).isoformat()
    data["total_datapoints"] = sum(len(p.get("datapoints",[])) for p in data.get("periods",[]))
    INTEL_FILE.write_text(json.dumps(data,ensure_ascii=False,indent=2),"utf-8")
    _rebuild_intelligence()

def _rebuild_intelligence():
    try:
        import importlib.util
        spec=importlib.util.spec_from_file_location("build",BUILD_PY)
        mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        mod.build_intelligence()
    except Exception as e: print(f"⚠  Intelligence rebuild: {e}")

def polls_with_counts():
    polls = load(POLLS_FILE,{"polls":[]})["polls"]
    votes = load(VOTES_FILE,{"votes":[]})["votes"]
    result=[]
    for p in polls:
        pid=p["id"]
        pv=[v for v in votes if v["poll_id"]==pid]
        counts={o:0 for o in p["options"]}
        for v in pv: counts[v.get("option","")] = counts.get(v.get("option",""),0)+1
        result.append({**p,"vote_counts":counts,"total_votes":len(pv)})
    return result


# ════════════════════════════════════════════════════════════════════════════════
# ADMIN HTML
# ════════════════════════════════════════════════════════════════════════════════
ADMIN_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>FitOut Post Admin</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --black:#1a1a1a;--claret:#990033;--claret-lt:#CC0044;--teal:#0D7680;
  --salmon:#FFF1E5;--border:#D9CBC0;--bg:#f4ede6;--card:#fff;
  --warm-gray:#66605A;--mid-gray:#9A948E;
  --serif:'Georgia',serif;--sans:'Inter','Segoe UI',sans-serif;
}
body{font-family:var(--sans);background:var(--bg);color:var(--black);display:flex;min-height:100vh}
a{color:inherit;text-decoration:none}

/* ─── Sidebar */
#sidebar{width:220px;background:var(--black);color:#fff;flex-shrink:0;
         display:flex;flex-direction:column;position:sticky;top:0;height:100vh;overflow-y:auto}
#sb-brand{padding:24px 20px 20px;border-bottom:1px solid rgba(255,255,255,.1)}
#sb-brand h1{font-family:var(--serif);font-size:16px;font-weight:700;
              color:#fff;line-height:1.3}
#sb-brand small{font-size:10px;color:rgba(255,255,255,.4);letter-spacing:.8px;text-transform:uppercase}
#sb-nav{padding:16px 0;flex:1}
.sb-item{display:flex;align-items:center;gap:12px;padding:12px 20px;
          font-size:13px;color:rgba(255,255,255,.6);cursor:pointer;
          transition:background .15s,color .15s;border-left:3px solid transparent}
.sb-item:hover{background:rgba(255,255,255,.07);color:#fff}
.sb-item.active{background:rgba(255,255,255,.1);color:#fff;border-left-color:var(--claret)}
.sb-item .sb-icon{font-size:18px;width:22px;text-align:center;flex-shrink:0}
.sb-item .sb-label{flex:1}
.sb-item .sb-count{font-size:10px;background:var(--claret);color:#fff;
                    padding:2px 6px;border-radius:10px}
#sb-footer{padding:16px 20px;border-top:1px solid rgba(255,255,255,.1);
            font-size:11px;color:rgba(255,255,255,.3)}
#sb-footer a{color:rgba(255,255,255,.4)}
#sb-footer a:hover{color:#fff}

/* ─── Main panel */
#main{flex:1;display:flex;flex-direction:column;min-width:0}
.panel-header{background:var(--card);border-bottom:1px solid var(--border);
               padding:20px 32px;display:flex;align-items:center;justify-content:space-between}
.panel-header h2{font-family:var(--serif);font-size:22px}
.panel-header .ph-sub{font-size:12px;color:var(--warm-gray);margin-top:3px}
.panel-body{padding:32px;max-width:900px}

/* ─── Cards */
.card{background:var(--card);border:1px solid var(--border);padding:24px 28px;margin-bottom:16px}
.card-header{display:flex;align-items:flex-start;justify-content:space-between;
              margin-bottom:14px;padding-bottom:14px;border-bottom:1px solid var(--border)}
.card-title{font-family:var(--serif);font-size:17px;font-weight:700;line-height:1.35;flex:1}
.card-meta{font-size:11px;color:var(--warm-gray);margin-top:4px;display:flex;gap:12px}
.card-source{font-weight:700;color:var(--claret);font-size:11.5px;text-transform:uppercase}
.card-body{font-size:13.5px;color:var(--warm-gray);line-height:1.65;margin-bottom:12px}
.card-note{font-size:13px;color:var(--black);font-style:italic;
            border-left:3px solid var(--claret);padding-left:10px;margin:8px 0}
.card-actions{display:flex;gap:10px;align-items:center;margin-top:14px}

/* ─── Buttons */
.btn{padding:9px 20px;font-size:13px;font-weight:600;cursor:pointer;border:none;
      font-family:var(--sans);transition:background .15s,opacity .15s;white-space:nowrap}
.btn:disabled{opacity:.4;cursor:default}
.btn-primary{background:var(--black);color:#fff}.btn-primary:hover:not(:disabled){background:#333}
.btn-claret{background:var(--claret);color:#fff}.btn-claret:hover:not(:disabled){background:var(--claret-lt)}
.btn-outline{background:transparent;color:var(--black);border:1px solid var(--border)}
.btn-outline:hover:not(:disabled){border-color:var(--black)}
.btn-sm{padding:5px 12px;font-size:12px}
.btn-danger{background:transparent;color:#cc2200;border:1px solid #cc2200}
.btn-danger:hover{background:#cc2200;color:#fff}

/* ─── Form */
.form-section{background:var(--card);border:1px solid var(--border);
               padding:24px 28px;margin-bottom:24px}
.form-section h3{font-family:var(--serif);font-size:18px;margin-bottom:18px;
                  padding-bottom:12px;border-bottom:2px solid var(--black)}
.field{margin-bottom:16px}
.field label{display:block;font-size:11px;font-weight:600;letter-spacing:.8px;
              text-transform:uppercase;color:var(--warm-gray);margin-bottom:6px}
.field input,.field textarea,.field select{
  width:100%;padding:9px 12px;font-size:14px;border:1px solid var(--border);
  outline:none;font-family:var(--sans);transition:border-color .15s;background:#fff}
.field input:focus,.field textarea:focus,.field select:focus{border-color:var(--black)}
.field textarea{resize:vertical}
.field-row{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.field-row-3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px}

/* ─── Status */
.status{font-size:13px;padding:10px 16px;display:none;margin-top:10px}
.status.ok{background:#d4edda;color:#155724}
.status.err{background:#f8d7da;color:#721c24}
.status.info{background:#e8f4fd;color:#0c5460}

/* ─── Poll cards */
.poll-card{background:var(--card);border:1px solid var(--border);
            padding:22px 26px;margin-bottom:16px}
.poll-q{font-family:var(--serif);font-size:18px;font-weight:700;
         margin-bottom:14px;line-height:1.35}
.poll-option{margin-bottom:10px}
.poll-option-label{display:flex;justify-content:space-between;align-items:center;
                    font-size:13px;margin-bottom:4px}
.poll-option-name{font-weight:500}
.poll-option-pct{font-weight:700;color:var(--claret);font-size:14px}
.poll-bar-track{height:8px;background:#eee;border-radius:4px;overflow:hidden}
.poll-bar-fill{height:100%;background:var(--claret);transition:width .3s;border-radius:4px}
.poll-meta{display:flex;gap:16px;font-size:11px;color:var(--mid-gray);
            margin-top:14px;padding-top:12px;border-top:1px solid var(--border)}
.poll-status-badge{padding:2px 10px;font-size:10px;font-weight:700;
                    letter-spacing:.5px;text-transform:uppercase}
.badge-active{background:#d4edda;color:#155724}
.badge-closed{background:#f8d7da;color:#721c24}
.badge-draft{background:#fff3cd;color:#856404}

.opt-input-row{display:flex;gap:8px;margin-bottom:8px;align-items:center}
.opt-input-row input{flex:1}
.opt-rm{background:none;border:none;cursor:pointer;color:#cc2200;font-size:18px;line-height:1}

.empty-state{text-align:center;padding:60px;color:var(--warm-gray);
              font-family:var(--serif);font-size:17px;font-style:italic;
              background:var(--card);border:1px dashed var(--border)}
.view-voters-link{font-size:12px;color:var(--claret);cursor:pointer;text-decoration:underline}

/* ─── Voter modal */
.modal-backdrop{display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:1000;
                 align-items:center;justify-content:center}
.modal-backdrop.open{display:flex}
.modal{background:#fff;border:1px solid var(--border);padding:28px 32px;
        max-width:600px;width:90%;max-height:80vh;overflow-y:auto}
.modal h3{font-family:var(--serif);font-size:20px;margin-bottom:18px}
.voter-table{width:100%;border-collapse:collapse;font-size:12.5px}
.voter-table th{text-align:left;padding:8px 10px;border-bottom:2px solid var(--border);
                 font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:var(--warm-gray)}
.voter-table td{padding:8px 10px;border-bottom:1px solid var(--border)}
.voter-option{font-weight:700;color:var(--claret)}
</style>
</head>
<body>

<!-- ─── Sidebar -->
<nav id="sidebar">
  <div id="sb-brand">
    <h1>FitOut Post<br>Admin</h1>
    <small>Editorial dashboard</small>
  </div>
  <div id="sb-nav">
    <div class="sb-item active" data-tab="alpha" onclick="switchTab('alpha')">
      <span class="sb-icon">α</span>
      <span class="sb-label">αEdge</span>
      <span class="sb-count" id="alpha-count">0</span>
    </div>
    <div class="sb-item" data-tab="beta" onclick="switchTab('beta')">
      <span class="sb-icon">β</span>
      <span class="sb-label">βEdge</span>
      <span class="sb-count" id="beta-count">0</span>
    </div>
    <div class="sb-item" data-tab="gamma" onclick="switchTab('gamma')">
      <span class="sb-icon">γ</span>
      <span class="sb-label">γEdge</span>
      <span class="sb-count" id="gamma-count">0</span>
    </div>
    <div class="sb-item" data-tab="intelligence" onclick="switchTab('intelligence')">
      <span class="sb-icon">⬡</span>
      <span class="sb-label">Intel</span>
      <span class="sb-count" id="intel-count">0</span>
    </div>
    <div class="sb-item" data-tab="members" onclick="switchTab('members')">
      <span class="sb-icon">👤</span>
      <span class="sb-label">Members</span>
      <span class="sb-count" id="members-count">0</span>
    </div>
  </div>
  <div id="sb-footer">
    <a href="/betaedge-preview" target="_blank">βEdge public ↗</a><br>
    <a href="../alphaedge.html" target="_blank">αEdge public ↗</a><br>
    <a href="../gammaedge.html" target="_blank">γEdge public ↗</a><br>
    <a href="../intelligence.html" target="_blank">Intelligence ↗</a><br>
    <a href="../register.html" target="_blank">Register ↗</a><br>
    <a href="../index.html" target="_blank">Main site ↗</a>
  </div>
</nav>

<!-- ─── Main content -->
<div id="main">

  <!-- ════ αEDGE PANEL ════ -->
  <div id="tab-alpha">
    <div class="panel-header">
      <div>
        <h2>α Edge — Curated Reading</h2>
        <div class="ph-sub">Add articles to AlphaEdge. Paste a URL — metadata is fetched automatically.</div>
      </div>
      <div style="display:flex;gap:10px">
        <a href="../alphaedge.html" target="_blank" class="btn btn-outline btn-sm">View public page ↗</a>
      </div>
    </div>
    <div class="panel-body">
      <!-- Add form -->
      <div class="form-section">
        <h3>Add article</h3>
        <div class="field">
          <label>Article URL</label>
          <div style="display:flex;gap:10px">
            <input type="url" id="alpha-url" placeholder="https://ft.com/…"
                   onkeydown="if(event.key==='Enter')fetchAlpha()">
            <button class="btn btn-primary" id="alpha-fetch-btn" onclick="fetchAlpha()">Fetch</button>
          </div>
        </div>
        <div id="alpha-status" class="status"></div>
        <div id="alpha-preview" style="display:none">
          <div class="field"><label>Title</label><input type="text" id="af-title"></div>
          <div class="field"><label>Summary</label><textarea id="af-summary" rows="4"></textarea></div>
          <div class="field"><label>Your take — curator's note (optional)</label>
            <textarea id="af-note" rows="3" placeholder="Why this matters for the fit-out industry…"></textarea></div>
          <div class="field-row">
            <div class="field"><label>Published</label><input type="text" id="af-pub"></div>
            <div class="field"><label>Source</label><input type="text" id="af-source"></div>
          </div>
          <div class="field"><label>Tags (comma-separated)</label><input type="text" id="af-tags"></div>
          <div style="display:flex;gap:10px;margin-top:20px">
            <button class="btn btn-claret" onclick="publishAlpha()">Publish to αEdge</button>
            <button class="btn btn-outline" onclick="cancelAlpha()">Cancel</button>
          </div>
        </div>
      </div>
      <!-- Article list -->
      <div id="alpha-list"></div>
    </div>
  </div>

  <!-- ════ βEDGE PANEL ════ -->
  <div id="tab-beta" style="display:none">
    <div class="panel-header">
      <div>
        <h2>β Edge — Polling Platform</h2>
        <div class="ph-sub">Create polls. People register on the public page to vote. Results are live.</div>
      </div>
      <div style="display:flex;gap:10px">
        <a href="/betaedge-preview" target="_blank" class="btn btn-outline btn-sm">View public page ↗</a>
      </div>
    </div>
    <div class="panel-body">
      <!-- Create poll form -->
      <div class="form-section">
        <h3>Create poll</h3>
        <div class="field"><label>Question</label>
          <input type="text" id="poll-q"
                 placeholder="Which region will see the most fit-out growth in 2026?"></div>
        <div class="field"><label>Category (optional)</label>
          <input type="text" id="poll-cat" placeholder="Market, Costs, Companies, Trends…"></div>
        <div class="field-row">
          <div class="field"><label>Closes on (optional)</label>
            <input type="date" id="poll-closes"></div>
          <div class="field"><label>Status</label>
            <select id="poll-status">
              <option value="active">Active — open for votes</option>
              <option value="draft">Draft — hidden from public</option>
            </select>
          </div>
        </div>
        <div class="field">
          <label>Options (min 2, max 8)</label>
          <div id="poll-options-list">
            <div class="opt-input-row"><input type="text" placeholder="Option 1" class="opt-inp">
              <button class="opt-rm" onclick="rmOpt(this)" title="Remove">×</button></div>
            <div class="opt-input-row"><input type="text" placeholder="Option 2" class="opt-inp">
              <button class="opt-rm" onclick="rmOpt(this)" title="Remove">×</button></div>
          </div>
          <button class="btn btn-outline btn-sm" style="margin-top:8px" onclick="addOpt()">+ Add option</button>
        </div>
        <div id="beta-status" class="status"></div>
        <div style="display:flex;gap:10px;margin-top:20px">
          <button class="btn btn-claret" onclick="createPoll()">Create poll</button>
          <button class="btn btn-outline" onclick="resetPollForm()">Reset</button>
        </div>
      </div>
      <!-- Poll list -->
      <div id="beta-list"></div>
    </div>
  </div>

  <!-- ════ γEDGE PANEL ════ -->
  <div id="tab-gamma" style="display:none">
    <div class="panel-header">
      <div>
        <h2>γ Edge — Games with an edge</h2>
        <div class="ph-sub">Curate links to web games and puzzles. Each entry opens an external site in a new tab.</div>
      </div>
      <div style="display:flex;gap:10px">
        <a href="../gammaedge.html" target="_blank" class="btn btn-outline btn-sm">View public page ↗</a>
      </div>
    </div>
    <div class="panel-body">
      <!-- Add game link form -->
      <div class="form-section">
        <h3>Add game link</h3>
        <div class="field"><label>URL *</label>
          <input type="url" id="gamma-url" placeholder="https://www.nytimes.com/games/wordle/index.html"></div>
        <div class="field"><label>Title *</label>
          <input type="text" id="gamma-title" placeholder="Wordle"></div>
        <div class="field"><label>Description</label>
          <input type="text" id="gamma-desc" placeholder="Brief description of the game and why it's worth playing"></div>
        <div class="field-row">
          <div class="field"><label>Game type</label>
            <select id="gamma-type">
              <option value="Word">Word</option>
              <option value="Puzzle">Puzzle</option>
              <option value="Geography">Geography</option>
              <option value="Visual">Visual</option>
              <option value="Trivia">Trivia</option>
              <option value="Strategy">Strategy</option>
              <option value="Other">Other</option>
            </select>
          </div>
          <div class="field"><label>Source (site name)</label>
            <input type="text" id="gamma-source" placeholder="New York Times"></div>
        </div>
        <div class="field"><label>Tags (comma-separated)</label>
          <input type="text" id="gamma-tags" placeholder="daily, word, 5 minutes"></div>
        <div id="gamma-game-status" class="status"></div>
        <div style="display:flex;gap:10px;margin-top:20px">
          <button class="btn btn-claret" onclick="addGameLink()">Add game</button>
          <button class="btn btn-outline" onclick="resetGameForm()">Reset</button>
        </div>
      </div>
      <!-- Game list -->
      <div id="gamma-list"></div>
    </div>
  </div>

  <!-- ════ INTELLIGENCE PANEL ════ -->
  <div id="tab-intelligence" style="display:none">
    <div class="panel-header">
      <div>
        <h2>Intelligence — Fit-Out Cost Data</h2>
        <div class="ph-sub">Add $/m² cost datapoints from published industry reports. Auto-fetch reads known report URLs.</div>
      </div>
      <div style="display:flex;gap:8px;align-items:center">
        <button class="btn btn-outline btn-sm" onclick="runIntelFetch()" id="intel-fetch-btn">Auto-fetch reports</button>
        <a href="../intelligence.html" target="_blank" class="btn btn-outline btn-sm">View public page ↗</a>
      </div>
    </div>
    <div class="panel-body">
      <div id="intel-fetch-status" class="status"></div>

      <!-- Add datapoint form -->
      <details style="margin-bottom:24px;border:1px solid var(--border);border-radius:4px">
        <summary style="padding:12px 16px;cursor:pointer;font-weight:600;font-family:var(--mono);font-size:13px;background:var(--bg)">
          + Add datapoint manually
        </summary>
        <div style="padding:16px">
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
            <div class="field"><label>Continent *</label>
              <select id="intel-continent">
                <option value="">— select —</option>
                <option>Europe</option><option>Middle East</option>
                <option>Asia Pacific</option><option>Americas</option>
                <option>Africa</option><option>Oceania</option><option>Global</option>
              </select>
            </div>
            <div class="field"><label>Country *</label>
              <input id="intel-country" type="text" placeholder="e.g. United Kingdom"></div>
            <div class="field"><label>City</label>
              <input id="intel-city" type="text" placeholder="e.g. London"></div>
            <div class="field"><label>Fit-out type *</label>
              <select id="intel-type">
                <option>Office Cat A</option><option selected>Office Cat B</option>
                <option>Retail</option><option>Hotel / Hospitality</option>
                <option>Healthcare</option><option>Industrial / Warehouse</option>
                <option>Data Centre</option><option>Residential</option>
                <option>Mixed / Other</option>
              </select>
            </div>
            <div class="field"><label>Cost low (original currency)</label>
              <input id="intel-cost-low" type="number" placeholder="1500"></div>
            <div class="field"><label>Cost high (original currency)</label>
              <input id="intel-cost-high" type="number" placeholder="2500"></div>
            <div class="field"><label>Currency</label>
              <select id="intel-currency">
                <option>USD</option><option>GBP</option><option>EUR</option>
                <option>AED</option><option>SAR</option><option>QAR</option>
                <option>SGD</option><option>AUD</option><option>HKD</option>
                <option>CAD</option><option>INR</option><option>BRL</option>
                <option>ZAR</option><option>CHF</option><option>NZD</option>
              </select>
            </div>
            <div class="field"><label>USD/m² (auto-calculated)</label>
              <input id="intel-cost-usd" type="text" readonly placeholder="calculated on save"></div>
            <div class="field"><label>Source (firm name) *</label>
              <input id="intel-source" type="text" placeholder="e.g. CBRE"></div>
            <div class="field" style="grid-column:span 2"><label>Report title</label>
              <input id="intel-report-title" type="text" placeholder="e.g. EMEA Fit-Out Cost Guide 2026"></div>
            <div class="field" style="grid-column:span 2"><label>Report URL</label>
              <input id="intel-report-url" type="url" placeholder="https://..."></div>
            <div class="field"><label>Date published</label>
              <input id="intel-date-pub" type="date"></div>
            <div class="field"><label>Period (YYYY-MM) *</label>
              <input id="intel-period" type="text" placeholder="2026-05" id="intel-period"></div>
          </div>
          <div class="field"><label>Summary / notes</label>
            <textarea id="intel-summary" rows="3" placeholder="One-sentence summary of what the report says about costs in this market…"></textarea>
          </div>
          <div id="intel-add-status" class="status"></div>
          <button class="btn btn-claret" onclick="addIntelDatapoint()">Add datapoint</button>
        </div>
      </details>

      <!-- Period filter -->
      <div style="display:flex;gap:8px;align-items:center;margin-bottom:12px">
        <label style="font-family:var(--mono);font-size:12px;letter-spacing:.05em">Period:</label>
        <select id="intel-period-filter" onchange="loadIntelList()" style="font-family:var(--mono);font-size:12px;padding:4px 8px;border:1px solid var(--border)">
          <option value="">All</option>
        </select>
        <span id="intel-count-label" style="font-family:var(--mono);font-size:11px;color:var(--warm-gray);margin-left:8px"></span>
      </div>

      <div id="intel-list"></div>
    </div>
  </div>

  <!-- ─── Members tab -->
  <div class="ph-panel" id="members-panel" style="display:none">
    <div class="ph-header">
      <h2>Members</h2>
      <div class="ph-actions">
        <button class="btn btn-outline btn-sm" onclick="exportMembersCSV()">Export CSV</button>
        <button class="btn btn-primary btn-sm" onclick="loadMembers()">Refresh</button>
      </div>
    </div>
    <div class="ph-sub">Registered members. Stored server-side in members.json when admin.py is running, and client-side in localStorage.</div>
    <div id="members-status" class="status"></div>
    <div id="members-list"></div>
  </div>

</div><!-- /main -->

<!-- ─── Add question modal -->
<div class="modal-backdrop" id="question-modal">
  <div class="modal" style="max-width:620px">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:18px">
      <h3 id="qmodal-title">Add question</h3>
      <button class="btn btn-outline btn-sm" onclick="closeQuestionModal()">Close</button>
    </div>
    <div class="field"><label>Question text *</label>
      <textarea id="q-text" rows="3" placeholder="What does CAT A fit-out typically include?"></textarea></div>
    <div class="field"><label>Options — mark the correct one</label>
      <div id="q-options-list">
        <div class="opt-input-row">
          <input type="radio" name="q-correct" value="0" style="flex-shrink:0;margin-top:2px" checked>
          <input type="text" placeholder="Option A" class="q-opt-inp">
        </div>
        <div class="opt-input-row">
          <input type="radio" name="q-correct" value="1" style="flex-shrink:0;margin-top:2px">
          <input type="text" placeholder="Option B" class="q-opt-inp">
        </div>
        <div class="opt-input-row">
          <input type="radio" name="q-correct" value="2" style="flex-shrink:0;margin-top:2px">
          <input type="text" placeholder="Option C" class="q-opt-inp">
        </div>
        <div class="opt-input-row">
          <input type="radio" name="q-correct" value="3" style="flex-shrink:0;margin-top:2px">
          <input type="text" placeholder="Option D" class="q-opt-inp">
        </div>
      </div>
    </div>
    <div class="field"><label>Explanation (shown after answer)</label>
      <textarea id="q-explanation" rows="2" placeholder="Brief explanation of why the correct answer is right…"></textarea></div>
    <div id="qmodal-status" class="status"></div>
    <div style="display:flex;gap:10px;margin-top:20px">
      <button class="btn btn-claret" id="qmodal-save-btn" onclick="saveQuestion()">Add question</button>
      <button class="btn btn-outline" onclick="closeQuestionModal()">Cancel</button>
    </div>
  </div>
</div>

<!-- ─── Voter detail modal -->
<div class="modal-backdrop" id="voter-modal">
  <div class="modal">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
      <h3 id="voter-modal-title">Voters</h3>
      <button class="btn btn-outline btn-sm" onclick="closeVoterModal()">Close</button>
    </div>
    <div id="voter-modal-body"></div>
  </div>
</div>

<script>
let alphaUrl="", alphaId="";
let currentTab="alpha";

// ══ TAB SWITCHING ════════════════════════════════════════════════════════════
function switchTab(t){
  currentTab=t;
  document.querySelectorAll(".sb-item").forEach(el=>el.classList.toggle("active",el.dataset.tab===t));
  document.getElementById("tab-alpha").style.display=t==="alpha"?"block":"none";
  document.getElementById("tab-beta").style.display=t==="beta"?"block":"none";
  document.getElementById("tab-gamma").style.display=t==="gamma"?"block":"none";
  document.getElementById("tab-intelligence").style.display=t==="intelligence"?"block":"none";
  const mp = document.getElementById("members-panel");
  if(mp) mp.style.display=t==="members"?"block":"none";
  if(t==="alpha") loadAlphaList();
  if(t==="beta") loadBetaList();
  if(t==="gamma") loadGammaList();
  if(t==="intelligence") loadIntelList();
  if(t==="members") loadMembers();
}

// ══ UTILS ════════════════════════════════════════════════════════════════════
function esc(s){return String(s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;")}
function fmtDate(iso){if(!iso)return"—";try{return new Date(iso).toLocaleDateString("en-GB",{day:"numeric",month:"short",year:"numeric"})}catch{return iso}}
function showStatus(id,msg,type){const el=document.getElementById(id);el.textContent=msg;el.className="status "+type;el.style.display="block"}
function hideStatus(id){document.getElementById(id).style.display="none"}

// ══ ALPHA EDGE ═══════════════════════════════════════════════════════════════
async function fetchAlpha(){
  const url=document.getElementById("alpha-url").value.trim();
  if(!url){showStatus("alpha-status","Please enter a URL.","err");return}
  document.getElementById("alpha-fetch-btn").disabled=true;
  showStatus("alpha-status","Fetching article…","info");
  document.getElementById("alpha-preview").style.display="none";
  try{
    const r=await fetch("/api/alpha/fetch",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({url})});
    const d=await r.json();if(!r.ok)throw new Error(d.error||"Fetch failed");
    alphaUrl=url; alphaId=d.id||"";
    document.getElementById("af-title").value=d.title||"";
    document.getElementById("af-summary").value=d.summary||"";
    document.getElementById("af-note").value="";
    document.getElementById("af-pub").value=d.published||"";
    document.getElementById("af-source").value=d.source||"";
    document.getElementById("af-tags").value="";
    document.getElementById("alpha-preview").style.display="block";
    hideStatus("alpha-status");
  }catch(e){showStatus("alpha-status","Error: "+e.message,"err")}
  finally{document.getElementById("alpha-fetch-btn").disabled=false}
}

async function publishAlpha(){
  const art={id:alphaId,url:alphaUrl,
    title:document.getElementById("af-title").value.trim(),
    summary:document.getElementById("af-summary").value.trim(),
    curator_note:document.getElementById("af-note").value.trim(),
    published:document.getElementById("af-pub").value.trim(),
    source:document.getElementById("af-source").value.trim(),
    tags:document.getElementById("af-tags").value.split(",").map(t=>t.trim()).filter(Boolean)};
  if(!art.title){showStatus("alpha-status","Title is required.","err");return}
  showStatus("alpha-status","Saving…","info");
  try{
    const r=await fetch("/api/alpha/save",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(art)});
    const d=await r.json();if(!r.ok)throw new Error(d.error||"Save failed");
    showStatus("alpha-status","✅ Published! αEdge page rebuilt.","ok");
    cancelAlpha(); loadAlphaList();
  }catch(e){showStatus("alpha-status","Error: "+e.message,"err")}
}

function cancelAlpha(){
  document.getElementById("alpha-preview").style.display="none";
  document.getElementById("alpha-url").value=""; alphaUrl=""; alphaId="";
}

async function deleteAlpha(id){
  if(!confirm("Remove this article from αEdge?"))return;
  await fetch("/api/alpha/delete",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({id})});
  loadAlphaList();
}

async function loadAlphaList(){
  const r=await fetch("/api/alpha/articles"); const d=await r.json();
  const arts=d.articles||[];
  document.getElementById("alpha-count").textContent=arts.length;
  const list=document.getElementById("alpha-list");
  if(!arts.length){list.innerHTML='<div class="empty-state">No articles yet. Paste a URL above.</div>';return}
  list.innerHTML=arts.slice().reverse().map(a=>`
<div class="card">
  <div class="card-header">
    <div>
      <div class="card-meta"><span class="card-source">${esc(a.source)}</span><span>${fmtDate(a.published)}</span></div>
      <div class="card-title"><a href="${esc(a.url)}" target="_blank">${esc(a.title)}</a></div>
    </div>
  </div>
  <div class="card-body">${esc(a.summary||"")}</div>
  ${a.curator_note?`<div class="card-note">${esc(a.curator_note)}</div>`:""}
  <div class="card-actions">
    <a href="${esc(a.url)}" target="_blank" class="btn btn-outline btn-sm">Read ↗</a>
    <button class="btn btn-danger btn-sm" onclick="deleteAlpha('${esc(a.id)}')">Delete</button>
  </div>
</div>`).join("");
}

// ══ BETA EDGE ════════════════════════════════════════════════════════════════
function addOpt(){
  const list=document.getElementById("poll-options-list");
  if(list.children.length>=8){alert("Maximum 8 options.");return}
  const n=list.children.length+1;
  const row=document.createElement("div");row.className="opt-input-row";
  row.innerHTML=`<input type="text" placeholder="Option ${n}" class="opt-inp">
    <button class="opt-rm" onclick="rmOpt(this)" title="Remove">×</button>`;
  list.appendChild(row);
}
function rmOpt(btn){
  const list=document.getElementById("poll-options-list");
  if(list.children.length<=2){alert("At least 2 options required.");return}
  btn.closest(".opt-input-row").remove();
}
function resetPollForm(){
  document.getElementById("poll-q").value="";
  document.getElementById("poll-cat").value="";
  document.getElementById("poll-closes").value="";
  document.getElementById("poll-status").value="active";
  const list=document.getElementById("poll-options-list");
  list.innerHTML=`
  <div class="opt-input-row"><input type="text" placeholder="Option 1" class="opt-inp">
    <button class="opt-rm" onclick="rmOpt(this)">×</button></div>
  <div class="opt-input-row"><input type="text" placeholder="Option 2" class="opt-inp">
    <button class="opt-rm" onclick="rmOpt(this)">×</button></div>`;
  hideStatus("beta-status");
}

async function createPoll(){
  const q=document.getElementById("poll-q").value.trim();
  if(!q){showStatus("beta-status","Question is required.","err");return}
  const opts=[...document.querySelectorAll(".opt-inp")].map(i=>i.value.trim()).filter(Boolean);
  if(opts.length<2){showStatus("beta-status","At least 2 options required.","err");return}
  const poll={
    question:q,
    category:document.getElementById("poll-cat").value.trim(),
    closes_at:document.getElementById("poll-closes").value||null,
    status:document.getElementById("poll-status").value,
    options:opts
  };
  showStatus("beta-status","Creating poll…","info");
  try{
    const r=await fetch("/api/beta/create",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(poll)});
    const d=await r.json();if(!r.ok)throw new Error(d.error||"Create failed");
    showStatus("beta-status","✅ Poll created! βEdge page rebuilt.","ok");
    resetPollForm(); loadBetaList();
  }catch(e){showStatus("beta-status","Error: "+e.message,"err")}
}

async function deletePoll(id){
  if(!confirm("Delete this poll and ALL its votes? This cannot be undone."))return;
  await fetch("/api/beta/delete",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({id})});
  loadBetaList();
}

async function togglePollStatus(id,newStatus){
  await fetch("/api/beta/update",{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({id,status:newStatus})});
  loadBetaList();
}

async function loadBetaList(){
  const r=await fetch("/api/polls"); const polls=await r.json();
  document.getElementById("beta-count").textContent=polls.filter(p=>p.status==="active").length;
  const list=document.getElementById("beta-list");
  if(!polls.length){list.innerHTML='<div class="empty-state">No polls yet. Create one above.</div>';return}
  list.innerHTML=polls.slice().reverse().map(p=>{
    const total=p.total_votes||0;
    const opts=p.options.map(o=>{
      const c=p.vote_counts[o]||0;
      const pct=total?Math.round(c/total*100):0;
      return `<div class="poll-option">
        <div class="poll-option-label">
          <span class="poll-option-name">${esc(o)}</span>
          <span class="poll-option-pct">${pct}% <small style="font-weight:400;color:#999">(${c})</small></span>
        </div>
        <div class="poll-bar-track"><div class="poll-bar-fill" style="width:${pct}%"></div></div>
      </div>`;
    }).join("");
    const badgeClass=p.status==="active"?"badge-active":p.status==="draft"?"badge-draft":"badge-closed";
    const toggleLabel=p.status==="active"?"Close poll":"Reopen";
    const toggleStatus=p.status==="active"?"closed":"active";
    return `<div class="poll-card">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px">
        <div class="poll-q">${esc(p.question)}</div>
        <span class="poll-status-badge ${badgeClass}">${p.status}</span>
      </div>
      ${p.category?`<div style="font-size:11px;color:var(--claret);font-weight:600;text-transform:uppercase;letter-spacing:.5px;margin-bottom:10px">${esc(p.category)}</div>`:""}
      ${opts}
      <div class="poll-meta">
        <span>${total} vote${total!==1?"s":""}</span>
        ${p.closes_at?`<span>Closes ${fmtDate(p.closes_at)}</span>`:""}
        ${p.created_at?`<span>Created ${fmtDate(p.created_at)}</span>`:""}
        <span class="view-voters-link" onclick="viewVoters('${esc(p.id)}','${esc(p.question)}')">View voters →</span>
      </div>
      <div class="card-actions" style="margin-top:12px;padding-top:12px;border-top:1px solid var(--border)">
        <button class="btn btn-outline btn-sm" onclick="togglePollStatus('${esc(p.id)}','${toggleStatus}')">${toggleLabel}</button>
        <button class="btn btn-danger btn-sm" onclick="deletePoll('${esc(p.id)}')">Delete</button>
      </div>
    </div>`;
  }).join("");
}

async function viewVoters(pollId,question){
  document.getElementById("voter-modal-title").textContent="Voters — "+question;
  document.getElementById("voter-modal-body").innerHTML="<p>Loading…</p>";
  document.getElementById("voter-modal").classList.add("open");
  try{
    const r=await fetch("/api/votes/"+pollId); const votes=await r.json();
    if(!votes.length){document.getElementById("voter-modal-body").innerHTML="<p style='color:#888'>No votes yet.</p>";return}
    const rows=votes.map(v=>`<tr>
      <td>${esc(v.voter?.name||"")}</td><td>${esc(v.voter?.org||"")}</td>
      <td>${esc(v.voter?.email||"")}</td>
      <td class="voter-option">${esc(v.option||"")}</td>
      <td>${fmtDate(v.voted_at)}</td>
    </tr>`).join("");
    document.getElementById("voter-modal-body").innerHTML=`
      <table class="voter-table">
        <thead><tr><th>Name</th><th>Organisation</th><th>Email</th><th>Vote</th><th>Date</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>`;
  }catch(e){document.getElementById("voter-modal-body").innerHTML="<p>Error loading voters.</p>"}
}
function closeVoterModal(){document.getElementById("voter-modal").classList.remove("open")}

// ══ GAMMA EDGE ═══════════════════════════════════════════════════════════════
let activeGameId="";

function resetGameForm(){
  document.getElementById("gamma-url").value="";
  document.getElementById("gamma-title").value="";
  document.getElementById("gamma-desc").value="";
  document.getElementById("gamma-type").value="Word";
  document.getElementById("gamma-source").value="";
  document.getElementById("gamma-tags").value="";
  hideStatus("gamma-game-status");
}

async function addGameLink(){
  const url=document.getElementById("gamma-url").value.trim();
  const title=document.getElementById("gamma-title").value.trim();
  if(!url){showStatus("gamma-game-status","URL is required.","err");return}
  if(!title){showStatus("gamma-game-status","Title is required.","err");return}
  const rawTags=document.getElementById("gamma-tags").value;
  const tags=rawTags.split(",").map(t=>t.trim()).filter(Boolean);
  const game={
    url,title,
    description:document.getElementById("gamma-desc").value.trim(),
    game_type:document.getElementById("gamma-type").value,
    source:document.getElementById("gamma-source").value.trim(),
    tags
  };
  showStatus("gamma-game-status","Saving…","info");
  try{
    const r=await fetch("/api/gamma/add",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(game)});
    const d=await r.json();if(!r.ok)throw new Error(d.error||"Save failed");
    showStatus("gamma-game-status","✅ Game link added.","ok");
    resetGameForm(); loadGammaList();
  }catch(e){showStatus("gamma-game-status","Error: "+e.message,"err")}
}

async function deleteGameLink(id){
  if(!confirm("Remove this game link?"))return;
  await fetch("/api/gamma/delete",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({id})});
  loadGammaList();
}

async function loadGammaList(){
  const r=await fetch("/api/gamma/games"); const d=await r.json();
  const games=d.games||[];
  document.getElementById("gamma-count").textContent=games.length;
  const list=document.getElementById("gamma-list");
  if(!games.length){list.innerHTML='<div class="empty-state">No games yet. Add one above.</div>';return}
  list.innerHTML=games.slice().reverse().map(g=>`
    <div class="poll-card">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px">
        <div style="flex:1;min-width:0">
          <div class="poll-q"><a href="${esc(g.url)}" target="_blank" rel="noopener"
               style="color:inherit;text-decoration:none">${esc(g.title)} ↗</a></div>
          ${g.game_type?`<div style="font-size:11px;color:var(--claret);font-weight:600;text-transform:uppercase;letter-spacing:.5px;margin-top:2px">${esc(g.game_type)}</div>`:""}
          ${g.description?`<div style="font-size:13px;color:var(--warm-gray);margin-top:4px">${esc(g.description)}</div>`:""}
          <div style="font-size:11px;color:var(--mid-gray);margin-top:4px">${esc(g.url)}</div>
          ${(g.tags||[]).length?`<div style="margin-top:6px;display:flex;gap:4px;flex-wrap:wrap">${g.tags.map(t=>`<span style="font-size:10px;padding:2px 6px;background:var(--bg-alt,#f5f0eb);border:1px solid var(--border)">${esc(t)}</span>`).join("")}</div>`:""}
        </div>
      </div>
      <div class="card-actions" style="margin-top:10px;padding-top:10px;border-top:1px solid var(--border)">
        <button class="btn btn-danger btn-sm" onclick="deleteGameLink('${esc(g.id)}')">Remove</button>
      </div>
    </div>`).join("");
}

// ── Stub kept for modal HTML compatibility (modal removed but saveQuestion ref may exist)
async function saveQuestion(){
  const text=document.getElementById("q-text")?document.getElementById("q-text").value.trim():"";
  if(!text) return;
  const correctRadio=document.querySelector("input[name=q-correct]:checked");
  const correct=correctRadio?parseInt(correctRadio.value):0;
  if(!options[correct]){showStatus("qmodal-status","The marked correct option has no text.","err");return}
  const q={text,options,correct,explanation:document.getElementById("q-explanation").value.trim()};
  document.getElementById("qmodal-save-btn").disabled=true;
  showStatus("qmodal-status","Saving…","info");
  try{
    const r=await fetch("/api/gamma/question/add",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({game_id:activeGameId,question:q})});
    const d=await r.json();if(!r.ok)throw new Error(d.error||"Save failed");
    showStatus("qmodal-status","✅ Question added! γEdge page rebuilt.","ok");
    setTimeout(()=>{closeQuestionModal();loadGammaList()},900);
  }catch(e){showStatus("qmodal-status","Error: "+e.message,"err")}
  finally{document.getElementById("qmodal-save-btn").disabled=false}
}

async function deleteQuestion(gameId,questionId){
  if(!confirm("Remove this question?"))return;
  await fetch("/api/gamma/question/delete",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({game_id:gameId,question_id:questionId})});
  loadGammaList();
}

// ══ INTELLIGENCE ═════════════════════════════════════════════════════════════

// FX rates mirror fetch_intelligence.py
const FX = {USD:1,GBP:1.27,EUR:1.08,AED:0.272,SAR:0.267,QAR:0.274,KWD:3.25,
            BHD:2.65,OMR:2.60,SGD:0.74,AUD:0.65,CAD:0.74,HKD:0.128,JPY:0.0067,
            INR:0.012,BRL:0.19,ZAR:0.055,CNY:0.14,NZD:0.60,CHF:1.11};

function calcIntelUsd(){
  const low=parseFloat(document.getElementById('intel-cost-low').value)||0;
  const high=parseFloat(document.getElementById('intel-cost-high').value)||0;
  const cur=document.getElementById('intel-currency').value;
  const rate=FX[cur]||1;
  const mid=low&&high?(low+high)/2:low||high;
  document.getElementById('intel-cost-usd').value=
    mid?'$'+Math.round(mid*rate).toLocaleString()+'/m²':'';
}
document.getElementById('intel-cost-low').addEventListener('input',calcIntelUsd);
document.getElementById('intel-cost-high').addEventListener('input',calcIntelUsd);
document.getElementById('intel-currency').addEventListener('change',calcIntelUsd);

// Default period to current month
document.getElementById('intel-period').value=
  new Date().toISOString().slice(0,7);

async function addIntelDatapoint(){
  const continent=document.getElementById('intel-continent').value;
  const country=document.getElementById('intel-country').value.trim();
  const source=document.getElementById('intel-source').value.trim();
  const period=document.getElementById('intel-period').value.trim();
  if(!continent||!country||!source||!period){
    setStatus('intel-add-status','Continent, country, source and period are required','error');return;
  }
  const cur=document.getElementById('intel-currency').value;
  const rate=FX[cur]||1;
  const low=parseFloat(document.getElementById('intel-cost-low').value)||null;
  const high=parseFloat(document.getElementById('intel-cost-high').value)||null;
  const mid=low&&high?Math.round((low+high)/2):low||high;
  const dp={
    continent, country,
    city:document.getElementById('intel-city').value.trim(),
    fit_out_type:document.getElementById('intel-type').value,
    cost_usd_m2_low: low?Math.round(low*rate):null,
    cost_usd_m2_high:high?Math.round(high*rate):null,
    cost_usd_m2_mid: mid?Math.round(mid*rate):null,
    cost_original:   (low||'')+(high&&high!==low?'–'+high:'')+(low||high?' '+cur+'/m²':''),
    currency:cur, exchange_rate:rate,
    source,
    report_title:document.getElementById('intel-report-title').value.trim(),
    report_url:  document.getElementById('intel-report-url').value.trim(),
    date_published:document.getElementById('intel-date-pub').value,
    summary:     document.getElementById('intel-summary').value.trim(),
    auto_extracted:false, needs_review:false,
  };
  const btn=document.getElementById('intel-add-status').previousElementSibling;
  btn.disabled=true;
  const r=await fetch('/api/intelligence/add',{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({period,datapoint:dp})
  });
  btn.disabled=false;
  const d=await r.json();
  if(d.ok){
    setStatus('intel-add-status','Datapoint added ✓','ok');
    // reset form fields
    ['intel-city','intel-cost-low','intel-cost-high','intel-cost-usd',
     'intel-report-title','intel-report-url','intel-summary','intel-date-pub']
      .forEach(id=>{document.getElementById(id).value='';});
    document.getElementById('intel-country').value='';
    document.getElementById('intel-continent').value='';
    loadIntelList();
  } else {
    setStatus('intel-add-status', d.error||'Error','error');
  }
}

async function deleteIntelDP(period,dpId){
  if(!confirm('Delete this datapoint?')) return;
  await fetch('/api/intelligence/delete',{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({period,id:dpId})
  });
  loadIntelList();
}

async function approveIntelDP(period,dpId){
  await fetch('/api/intelligence/approve',{
    method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({period,id:dpId})
  });
  loadIntelList();
}

async function loadIntelList(){
  const r=await fetch('/api/intelligence/datapoints');
  const data=await r.json();
  const periods=data.periods||[];

  // Populate period filter
  const sel=document.getElementById('intel-period-filter');
  const cur=sel.value;
  sel.innerHTML='<option value="">All periods</option>';
  for(const p of [...periods].reverse()){
    const opt=document.createElement('option');
    opt.value=p.id; opt.textContent=p.label||p.id;
    if(p.id===cur) opt.selected=true;
    sel.appendChild(opt);
  }

  const filterPeriod=sel.value;
  let allDPs=[];
  for(const p of periods){
    if(filterPeriod && p.id!==filterPeriod) continue;
    for(const dp of p.datapoints||[]) allDPs.push({...dp, _period:p.id});
  }

  document.getElementById('intel-count').textContent=allDPs.length;
  document.getElementById('intel-count-label').textContent=allDPs.length+' datapoint'+(allDPs.length!==1?'s':'');

  const list=document.getElementById('intel-list');
  if(!allDPs.length){
    list.innerHTML='<div style="color:var(--warm-gray);font-family:var(--mono);font-size:12px;padding:20px 0">'+
      'No datapoints yet. Add one above or run Auto-fetch.</div>';
    return;
  }

  list.innerHTML=allDPs.map(dp=>`
    <div class="article-row" style="border-left:3px solid ${dp.needs_review?'#e67e22':'#27ae60'}">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px">
        <div>
          <div style="font-weight:600;font-size:13px">${esc(dp.city||dp.country||'?')}${dp.country&&dp.city?' · '+esc(dp.country):''}</div>
          <div style="font-family:var(--mono);font-size:11px;color:var(--warm-gray);margin:2px 0">
            ${esc(dp.continent||'')} · ${esc(dp.fit_out_type||'')} · ${esc(dp.source||'')}
          </div>
          <div style="font-size:13px;color:#1a1a1a;margin:4px 0">
            <strong>$${(dp.cost_usd_m2_low||0).toLocaleString()}${dp.cost_usd_m2_high&&dp.cost_usd_m2_high!==dp.cost_usd_m2_low?'–$'+dp.cost_usd_m2_high.toLocaleString():''}/m²</strong>
            ${dp.cost_original?'<span style="color:#888;font-size:11px"> ['+esc(dp.cost_original)+']</span>':''}
          </div>
          ${dp.summary?'<div style="font-size:12px;color:#555;margin-top:4px">'+esc(dp.summary)+'</div>':''}
          ${dp.report_url?'<div style="margin-top:4px"><a href="'+esc(dp.report_url)+'" target="_blank" style="font-size:11px;color:#c8a84b">'+esc(dp.report_title||dp.report_url)+' ↗</a></div>':''}
        </div>
        <div style="display:flex;flex-direction:column;gap:4px;flex-shrink:0">
          ${dp.needs_review?`<button class="btn btn-outline btn-sm" onclick="approveIntelDP('${dp._period}','${dp.id}')">Approve</button>`:''}
          <button class="btn btn-outline btn-sm" style="color:#c0392b" onclick="deleteIntelDP('${dp._period}','${dp.id}')">Delete</button>
        </div>
      </div>
      <div style="font-family:var(--mono);font-size:10px;color:#bbb;margin-top:6px">
        Period: ${dp._period} · Added: ${dp.date_added||'—'} · ${dp.needs_review?'⚠ Needs review':'✓ Approved'}
      </div>
    </div>
  `).join('');
}

async function runIntelFetch(){
  const btn=document.getElementById('intel-fetch-btn');
  btn.disabled=true; btn.textContent='Fetching…';
  setStatus('intel-fetch-status','Running fetch_intelligence.py — this may take a minute…','ok');
  const r=await fetch('/api/intelligence/fetch',{method:'POST'});
  const d=await r.json();
  btn.disabled=false; btn.textContent='Auto-fetch reports';
  if(d.ok){
    setStatus('intel-fetch-status',d.message||'Fetch complete','ok');
    loadIntelList();
  } else {
    setStatus('intel-fetch-status',d.error||'Fetch failed','error');
  }
}

// ══ MEMBERS ══════════════════════════════════════════════════════════════════
async function loadMembers(){
  showStatus('members-status','Loading members…','info');
  try {
    const r = await fetch('/api/members');
    const d = await r.json();
    const members = d.members || [];
    document.getElementById('members-count').textContent = members.length;
    const el = document.getElementById('members-list');
    if(!members.length){
      el.innerHTML='<p style="color:#9A8A80;font-size:13px;padding:20px 0;">No members registered yet. Members appear here once someone registers at <a href="../register.html" target="_blank">register.html</a>.</p>';
      showStatus('members-status','0 members','info'); return;
    }
    el.innerHTML = '<table style="width:100%;border-collapse:collapse;font-size:13px;">'
      + '<thead><tr style="border-bottom:2px solid #1a1a1a;">'
      + '<th style="text-align:left;padding:8px 10px;font-size:11px;letter-spacing:0.5px;text-transform:uppercase;">Name</th>'
      + '<th style="text-align:left;padding:8px 10px;font-size:11px;letter-spacing:0.5px;text-transform:uppercase;">Email</th>'
      + '<th style="text-align:left;padding:8px 10px;font-size:11px;letter-spacing:0.5px;text-transform:uppercase;">Company</th>'
      + '<th style="text-align:left;padding:8px 10px;font-size:11px;letter-spacing:0.5px;text-transform:uppercase;">Role</th>'
      + '<th style="text-align:left;padding:8px 10px;font-size:11px;letter-spacing:0.5px;text-transform:uppercase;">Region</th>'
      + '<th style="text-align:left;padding:8px 10px;font-size:11px;letter-spacing:0.5px;text-transform:uppercase;">Registered</th>'
      + '<th style="text-align:left;padding:8px 10px;font-size:11px;letter-spacing:0.5px;text-transform:uppercase;"></th>'
      + '</tr></thead><tbody>'
      + members.map(m => `<tr style="border-bottom:1px solid #EDE3DA;">
          <td style="padding:9px 10px;">${esc(m.firstName||'')} ${esc(m.lastName||'')}</td>
          <td style="padding:9px 10px;"><a href="mailto:${esc(m.email)}">${esc(m.email)}</a></td>
          <td style="padding:9px 10px;">${esc(m.company||'—')}</td>
          <td style="padding:9px 10px;">${esc(m.role||'—')}</td>
          <td style="padding:9px 10px;">${esc(m.region||'—')}</td>
          <td style="padding:9px 10px;">${fmtDate(m.registeredAt)}</td>
          <td style="padding:9px 10px;"><button class="btn btn-outline btn-sm" onclick="deleteMember('${esc(m.id||'')}')">Remove</button></td>
        </tr>`).join('')
      + '</tbody></table>';
    showStatus('members-status', members.length + ' member(s)','ok');
  } catch(e) {
    showStatus('members-status','Error loading members: '+e.message,'error');
  }
}

async function deleteMember(id){
  if(!confirm('Remove this member?')) return;
  try {
    await fetch('/api/members/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});
    loadMembers();
  } catch(e) { alert('Error: '+e.message); }
}

function exportMembersCSV(){
  window.open('/api/members/export.csv','_blank');
}

// Boot
loadAlphaList();
loadBetaList();
loadGammaList();
loadIntelList();
</script>
</body>
</html>
"""


# ════════════════════════════════════════════════════════════════════════════════
# BETAEDGE PUBLIC PAGE (served directly by server for live voting)
# ════════════════════════════════════════════════════════════════════════════════
BETAEDGE_PUBLIC_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>β Edge — FitOut Post Polling</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;0,800;1,700&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --black:#1a1a1a;--claret:#990033;--claret-lt:#CC0044;
  --salmon:#FFF1E5;--border:#D9CBC0;--bg:#FAF5F0;--card:#fff;
  --warm-gray:#66605A;--mid-gray:#9A948E;--border-lt:#EDE3DA;
  --serif:'Playfair Display',Georgia,serif;--sans:'Inter','Segoe UI',sans-serif;
}
body{font-family:var(--sans);background:var(--bg);color:var(--black);-webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}

/* utility bar */
#util{background:var(--black);color:rgba(255,255,255,.6);font-size:11.5px;padding:0 24px}
#util-inner{max-width:1320px;margin:0 auto;height:34px;display:flex;align-items:center;justify-content:space-between}
.util-link{color:rgba(255,255,255,.5);transition:color .15s}.util-link:hover{color:#fff}

/* masthead */
#masthead{background:var(--salmon);border-bottom:2px solid var(--black);
           position:sticky;top:0;z-index:200}
#mh-inner{max-width:1320px;margin:0 auto;padding:0 24px;height:72px;
           display:flex;align-items:center;gap:24px}
#fop-logo{display:flex;align-items:center;gap:14px;flex-shrink:0;cursor:default}
#fop-box{width:52px;height:52px;background:var(--black);display:flex;
          align-items:center;justify-content:center}
#fop-box span{font-family:var(--serif);font-weight:800;font-size:24px;color:#fff;line-height:1}
#fop-wm strong{font-family:var(--serif);font-weight:700;font-size:20px;color:var(--black)}
#fop-wm em{font-style:normal;font-size:10px;letter-spacing:1.4px;text-transform:uppercase;
            color:var(--warm-gray);font-weight:500;display:block;margin-top:2px}
#be-badge{font-family:var(--serif);font-style:italic;font-size:17px;
           font-weight:700;color:var(--claret);padding-left:16px;
           border-left:1px solid var(--border)}
#mh-right{margin-left:auto;flex-shrink:0}
.mh-cta{font-size:12.5px;font-weight:600;padding:6px 18px;
         background:var(--claret);color:#fff;border:1px solid var(--claret);
         transition:background .15s}
.mh-cta:hover{background:var(--claret-lt)}

/* product nav */
#pnav{background:var(--black);position:sticky;top:72px;z-index:195}
#pnav-inner{max-width:1320px;margin:0 auto;padding:0 24px;display:flex}
.pnav-link{display:inline-block;padding:0 20px;height:38px;line-height:38px;
            font-size:12.5px;font-weight:500;color:rgba(255,255,255,.65);
            border-right:1px solid rgba(255,255,255,.1);transition:color .15s,background .15s}
.pnav-link:first-child{border-left:1px solid rgba(255,255,255,.1)}
.pnav-link:hover{color:#fff;background:rgba(255,255,255,.08)}
.pnav-link.active{color:#fff;background:var(--claret);border-color:var(--claret)}

/* page header */
#be-header{background:var(--black);color:#fff;padding:40px 24px 32px}
#be-hdr-inner{max-width:1320px;margin:0 auto;display:grid;grid-template-columns:1fr auto;gap:32px;align-items:end}
#be-title{font-family:var(--serif);font-size:46px;font-weight:800;font-style:italic;line-height:1;letter-spacing:-1px}
#be-title .greek{color:var(--claret)}
#be-tagline{font-size:14px;color:rgba(255,255,255,.55);margin-top:8px;max-width:520px;line-height:1.6}
#be-meta{text-align:right;font-size:11px;color:rgba(255,255,255,.4);line-height:1.8}
#be-meta strong{color:rgba(255,255,255,.7);font-size:22px;display:block;font-family:var(--serif)}

/* content */
#content-area{max-width:1320px;margin:0 auto;padding:32px 24px 80px;
               display:grid;grid-template-columns:1fr 360px;gap:32px}
@media(max-width:900px){#content-area{grid-template-columns:1fr}}

/* poll cards */
#polls-col h3{font-family:var(--serif);font-size:13px;text-transform:uppercase;
               letter-spacing:1px;color:var(--warm-gray);margin-bottom:16px;
               padding-bottom:10px;border-bottom:1px solid var(--border)}
.poll-card{background:var(--card);border:1px solid var(--border);
            padding:26px 28px;margin-bottom:20px;transition:border-color .15s}
.poll-card:hover{border-color:var(--black)}
.poll-cat{font-size:10px;font-weight:700;letter-spacing:.8px;text-transform:uppercase;
           color:var(--claret);margin-bottom:8px}
.poll-q{font-family:var(--serif);font-size:20px;font-weight:700;
         line-height:1.35;margin-bottom:18px}
.poll-option{margin-bottom:12px;cursor:pointer}
.poll-option-label{display:flex;justify-content:space-between;
                    align-items:center;font-size:13.5px;margin-bottom:5px}
.poll-option-name{font-weight:500}
.poll-option-pct{font-weight:700;font-size:15px;color:var(--claret)}
.poll-bar-track{height:10px;background:#eee;border-radius:5px;overflow:hidden}
.poll-bar-fill{height:100%;background:var(--claret);transition:width .5s;border-radius:5px}
.poll-footer{display:flex;justify-content:space-between;align-items:center;
              margin-top:18px;padding-top:14px;border-top:1px solid var(--border-lt)}
.poll-votes{font-size:12px;color:var(--mid-gray)}
.poll-deadline{font-size:12px;color:var(--mid-gray)}
.btn-vote{padding:9px 22px;background:var(--claret);color:#fff;border:none;
           font-size:13px;font-weight:600;cursor:pointer;font-family:var(--sans);
           transition:background .15s}
.btn-vote:hover{background:var(--claret-lt)}
.voted-badge{font-size:12px;font-weight:600;color:#155724;background:#d4edda;padding:6px 12px}
.closed-badge{font-size:12px;color:var(--mid-gray);padding:6px 12px;background:#eee}

/* side panel */
#side-col h3{font-family:var(--serif);font-size:13px;text-transform:uppercase;
              letter-spacing:1px;color:var(--warm-gray);margin-bottom:16px;
              padding-bottom:10px;border-bottom:1px solid var(--border)}
.how-it-works{background:var(--card);border:1px solid var(--border);padding:22px 24px;margin-bottom:20px}
.how-step{display:flex;gap:14px;margin-bottom:16px;align-items:flex-start}
.step-num{width:28px;height:28px;background:var(--black);color:#fff;
           font-size:12px;font-weight:700;display:flex;align-items:center;
           justify-content:center;flex-shrink:0;border-radius:50%}
.step-text{font-size:13px;line-height:1.55;color:var(--warm-gray)}
.step-text strong{color:var(--black)}
.disclaimer{background:var(--salmon);border:1px solid var(--border);padding:18px 22px;
             font-size:12px;color:var(--warm-gray);line-height:1.65}
.disclaimer strong{color:var(--black)}

/* modal */
.modal-backdrop{display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);
                 z-index:1000;align-items:center;justify-content:center}
.modal-backdrop.open{display:flex}
.modal{background:#fff;border:1px solid var(--border);padding:32px 36px;
        max-width:480px;width:90%;max-height:90vh;overflow-y:auto}
.modal h2{font-family:var(--serif);font-size:22px;margin-bottom:6px}
.modal .m-sub{font-size:13px;color:var(--warm-gray);margin-bottom:24px;line-height:1.5}
.mfield{margin-bottom:16px}
.mfield label{display:block;font-size:11px;font-weight:600;letter-spacing:.8px;
               text-transform:uppercase;color:var(--warm-gray);margin-bottom:5px}
.mfield input,.mfield select{width:100%;padding:10px 12px;font-size:14px;
  border:1px solid var(--border);outline:none;font-family:var(--sans);
  transition:border-color .15s}
.mfield input:focus{border-color:var(--black)}
.mfield-check{display:flex;gap:10px;align-items:flex-start;margin-top:4px}
.mfield-check input[type=checkbox]{width:16px;height:16px;flex-shrink:0;margin-top:2px;cursor:pointer}
.mfield-check label{font-size:12.5px;color:var(--warm-gray);line-height:1.5;
                      font-weight:400;text-transform:none;letter-spacing:0}
.m-selected-option{background:var(--salmon);border:1px solid var(--border);
                    padding:12px 16px;margin-bottom:20px;font-size:14px}
.m-selected-option strong{display:block;font-size:11px;text-transform:uppercase;
                            letter-spacing:.5px;color:var(--claret);margin-bottom:4px}
.m-status{font-size:13px;padding:10px 14px;margin-top:12px;display:none}
.m-status.ok{background:#d4edda;color:#155724}
.m-status.err{background:#f8d7da;color:#721c24}
.modal-actions{display:flex;gap:12px;margin-top:24px}
.mbtn{padding:11px 24px;font-size:14px;font-weight:600;cursor:pointer;
       border:none;font-family:var(--sans);transition:background .15s}
.mbtn-primary{background:var(--black);color:#fff}.mbtn-primary:hover{background:#333}
.mbtn-outline{background:transparent;color:var(--black);border:1px solid var(--border)}
.mbtn-outline:hover{border-color:var(--black)}

/* loading / empty */
.loading{text-align:center;padding:80px 24px;color:var(--warm-gray);
          font-family:var(--serif);font-size:18px;font-style:italic}
.empty-polls{text-align:center;padding:60px 24px;color:var(--warm-gray);
              font-size:14px;line-height:1.7}

/* footer */
#footer{background:var(--black);color:rgba(255,255,255,.4);
         padding:20px 24px;font-size:11px}
#footer-inner{max-width:1320px;margin:0 auto;display:flex;
               justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px}
#footer-inner a{color:rgba(255,255,255,.4);margin-left:16px}
#footer-inner a:hover{color:#fff}
</style>
</head>
<body>

<div id="util"><div id="util-inner">
  <span id="util-date"></span>
  <div>
    <a class="util-link" href="companies_site.html">Companies</a>
    <a class="util-link" style="margin-left:16px" href="mailto:hello@fitoutpost.com">Contact</a>
  </div>
</div></div>

<header id="masthead">
  <div id="mh-inner">
    <a href="index.html" id="fop-logo">
      <div id="fop-box"><span>FOP</span></div>
      <div id="fop-wm"><strong>FitOut Post</strong><em>Global Industry Intelligence</em></div>
    </a>
    <div id="be-badge">βEdge</div>
    <div id="mh-right">
      <a href="companies_site.html" class="mh-cta">Companies directory</a>
    </div>
  </div>
</header>

<nav id="pnav">
  <div id="pnav-inner">
    <a class="pnav-link" href="index.html">News</a>
    <a class="pnav-link" href="companies_site.html">Companies</a>
    <a class="pnav-link" href="alphaedge.html">αEdge</a>
    <a class="pnav-link active" href="#">βEdge</a>
  </div>
</nav>

<div id="be-header"><div id="be-hdr-inner">
  <div>
    <div id="be-title"><span class="greek">β</span>Edge</div>
    <div id="be-tagline">Polling with an edge — industry questions, real opinions, zero money.
      Register once to vote on any poll.</div>
  </div>
  <div id="be-meta"><strong id="be-poll-count">—</strong>active polls</div>
</div></div>

<div id="content-area">
  <div id="polls-col">
    <h3>Active polls</h3>
    <div id="polls-list"><div class="loading">Loading polls…</div></div>
  </div>
  <div id="side-col">
    <h3>How it works</h3>
    <div class="how-it-works">
      <div class="how-step">
        <div class="step-num">1</div>
        <div class="step-text"><strong>Read the question</strong><br>Each poll covers a real industry topic — costs, trends, regions, companies.</div>
      </div>
      <div class="how-step">
        <div class="step-num">2</div>
        <div class="step-text"><strong>Register once</strong><br>Name, organisation and email. Your details stay private and are only used to prevent duplicate votes.</div>
      </div>
      <div class="how-step">
        <div class="step-num">3</div>
        <div class="step-text"><strong>Vote and see results</strong><br>Results update live. One vote per person per poll.</div>
      </div>
    </div>
    <div class="disclaimer">
      <strong>For information only.</strong> βEdge polls are informal opinion surveys. No money, no prizes. Results reflect participant sentiment only and should not be used as market data.
    </div>
  </div>
</div>

<footer id="footer"><div id="footer-inner">
  <span>© <span id="fy"></span> FitOut Post. All rights reserved.</span>
  <div>
    <a href="legal.html#terms">Terms</a>
    <a href="legal.html#privacy">Privacy</a>
    <a href="mailto:hello@fitoutpost.com">Contact</a>
  </div>
</div></footer>

<!-- ─── Vote modal -->
<div class="modal-backdrop" id="vote-modal">
  <div class="modal">
    <h2>Cast your vote</h2>
    <div class="m-sub">Register to vote. Your details are private and used only to prevent duplicate votes.</div>
    <div class="m-selected-option">
      <strong>Your choice</strong>
      <span id="m-option-name"></span>
    </div>
    <div class="mfield"><label>Full name *</label><input type="text" id="m-name" autocomplete="name"></div>
    <div class="mfield"><label>Organisation *</label><input type="text" id="m-org" autocomplete="organization"></div>
    <div class="mfield"><label>Email address *</label><input type="email" id="m-email" autocomplete="email"></div>
    <div class="mfield"><label>Phone number (optional)</label><input type="tel" id="m-phone" autocomplete="tel"></div>
    <div class="mfield">
      <div class="mfield-check">
        <input type="checkbox" id="m-tc">
        <label for="m-tc">I accept the <a href="legal.html#terms" target="_blank" style="color:var(--claret)">Terms and Conditions</a> and understand this is an informal opinion poll.</label>
      </div>
    </div>
    <div class="m-status" id="m-status"></div>
    <div class="modal-actions">
      <button class="mbtn mbtn-primary" id="m-submit" onclick="submitVote()">Submit vote</button>
      <button class="mbtn mbtn-outline" onclick="closeModal()">Cancel</button>
    </div>
  </div>
</div>

<script>
const SERVER=""; // same origin
let activePollId="", activeOption="", votedPolls={};

// Load voted polls from localStorage
try{votedPolls=JSON.parse(localStorage.getItem("betaedge_voted")||"{}")}catch{}

function esc(s){return String(s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;")}
function fmtDate(iso){if(!iso)return"";try{return new Date(iso).toLocaleDateString("en-GB",{day:"numeric",month:"short",year:"numeric"})}catch{return iso}}

async function loadPolls(){
  try{
    const r=await fetch(SERVER+"/api/polls");
    const polls=await r.json();
    const active=polls.filter(p=>p.status==="active");
    document.getElementById("be-poll-count").textContent=active.length;
    renderPolls(active);
  }catch(e){
    document.getElementById("polls-list").innerHTML=
      `<div class="empty-polls">Could not load polls.<br><small>Make sure admin.py is running.</small></div>`;
  }
}

function renderPolls(polls){
  const list=document.getElementById("polls-list");
  if(!polls.length){
    list.innerHTML='<div class="empty-polls">No active polls at the moment.<br>Check back soon.</div>';
    return;
  }
  list.innerHTML=polls.map(p=>{
    const total=p.total_votes||0;
    const hasVoted=!!votedPolls[p.id];
    const isClosed=p.status==="closed"||
      (p.closes_at && new Date(p.closes_at)<new Date());
    const showBars=hasVoted||isClosed;

    const opts=p.options.map(o=>{
      const c=p.vote_counts[o]||0;
      const pct=total?Math.round(c/total*100):0;
      const isMyVote=votedPolls[p.id]===o;
      return `<div class="poll-option" ${(!showBars&&!isClosed)?`onclick="openModal('${esc(p.id)}','${esc(o)}','${esc(p.question)}')" style="cursor:pointer"`:""}>
        <div class="poll-option-label">
          <span class="poll-option-name">${esc(o)}${isMyVote?' <span style="color:var(--claret);font-size:11px">✓ your vote</span>':""}</span>
          ${showBars?`<span class="poll-option-pct">${pct}%</span>`:""}
        </div>
        <div class="poll-bar-track">
          <div class="poll-bar-fill" style="width:${showBars?pct:0}%"></div>
        </div>
      </div>`;
    }).join("");

    let footerRight="";
    if(hasVoted) footerRight=`<span class="voted-badge">✓ Voted</span>`;
    else if(isClosed) footerRight=`<span class="closed-badge">Poll closed</span>`;
    else footerRight=`<button class="btn-vote" onclick="openModal('${esc(p.id)}',null,'${esc(p.question)}')">Vote now</button>`;

    return `<div class="poll-card" id="poll-${esc(p.id)}">
      ${p.category?`<div class="poll-cat">${esc(p.category)}</div>`:""}
      <div class="poll-q">${esc(p.question)}</div>
      ${opts}
      <div class="poll-footer">
        <div>
          <div class="poll-votes">${total} vote${total!==1?"s":""}</div>
          ${p.closes_at?`<div class="poll-deadline">Closes ${fmtDate(p.closes_at)}</div>`:""}
        </div>
        ${footerRight}
      </div>
    </div>`;
  }).join("");
}

function openModal(pollId,option,question){
  activePollId=pollId; activeOption=option||"";
  document.getElementById("m-option-name").textContent=option||"(choose below)";
  document.getElementById("m-name").value="";
  document.getElementById("m-org").value="";
  document.getElementById("m-email").value="";
  document.getElementById("m-phone").value="";
  document.getElementById("m-tc").checked=false;
  document.getElementById("m-status").style.display="none";
  document.getElementById("vote-modal").classList.add("open");
  document.getElementById("m-name").focus();
}
function closeModal(){document.getElementById("vote-modal").classList.remove("open")}

async function submitVote(){
  const name=document.getElementById("m-name").value.trim();
  const org=document.getElementById("m-org").value.trim();
  const email=document.getElementById("m-email").value.trim();
  const phone=document.getElementById("m-phone").value.trim();
  const tc=document.getElementById("m-tc").checked;
  const st=document.getElementById("m-status");

  if(!name||!org||!email){st.textContent="Please fill in all required fields.";st.className="m-status err";st.style.display="block";return}
  if(!tc){st.textContent="Please accept the Terms and Conditions.";st.className="m-status err";st.style.display="block";return}
  if(!activeOption){st.textContent="Please select an option from the poll.";st.className="m-status err";st.style.display="block";return}

  document.getElementById("m-submit").disabled=true;
  st.textContent="Submitting…";st.className="m-status";st.style.display="block";

  try{
    const r=await fetch(SERVER+"/api/vote",{
      method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({poll_id:activePollId,option:activeOption,
        voter:{name,org,email,phone,tc_accepted:true}})
    });
    const d=await r.json();
    if(!r.ok)throw new Error(d.error||"Vote failed");
    votedPolls[activePollId]=activeOption;
    localStorage.setItem("betaedge_voted",JSON.stringify(votedPolls));
    st.textContent="✅ Vote recorded!";st.className="m-status ok";
    setTimeout(()=>{closeModal();loadPolls()},1200);
  }catch(e){
    st.textContent="Error: "+e.message;st.className="m-status err";
    document.getElementById("m-submit").disabled=false;
  }
}

document.getElementById("util-date").textContent=new Date().toLocaleDateString("en-GB",{weekday:"long",day:"numeric",month:"long",year:"numeric"});
document.getElementById("fy").textContent=new Date().getFullYear();
loadPolls();
// Refresh every 30 s so results stay live
setInterval(loadPolls,30000);
</script>
</body>
</html>
"""


# ════════════════════════════════════════════════════════════════════════════════
# HTTP HANDLER
# ════════════════════════════════════════════════════════════════════════════════
class AdminHandler(BaseHTTPRequestHandler):
    def log_message(self,fmt,*args):
        if args and str(args[1]) not in("200","204"): super().log_message(fmt,*args)

    def send_json(self,status,obj):
        body=json.dumps(obj,ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",str(len(body)))
        self.send_header("Access-Control-Allow-Origin","*")
        self.end_headers(); self.wfile.write(body)

    def send_html(self,html):
        body=html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type","text/html; charset=utf-8")
        self.send_header("Content-Length",str(len(body)))
        self.end_headers(); self.wfile.write(body)

    def read_body(self):
        n=int(self.headers.get("Content-Length",0))
        return json.loads(self.rfile.read(n))

    def do_GET(self):
        p=self.path.split("?")[0]
        if p in("/","/index.html"): self.send_html(ADMIN_HTML)
        elif p=="/betaedge-preview": self.send_html(BETAEDGE_PUBLIC_HTML)
        elif p=="/api/polls":
            self.send_json(200,polls_with_counts())
        elif p.startswith("/api/votes/"):
            pid=p[len("/api/votes/"):]
            votes=load(VOTES_FILE,{"votes":[]})["votes"]
            self.send_json(200,[v for v in votes if v.get("poll_id")==pid])
        elif p=="/api/alpha/articles":
            self.send_json(200,load(ALPHAEDGE_FILE,{"articles":[]}))
        elif p=="/api/gamma/games":
            self.send_json(200,load(GAMMAEDGE_FILE,{"last_updated":"","total_games":0,"games":[]}))
        elif p=="/api/intelligence/datapoints":
            self.send_json(200,load(INTEL_FILE,{"last_updated":"","total_datapoints":0,"periods":[]}))
        elif p=="/api/members":
            # Return member list from members.json (server-side) or empty list
            members_file = BASE / "members.json"
            data = load(members_file, {"members": [], "total": 0})
            self.send_json(200, data)
        elif p=="/api/members/export.csv":
            # Export member list as CSV
            members_file = BASE / "members.json"
            data = load(members_file, {"members": [], "total": 0})
            members = data.get("members", [])
            import io, csv as csv_mod
            buf = io.StringIO()
            fields = ["id","firstName","lastName","email","company","role","region","registeredAt","interests"]
            w = csv_mod.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            for m in members:
                m2 = dict(m)
                m2["interests"] = "|".join(m2.get("interests", []))
                w.writerow(m2)
            csv_bytes = buf.getvalue().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", 'attachment; filename="fitoutpost_members.csv"')
            self.send_header("Content-Length", str(len(csv_bytes)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(csv_bytes)
        else:
            self.send_response(404); self.end_headers()

    def do_POST(self):
        try: body=self.read_body()
        except: self.send_json(400,{"error":"Invalid JSON"}); return

        p=self.path
        # ── AlphaEdge
        if p=="/api/alpha/fetch":
            url=body.get("url","").strip()
            if not url: self.send_json(400,{"error":"url required"}); return
            try:
                meta=fetch_article_meta(url)
                meta["id"]=hashlib.md5(url.encode()).hexdigest()[:10]
                self.send_json(200,meta)
            except Exception as e: self.send_json(500,{"error":str(e)})

        elif p=="/api/alpha/save":
            article={
                "id":body.get("id") or hashlib.md5(body.get("url","").encode()).hexdigest()[:10],
                "url":body.get("url",""),"title":body.get("title",""),
                "summary":body.get("summary",""),"curator_note":body.get("curator_note",""),
                "published":body.get("published",""),
                "accessed_at":datetime.now(timezone.utc).isoformat(),
                "source":body.get("source",""),"tags":body.get("tags",[]),
            }
            if not article["title"]: self.send_json(400,{"error":"title required"}); return
            data=load(ALPHAEDGE_FILE,{"last_updated":"","total_articles":0,"articles":[]})
            data["articles"]=[a for a in data["articles"] if a.get("id")!=article["id"]]
            data["articles"].append(article)
            save_alphaedge(data)
            self.send_json(200,{"ok":True,"total":len(data["articles"])})

        elif p=="/api/alpha/delete":
            art_id=body.get("id","")
            data=load(ALPHAEDGE_FILE,{"last_updated":"","total_articles":0,"articles":[]})
            data["articles"]=[a for a in data["articles"] if a.get("id")!=art_id]
            save_alphaedge(data)
            self.send_json(200,{"ok":True})

        # ── BetaEdge
        elif p=="/api/beta/create":
            opts=[o.strip() for o in body.get("options",[]) if o.strip()]
            if len(opts)<2: self.send_json(400,{"error":"min 2 options"}); return
            poll={
                "id":hashlib.md5((body.get("question","")+datetime.now().isoformat()).encode()).hexdigest()[:10],
                "question":body.get("question","").strip(),
                "category":body.get("category","").strip(),
                "options":opts,
                "status":body.get("status","active"),
                "closes_at":body.get("closes_at") or None,
                "created_at":datetime.now(timezone.utc).isoformat(),
            }
            if not poll["question"]: self.send_json(400,{"error":"question required"}); return
            data=load(POLLS_FILE,{"polls":[]})
            data["polls"].append(poll)
            save_polls(data)
            _rebuild_betaedge()
            self.send_json(200,{"ok":True,"id":poll["id"]})

        elif p=="/api/beta/delete":
            pid=body.get("id","")
            pdata=load(POLLS_FILE,{"polls":[]})
            pdata["polls"]=[p for p in pdata["polls"] if p.get("id")!=pid]
            save_polls(pdata)
            vdata=load(VOTES_FILE,{"votes":[]})
            vdata["votes"]=[v for v in vdata["votes"] if v.get("poll_id")!=pid]
            save_votes(vdata)
            _rebuild_betaedge()
            self.send_json(200,{"ok":True})

        elif p=="/api/beta/update":
            pid=body.get("id","")
            data=load(POLLS_FILE,{"polls":[]})
            for poll in data["polls"]:
                if poll.get("id")==pid:
                    if "status" in body: poll["status"]=body["status"]
            save_polls(data)
            _rebuild_betaedge()
            self.send_json(200,{"ok":True})

        elif p=="/api/vote":
            poll_id=body.get("poll_id","")
            option=body.get("option","")
            voter=body.get("voter",{})
            if not poll_id or not option: self.send_json(400,{"error":"poll_id and option required"}); return
            if not voter.get("name") or not voter.get("email"):
                self.send_json(400,{"error":"name and email required"}); return
            # Prevent duplicate votes by email per poll
            vdata=load(VOTES_FILE,{"votes":[]})
            dupe=[v for v in vdata["votes"]
                  if v.get("poll_id")==poll_id and v.get("voter",{}).get("email","").lower()==voter.get("email","").lower()]
            if dupe: self.send_json(409,{"error":"You have already voted on this poll."}); return
            # Verify poll is active
            pdata=load(POLLS_FILE,{"polls":[]})
            poll=next((p for p in pdata["polls"] if p.get("id")==poll_id),None)
            if not poll: self.send_json(404,{"error":"Poll not found"}); return
            if poll.get("status")!="active": self.send_json(400,{"error":"This poll is not open for voting."}); return
            if option not in poll.get("options",[]): self.send_json(400,{"error":"Invalid option"}); return
            vote={
                "id":hashlib.md5((poll_id+voter.get("email","")+datetime.now().isoformat()).encode()).hexdigest()[:10],
                "poll_id":poll_id,"option":option,"voter":voter,
                "voted_at":datetime.now(timezone.utc).isoformat(),
            }
            vdata["votes"].append(vote)
            save_votes(vdata)
            _rebuild_betaedge()
            self.send_json(200,{"ok":True})

        # ── GammaEdge
        elif p=="/api/gamma/add":
            url=body.get("url","").strip()
            title=body.get("title","").strip()
            if not url:   self.send_json(400,{"error":"url required"}); return
            if not title: self.send_json(400,{"error":"title required"}); return
            game={
                "id": hashlib.md5(url.encode()).hexdigest()[:10],
                "title": title,
                "url": url,
                "description": body.get("description","").strip(),
                "game_type": body.get("game_type","Other"),
                "source": body.get("source","").strip(),
                "tags": [t for t in body.get("tags",[]) if t],
                "date_added": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            }
            data=load(GAMMAEDGE_FILE,{"last_updated":"","total_games":0,"games":[]})
            data["games"]=[g for g in data["games"] if g.get("id")!=game["id"]]
            data["games"].append(game)
            save_gammaedge(data)
            self.send_json(200,{"ok":True,"id":game["id"]})

        elif p=="/api/gamma/delete":
            gid=body.get("id","")
            data=load(GAMMAEDGE_FILE,{"last_updated":"","total_games":0,"games":[]})
            data["games"]=[g for g in data["games"] if g.get("id")!=gid]
            save_gammaedge(data)
            self.send_json(200,{"ok":True})

        # ── Intelligence routes ───────────────────────────────────────────────
        elif p=="/api/intelligence/add":
            period_id=body.get("period","")
            dp=body.get("datapoint",{})
            if not period_id or not dp:
                self.send_json(400,{"ok":False,"error":"period and datapoint required"})
                return
            # Generate id
            key=(dp.get("source","")+'|'+dp.get("city",dp.get("country",""))+'|'+
                 dp.get("fit_out_type","")+'|'+str(dp.get("cost_usd_m2_low",""))).encode()
            dp["id"]="dp_"+hashlib.md5(key).hexdigest()[:10]
            dp["date_added"]=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            data=load(INTEL_FILE,{"last_updated":"","total_datapoints":0,"periods":[]})
            # Find or create period
            period=next((p2 for p2 in data["periods"] if p2["id"]==period_id),None)
            if not period:
                from calendar import monthrange
                y,m=map(int,period_id.split("-"))
                _,last_day=monthrange(y,m)
                period={"id":period_id,"label":datetime(y,m,1).strftime("%B %Y"),
                        "start":f"{period_id}-01","end":f"{period_id}-{last_day:02d}","datapoints":[]}
                data["periods"].append(period)
            # Dedup by id
            if not any(d2["id"]==dp["id"] for d2 in period["datapoints"]):
                period["datapoints"].append(dp)
            save_intelligence(data)
            self.send_json(200,{"ok":True})

        elif p=="/api/intelligence/delete":
            period_id=body.get("period","")
            dp_id=body.get("id","")
            data=load(INTEL_FILE,{"last_updated":"","total_datapoints":0,"periods":[]})
            for per in data["periods"]:
                if per["id"]==period_id:
                    per["datapoints"]=[d2 for d2 in per["datapoints"] if d2.get("id")!=dp_id]
                    break
            save_intelligence(data)
            self.send_json(200,{"ok":True})

        elif p=="/api/intelligence/approve":
            period_id=body.get("period","")
            dp_id=body.get("id","")
            data=load(INTEL_FILE,{"last_updated":"","total_datapoints":0,"periods":[]})
            for per in data["periods"]:
                if per["id"]==period_id:
                    for dp in per["datapoints"]:
                        if dp.get("id")==dp_id:
                            dp["needs_review"]=False; break
                    break
            save_intelligence(data)
            self.send_json(200,{"ok":True})

        elif p=="/api/intelligence/fetch":
            # Run fetch_intelligence.py as subprocess
            import subprocess, sys as _sys
            try:
                result=subprocess.run(
                    [_sys.executable, str(BASE/"fetch_intelligence.py"), "--dry-run"],
                    capture_output=True, text=True, timeout=120,
                    cwd=str(BASE)
                )
                self.send_json(200,{"ok":True,
                    "message":f"Fetch complete (dry-run). Output: {result.stdout[-500:] if result.stdout else 'none'}",
                    "stderr":result.stderr[-500:] if result.stderr else ""})
            except subprocess.TimeoutExpired:
                self.send_json(200,{"ok":False,"error":"Fetch timed out after 120s"})
            except Exception as e:
                self.send_json(500,{"ok":False,"error":str(e)})

        # ── Members
        elif p=="/api/members/register":
            # Called by register.html when hosting is live (server-side backup)
            members_file = BASE / "members.json"
            data = load(members_file, {"members": [], "total": 0})
            member = {
                "id":         body.get("id", "fop_" + datetime.now().strftime("%Y%m%d%H%M%S%f")),
                "firstName":  body.get("firstName", ""),
                "lastName":   body.get("lastName", ""),
                "email":      body.get("email", "").lower().strip(),
                "company":    body.get("company", ""),
                "role":       body.get("role", ""),
                "region":     body.get("region", ""),
                "interests":  body.get("interests", []),
                "registeredAt": body.get("registeredAt", datetime.now(timezone.utc).isoformat()),
                "source":     "register.html",
            }
            if not member["email"]:
                self.send_json(400, {"error": "email required"}); return
            # Deduplicate by email
            data["members"] = [m for m in data["members"] if m.get("email") != member["email"]]
            data["members"].append(member)
            data["total"] = len(data["members"])
            data["last_updated"] = datetime.now(timezone.utc).isoformat()
            save(members_file, data)
            self.send_json(200, {"ok": True, "total": data["total"]})

        elif p=="/api/members/delete":
            member_id = body.get("id", "")
            members_file = BASE / "members.json"
            data = load(members_file, {"members": [], "total": 0})
            data["members"] = [m for m in data["members"] if m.get("id") != member_id]
            data["total"] = len(data["members"])
            save(members_file, data)
            self.send_json(200, {"ok": True})

        else:
            self.send_response(404); self.end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin","*")
        self.send_header("Access-Control-Allow-Headers","Content-Type")
        self.end_headers()


# ── Main ──────────────────────────────────────────────────────────────────────
def run():
    server=HTTPServer(("127.0.0.1",PORT),AdminHandler)
    def _open():
        import time; time.sleep(0.8)
        webbrowser.open(f"http://localhost:{PORT}")
    threading.Thread(target=_open,daemon=True).start()
    print(f"\n  ╔══════════════════════════════════════════╗")
    print(f"  ║  FitOut Post Admin                       ║")
    print(f"  ║  http://localhost:{PORT}                   ║")
    print(f"  ╠══════════════════════════════════════════╣")
    print(f"  ║  α Edge  — curated articles              ║")
    print(f"  ║  β Edge  — polls & voting                ║")
    print(f"  ║                                          ║")
    print(f"  ║  Ctrl+C to stop.                         ║")
    print(f"  ╚══════════════════════════════════════════╝\n")
    try: server.serve_forever()
    except KeyboardInterrupt: print("\n  Admin stopped.")

if __name__=="__main__": run()
