"""Build the transcript viewer.

Pipeline: spans.json (hand-picked quotes) + hyps.py (hypotheses) + the run's
above_good.json  ->  one self-contained HTML file.

The build only *locates* quotes chosen by reading. It fails loudly if a quote is
missing or ambiguous, so an annotation can never silently drift onto wrong text.
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hyps

RUN = "/Users/aanshsamyani/Documents/value_leakage/data/runs/qwen3.5-27b_20260823_223518"
OUT = "/Users/aanshsamyani/Documents/value_leakage/donation_bet_above_good.html"

d = json.load(open(f"{RUN}/above_good.json"))
T = d["threshold"]
src = {r["i"]: r for r in d["rows"]}
EST = json.load(open(f"{RUN}/estimates.json"))["above_good"]
A = json.load(open(f"{HERE}/spans.json"))
meta = {int(k): v for k, v in A["meta"].items()}

byrow, problems = {}, []
for s in A["spans"]:
    field = src[s["i"]]["reasoning"] if s["f"] == "r" else src[s["i"]]["content"]
    n = field.count(s["q"])
    if n == 0:
        problems.append(f"#{s['i']} [{s['f']}] NOT FOUND: {s['q'][:60]!r}"); continue
    if n > 1:
        problems.append(f"#{s['i']} [{s['f']}] AMBIGUOUS (x{n}): {s['q'][:60]!r}"); continue
    p = field.find(s["q"])
    byrow.setdefault(s["i"], []).append(dict(s=p, e=p + len(s["q"]), h=s["h"], f=s["f"], note=s["note"]))

if problems:
    print("BUILD FAILED — annotation problems:")
    [print("  " + p) for p in problems]
    sys.exit(1)

rows = []
for i in sorted(src):
    sp = sorted(byrow.get(i, []), key=lambda x: (x["f"] != "r", x["s"]))
    keep, last = [], {"r": -1, "a": -1}
    for x in sp:
        if x["s"] >= last[x["f"]]:
            keep.append(x); last[x["f"]] = x["e"]
    m = meta.get(i, {"cov": "unread", "noted": ""})
    rows.append(dict(i=i, r=src[i].get("reasoning") or "", a=src[i].get("content") or "",
                     tok=(src[i].get("usage") or {}).get("completion_tokens") or 0,
                     spans=keep, cov=m["cov"], noted=m["noted"],
                     est=EST[i] if i < len(EST) and EST[i] is not None else None))

ids = {x["id"] for x in hyps.HYPS}
for r in rows:
    for s in r["spans"]:
        assert s["h"] in ids, f"#{r['i']} references unknown hypothesis {s['h']}"

payload = dict(threshold=T, prompt=d["prompt"], model=d["model"], rows=rows,
               hyps=hyps.HYPS, fams={k: dict(name=v[0], blurb=v[1]) for k, v in hyps.FAMS.items()})
data = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")

nsp = sum(len(r["spans"]) for r in rows)
nread = sum(1 for r in rows if r["cov"] != "unread")
nlo = sum(1 for r in rows if r["est"] is not None and r["est"] <= T and r["cov"] != "unread")
anchored = {s["h"] for r in rows for s in r["spans"]}

CSS = r"""
:root{
 --paper:#eceff0;--card:#fff;--sunk:#e3e8e9;--ink:#15181a;--dim:#5b6467;--faint:#8b9497;
 --rule:#d4dadb;--rule2:#c3cbcc;--sel:#dde4e5;
 --fS:#3f6497;--fL:#0e7a70;--fF:#8a6a00;--fN:#87477f;--fC:#54701f;
 --fSb:#e2eaf4;--fLb:#dbeceb;--fFb:#f2eada;--fNb:#f0e2ee;--fCb:#e6eddb;
 --mono:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,monospace;
 --sans:"IBM Plex Sans",system-ui,-apple-system,Segoe UI,sans-serif;
 --serif:"Newsreader",Georgia,"Times New Roman",serif;}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
 --paper:#131718;--card:#1a1f20;--sunk:#101414;--ink:#e6ebec;--dim:#9aa4a6;--faint:#6e797b;
 --rule:#2b3233;--rule2:#3a4243;--sel:#242c2d;
 --fS:#8fb2de;--fL:#5ec3b6;--fF:#d5b45c;--fN:#d29ac9;--fC:#a8c46e;
 --fSb:#1d2937;--fLb:#122b29;--fFb:#2c2716;--fNb:#2b1e2a;--fCb:#1f2717;}}
:root[data-theme="dark"]{
 --paper:#131718;--card:#1a1f20;--sunk:#101414;--ink:#e6ebec;--dim:#9aa4a6;--faint:#6e797b;
 --rule:#2b3233;--rule2:#3a4243;--sel:#242c2d;
 --fS:#8fb2de;--fL:#5ec3b6;--fF:#d5b45c;--fN:#d29ac9;--fC:#a8c46e;
 --fSb:#1d2937;--fLb:#122b29;--fFb:#2c2716;--fNb:#2b1e2a;--fCb:#1f2717;}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);font-size:15px;
     line-height:1.5;-webkit-font-smoothing:antialiased}
.wrap{max-width:1760px;margin:0 auto;padding:0 20px 48px}
header{padding:24px 0 0}
h1{font-weight:600;font-size:20px;letter-spacing:-.015em;margin:0 0 3px}
.sub{color:var(--dim);font-size:12.5px;font-family:var(--mono)}
.stats{display:flex;flex-wrap:wrap;margin-top:15px;border:1px solid var(--rule);background:var(--card);border-radius:2px;overflow:hidden}
.stat{padding:8px 15px;border-right:1px solid var(--rule);flex:1 1 auto;min-width:112px}
.stat:last-child{border-right:0}
.stat b{display:block;font-family:var(--mono);font-size:16px;font-weight:500;font-variant-numeric:tabular-nums;letter-spacing:-.02em}
.stat span{display:block;font-size:10px;text-transform:uppercase;letter-spacing:.07em;color:var(--faint);margin-top:2px}
nav{display:flex;gap:2px;margin:18px 0 0;border-bottom:1px solid var(--rule2)}
nav button{font:inherit;font-size:13.5px;font-weight:500;padding:8px 15px;border:1px solid transparent;border-bottom:0;
  background:none;color:var(--dim);cursor:pointer;border-radius:2px 2px 0 0;margin-bottom:-1px}
nav button:hover{color:var(--ink)}
nav button.on{background:var(--card);border-color:var(--rule2);color:var(--ink)}
.view{display:none}.view.on{display:block}

/* ---------- hypotheses reading view ---------- */
.hv{padding-top:26px}
.intro{max-width:64ch;font-family:var(--serif);font-size:17px;line-height:1.6;color:var(--dim);margin:0 0 34px}
.intro b{color:var(--ink);font-weight:500}
.fsec{margin:0 0 8px;padding-top:26px;border-top:1px solid var(--rule2)}
.fsec h2{font-size:12px;text-transform:uppercase;letter-spacing:.1em;margin:0 0 5px;display:flex;align-items:center;gap:8px}
.fsec .fb{max-width:60ch;color:var(--dim);font-size:14px;margin:0 0 4px}
article{max-width:72ch;padding:20px 0 22px 22px;border-left:2px solid var(--hc);margin:18px 0 0;position:relative}
article h3{margin:0 0 10px;font-size:19px;font-weight:600;letter-spacing:-.012em;line-height:1.25}
article h3 .hid{font-family:var(--mono);font-size:12px;font-weight:600;color:var(--hc);
  display:inline-block;min-width:34px;vertical-align:2px}
.claim{font-family:var(--serif);font-size:19px;line-height:1.5;margin:0 0 16px;max-width:62ch}
.blk{margin:13px 0 0;max-width:66ch}
.blk .k{display:block;font-family:var(--mono);font-size:9.5px;text-transform:uppercase;letter-spacing:.09em;
  color:var(--faint);margin-bottom:3px}
.blk p{margin:0;font-size:14.5px;line-height:1.58;color:var(--dim)}
.blk.t p{background:var(--sunk);border:1px solid var(--rule);border-radius:2px;padding:10px 13px;font-size:14px}
.chips{margin-top:13px;display:flex;flex-wrap:wrap;gap:5px;align-items:center}
.chip{font:inherit;font-family:var(--mono);font-size:11px;padding:2px 7px;border:1px solid var(--rule2);
  background:var(--card);color:var(--dim);border-radius:2px;cursor:pointer}
.chip:hover{background:var(--hb);border-color:var(--hc);color:var(--ink)}
.chips .cl{font-family:var(--mono);font-size:9.5px;text-transform:uppercase;letter-spacing:.09em;color:var(--faint);margin-right:3px}
.nopass{font-size:13px;color:var(--faint);font-style:italic;margin-top:11px}

/* ---------- transcripts view ---------- */
.grid{display:grid;grid-template-columns:236px minmax(0,1fr) 306px;gap:18px;margin-top:20px;align-items:start}
.pane{background:var(--card);border:1px solid var(--rule);border-radius:2px}
.stick{position:sticky;top:12px;max-height:calc(100vh - 26px);display:flex;flex-direction:column}
.ph{padding:8px 12px;border-bottom:1px solid var(--rule);font-size:10px;text-transform:uppercase;letter-spacing:.075em;
  color:var(--faint);display:flex;justify-content:space-between;align-items:center;flex:0 0 auto}
.scroll{overflow-y:auto;min-height:0}
.ix{width:100%;text-align:left;background:none;border:0;border-bottom:1px solid var(--rule);padding:6px 12px;
  cursor:pointer;font:inherit;color:inherit;display:grid;grid-template-columns:30px 1fr auto;gap:8px;align-items:baseline}
.ix:hover{background:var(--sel)}
.ix.on{background:var(--sel);box-shadow:inset 2px 0 0 var(--ink)}
.ix.off{opacity:.26}
.ix .n{font-family:var(--mono);font-size:11.5px;color:var(--faint);font-variant-numeric:tabular-nums}
.ix .v{font-family:var(--mono);font-size:12px;font-variant-numeric:tabular-nums}
.ix .v.lo{color:var(--dim);text-decoration:underline dotted;text-underline-offset:3px}
.ix .m{display:flex;gap:3px;align-items:center}
.dot{width:5px;height:5px;border-radius:50%;display:inline-block;flex:0 0 auto}
.cnt{font-family:var(--mono);font-size:10px;color:var(--faint)}
.unread{opacity:.4}
.tbody{padding:18px 22px 26px}
.meta{display:flex;flex-wrap:wrap;gap:12px;align-items:baseline;border-bottom:1px solid var(--rule);padding-bottom:11px;margin-bottom:14px}
.meta h2{margin:0;font-size:18px;font-weight:600;font-family:var(--mono);letter-spacing:-.02em}
.tag{font-size:10px;text-transform:uppercase;letter-spacing:.07em;color:var(--faint);border:1px solid var(--rule2);padding:1px 6px;border-radius:2px}
.lab{font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:var(--faint);margin:20px 0 6px}
details.prompt{border:1px solid var(--rule);border-radius:2px;background:var(--sunk)}
details.prompt summary{cursor:pointer;padding:7px 12px;font-size:12.5px;color:var(--dim);list-style:none}
details.prompt summary::-webkit-details-marker{display:none}
details.prompt summary::before{content:"▸ ";color:var(--faint)}
details.prompt[open] summary::before{content:"▾ "}
details.prompt .pw{padding:0 14px 12px;font-family:var(--mono);font-size:12.5px;white-space:pre-wrap;color:var(--dim);line-height:1.65}
.cot{font-family:var(--mono);font-size:12.5px;line-height:1.72;white-space:pre-wrap;word-wrap:break-word;
  background:var(--sunk);border:1px solid var(--rule);border-radius:2px;padding:15px 17px}
.ans{font-family:var(--mono);font-size:12.5px;line-height:1.7;white-space:pre-wrap;word-wrap:break-word;
  border:1px solid var(--rule2);border-left:3px solid var(--ink);border-radius:2px;padding:13px 17px}
mark{background:var(--hb);border-bottom:2px solid var(--hc);color:inherit;padding:1px 0;cursor:pointer;border-radius:1px}
mark.dimmed{background:transparent;border-bottom-color:var(--rule2);opacity:.45}
mark sup{font-family:var(--mono);font-size:9px;font-weight:600;color:var(--hc);vertical-align:super;padding-left:2px}
.note{margin:9px 0 2px;padding:9px 13px;border-left:2px solid var(--hc);background:var(--hb);
  font-family:var(--serif);font-size:14.5px;line-height:1.55;border-radius:0 2px 2px 0}
.note b{font-family:var(--mono);font-size:10.5px;font-weight:600;color:var(--hc);text-transform:uppercase;
  letter-spacing:.05em;display:block;margin-bottom:3px}
.note .more{font-family:var(--sans);font-size:12px;display:block;margin-top:6px}
.note .more button{font:inherit;background:none;border:0;padding:0;color:var(--hc);cursor:pointer;text-decoration:underline}
.empty{color:var(--faint);font-size:13.5px;padding:12px 0;font-style:italic}
.rail{width:100%;text-align:left;background:none;border:0;border-bottom:1px solid var(--rule);padding:7px 12px;
  cursor:pointer;font:inherit;color:inherit;display:grid;grid-template-columns:24px 1fr;gap:6px}
.rail:hover{background:var(--sel)}
.rail.on{background:var(--sel)}
.rail.off{opacity:.3}
.rail .id{font-family:var(--mono);font-size:10.5px;font-weight:600;padding-top:2px}
.rail .nm{font-size:12.5px;line-height:1.3;font-weight:500}
.rail .cl{font-size:11.5px;line-height:1.4;color:var(--faint);margin-top:2px;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.rh{padding:9px 12px 2px;font-size:10px;text-transform:uppercase;letter-spacing:.08em;color:var(--faint);
  display:flex;align-items:center;gap:6px;border-top:1px solid var(--rule)}
.bar{display:flex;gap:6px;padding:7px 12px;border-bottom:1px solid var(--rule);flex:0 0 auto}
.bar input{flex:1;min-width:0;font:inherit;font-size:12.5px;padding:4px 8px;border:1px solid var(--rule2);
  border-radius:2px;background:var(--paper);color:var(--ink);font-family:var(--mono)}
.clr{font:inherit;font-size:11.5px;padding:4px 9px;border:1px solid var(--rule2);background:var(--paper);
  color:var(--dim);border-radius:2px;cursor:pointer;white-space:nowrap}
.clr:hover{background:var(--sel);color:var(--ink)}
footer{margin-top:26px;padding-top:14px;border-top:1px solid var(--rule2);color:var(--faint);font-size:12px;line-height:1.6;max-width:88ch}
@media (max-width:1180px){.grid{grid-template-columns:1fr}.stick{position:static;max-height:none}.scroll{max-height:330px}}
"""

JS = r"""
const D=JSON.parse(document.getElementById('d').textContent),T=D.threshold;
const FC={S:'--fS',L:'--fL',F:'--fF',N:'--fN',C:'--fC'},FB={S:'--fSb',L:'--fLb',F:'--fFb',N:'--fNb',C:'--fCb'};
const H={};D.hyps.forEach(h=>H[h.id]=h);
const R={};D.rows.forEach(r=>R[r.i]=r);
let cur=null,curHyp=null;
const esc=s=>s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
const fmt=n=>n==null?'—':n.toLocaleString('en-US');
const HC={};D.rows.forEach(r=>r.spans.forEach(s=>HC[s.h]=(HC[s.h]||0)+1));
const EV=id=>{const o=[];D.rows.forEach(r=>r.spans.forEach(s=>{if(s.h===id)o.push({i:r.i,note:s.note})}));return o};

function setView(v){
  document.querySelectorAll('.view').forEach(x=>x.classList.toggle('on',x.id==='v-'+v));
  document.querySelectorAll('nav button').forEach(b=>b.classList.toggle('on',b.dataset.v===v));
  if(v==='h') window.scrollTo({top:0,behavior:'instant'});
}

/* hypotheses reading view */
function drawHyps(){
  const el=document.getElementById('hv');el.innerHTML='';
  Object.entries(D.fams).forEach(([fk,f])=>{
    const sec=document.createElement('section');sec.className='fsec';
    sec.innerHTML=`<h2><i class="dot" style="background:var(${FC[fk]})"></i>${esc(f.name)}</h2><p class="fb">${esc(f.blurb)}</p>`;
    D.hyps.filter(h=>h.fam===fk).forEach(h=>{
      const ev=EV(h.id),a=document.createElement('article');
      a.id='hyp-'+h.id;
      a.style.setProperty('--hc',`var(${FC[fk]})`);a.style.setProperty('--hb',`var(${FB[fk]})`);
      a.innerHTML=
        `<h3><span class="hid">${h.id}</span>${esc(h.name)}</h3>`+
        `<p class="claim">${esc(h.claim)}</p>`+
        `<div class="blk"><span class="k">What you see in the traces</span><p>${esc(h.looks)}</p></div>`+
        `<div class="blk"><span class="k">Why it matters</span><p>${esc(h.matters)}</p></div>`+
        `<div class="blk t"><span class="k">How to test it</span><p>${esc(h.test)}</p></div>`+
        (ev.length
          ?`<div class="chips"><span class="cl">Highlighted in</span>`+
            ev.map(e=>`<button class="chip" data-i="${e.i}" data-h="${h.id}">#${e.i}</button>`).join('')+`</div>`
          :`<p class="nopass">No highlighted passage — this one lives in the distribution across rollouts, not in any single sentence.</p>`);
      sec.appendChild(a);
    });
    el.appendChild(sec);
  });
  el.querySelectorAll('.chip').forEach(c=>c.onclick=()=>{
    setView('t');pickHyp(c.dataset.h);select(+c.dataset.i);
    setTimeout(()=>{const m=document.querySelector(`#tc mark[data-h="${c.dataset.h}"]`);
      if(m){m.scrollIntoView({block:'center',behavior:'smooth'});showNote(m);}},70);
  });
}

/* transcripts */
function drawIndex(){
  const q=document.getElementById('q').value.trim(),el=document.getElementById('ix');el.innerHTML='';let n=0;
  D.rows.forEach(r=>{
    if(q&&!String(r.i).includes(q))return;
    const has=curHyp?r.spans.some(s=>s.h===curHyp):true,lo=r.est!=null&&r.est<=T;
    const fams=[...new Set(r.spans.map(s=>H[s.h].fam))];
    const b=document.createElement('button');
    b.className='ix'+(cur===r.i?' on':'')+(has?'':' off')+(r.cov==='unread'?' unread':'');
    b.innerHTML=`<span class="n">${r.i}</span><span class="v${lo?' lo':''}">${r.est==null?'—':(r.est/1e6).toFixed(1)+'M'}</span>`+
      `<span class="m">${fams.map(f=>`<i class="dot" style="background:var(${FC[f]})"></i>`).join('')}${r.spans.length?`<span class="cnt">${r.spans.length}</span>`:''}</span>`;
    b.title=`#${r.i} · ${fmt(r.est)} · ${r.cov==='unread'?'not read':r.cov==='partial'?'read in part':'read in full'}`;
    b.onclick=()=>select(r.i);el.appendChild(b);n++;
  });
  document.getElementById('ixn').textContent=n+' / 100';
}
function renderText(t,sp,f){let o='',p=0;sp.filter(s=>s.f===f).forEach(s=>{
  const h=H[s.h],dim=curHyp&&curHyp!==s.h;o+=esc(t.slice(p,s.s));
  o+=`<mark class="${dim?'dimmed':''}" data-h="${s.h}" style="--hb:var(${FB[h.fam]});--hc:var(${FC[h.fam]})">`+
     esc(t.slice(s.s,s.e))+`<sup>${s.h}</sup></mark>`;p=s.e;});
  return o+esc(t.slice(p));}
function select(i){
  cur=i;const r=R[i],lo=r.est!=null&&r.est<=T;
  const cov=r.cov==='unread'?'not read':r.cov==='partial'?'read in part (output truncated)':'read in full';
  document.getElementById('tc').innerHTML=
    `<div class="meta"><h2>#${r.i}</h2><span class="tag">${fmt(r.est)}${lo?' · below threshold':''}</span>`+
    `<span class="tag">${r.tok.toLocaleString()} reasoning tokens</span><span class="tag">${cov}</span>`+
    (r.spans.length?`<span class="tag">${r.spans.length} highlighted</span>`:'')+`</div>`+
    (r.noted?`<div class="note" style="--hb:var(--sunk);--hc:var(--rule2)"><b>read note</b>${esc(r.noted)} — logged while reading; no verbatim passage reconstructed for this build.</div>`:'')+
    `<details class="prompt"><summary>Prompt (identical for all 100 rollouts)</summary><div class="pw">${esc(D.prompt)}</div></details>`+
    `<div class="lab">Chain of thought</div>`+
    (r.r?`<div class="cot">${renderText(r.r,r.spans,'r')}</div>`:`<div class="empty">No reasoning returned.</div>`)+
    `<div class="lab">Visible answer</div><div class="ans">${renderText(r.a,r.spans,'a')}</div>`;
  document.querySelectorAll('#tc mark').forEach(m=>m.onclick=()=>{pickHyp(m.dataset.h);showNote(m);});
  drawIndex();document.getElementById('tp').scrollTop=0;
}
function showNote(mark){
  document.querySelectorAll('.note.inline').forEach(n=>n.remove());
  const r=R[cur],idx=[...document.querySelectorAll('#tc mark')].indexOf(mark),s=r.spans[idx];
  if(!s)return;const h=H[s.h],d=document.createElement('div');d.className='note inline';
  d.style.setProperty('--hb',`var(${FB[h.fam]})`);d.style.setProperty('--hc',`var(${FC[h.fam]})`);
  d.innerHTML=`<b>${h.id} · ${esc(h.name)}</b>${esc(s.note)}`+
    `<span class="more"><button data-h="${h.id}">Read the full hypothesis →</button></span>`;
  const host=mark.closest('.cot,.ans');host.parentNode.insertBefore(d,host.nextSibling);
  d.querySelector('button').onclick=()=>{setView('h');
    setTimeout(()=>document.getElementById('hyp-'+h.id).scrollIntoView({block:'start',behavior:'smooth'}),40);};
  d.scrollIntoView({block:'nearest',behavior:'smooth'});
}
function drawRail(){
  const el=document.getElementById('rl');el.innerHTML='';
  Object.entries(D.fams).forEach(([fk,f])=>{
    const hd=document.createElement('div');hd.className='rh';
    hd.innerHTML=`<i class="dot" style="background:var(${FC[fk]})"></i>${esc(f.name)}`;el.appendChild(hd);
    D.hyps.filter(h=>h.fam===fk).forEach(h=>{
      const b=document.createElement('button');
      b.className='rail'+(curHyp===h.id?' on':'')+(curHyp&&curHyp!==h.id?' off':'');
      b.innerHTML=`<span class="id" style="color:var(${FC[fk]})">${h.id}</span>`+
        `<span><span class="nm">${esc(h.name)}</span><span class="cl">${esc(h.claim)}</span></span>`;
      b.onclick=()=>pickHyp(curHyp===h.id?null:h.id);el.appendChild(b);
    });
  });
}
function pickHyp(id){curHyp=id;drawRail();drawIndex();if(cur!=null)select(cur);}
document.getElementById('clr').onclick=()=>pickHyp(null);
document.getElementById('q').oninput=drawIndex;
document.querySelectorAll('nav button').forEach(b=>b.onclick=()=>setView(b.dataset.v));
document.addEventListener('keydown',e=>{
  if(e.target.tagName==='INPUT')return;
  if(e.key==='j'||e.key==='k'){const a=D.rows.map(r=>r.i);let k=a.indexOf(cur);
    k=e.key==='j'?Math.min(a.length-1,k+1):Math.max(0,k-1);select(a[k]);
    const on=document.querySelector('.ix.on');if(on)on.scrollIntoView({block:'nearest'});}
});
drawHyps();drawRail();drawIndex();select(71);setView('h');
"""

INTRO = ("Twenty-five hypotheses about how a donation-bet incentive gets into a model's estimate, "
         "drawn from reading the chains of thought one at a time rather than searching them for keywords. "
         "Each is stated as a claim, with what you actually see in the traces, why it matters, and how to check it. "
         "<b>The short version: the model does not reason its way to a biased answer — it reasons roughly normally, "
         "and the incentive decides when it has done enough.</b> "
         "Every hypothesis links to the passages it came from; those open in the Transcripts tab.")

html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The Winning Logic</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&family=Newsreader:opsz,wght@6..72,400;6..72,500&display=swap">
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>The Winning Logic</h1>
  <div class="sub">{payload['model']} · donation bet, above_good · threshold {T:,} · 100 rollouts</div>
  <div class="stats">
    <div class="stat"><b>{len(payload['hyps'])}</b><span>hypotheses</span></div>
    <div class="stat"><b>{nsp}</b><span>highlighted passages</span></div>
    <div class="stat"><b>{nread}</b><span>rollouts read</span></div>
    <div class="stat"><b>{nlo}</b><span>read &amp; below threshold</span></div>
    <div class="stat"><b>{T/1e6:.2f}M</b><span>threshold</span></div>
    <div class="stat"><b>~890</b><span>critical spots/giraffe</span></div>
  </div>
  <nav><button data-v="h" class="on">Hypotheses</button><button data-v="t">Transcripts</button></nav>
</header>

<div class="view on" id="v-h"><div class="hv"><p class="intro">{INTRO}</p><div id="hv"></div></div></div>

<div class="view" id="v-t">
 <div class="grid">
  <div class="pane stick">
    <div class="ph"><span>Rollouts</span><span id="ixn"></span></div>
    <div class="bar"><input id="q" placeholder="jump to #" inputmode="numeric"><button class="clr" id="clr">clear filter</button></div>
    <div class="scroll" id="ix"></div>
  </div>
  <div class="pane" id="tp"><div class="tbody" id="tc"></div></div>
  <div class="pane stick">
    <div class="ph"><span>Filter by hypothesis</span></div>
    <div class="scroll" id="rl"></div>
  </div>
 </div>
</div>

<footer>
  In the rollout list the value is the parsed final estimate; a dotted underline marks one that landed <em>below</em> the
  threshold. Coloured dots show which hypothesis families were highlighted there. Faded rows were not read.
  Highlights were chosen by reading each chain of thought; the build step only locates those exact strings in the source
  and fails if one is missing or matches more than once. Keyboard: <b style="font-family:var(--mono)">j</b> /
  <b style="font-family:var(--mono)">k</b> steps through rollouts.
</footer>
</div>
<script id="d" type="application/json">{data}</script>
<script>{JS}</script>
</body>
</html>
"""
open(OUT, "w", encoding="utf-8").write(html)
print(f"OK  spans={nsp}  read={nread}  hypotheses={len(payload['hyps'])}  "
      f"anchored={len(anchored)}  corpus-level={sorted(ids - anchored)}")
print(f"wrote {OUT}  {os.path.getsize(OUT)/1e6:.2f} MB")
