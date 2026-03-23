"""views/dalio_view.py — Dalio historical overlay tab."""
import streamlit as st
import streamlit.components.v1 as components


DALIO_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,sans-serif;color:#111;background:#fff;padding:12px}
@media(prefers-color-scheme:dark){body{color:#e8e6df;background:#161614}}
.vbtns{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:12px}
.vb{padding:5px 13px;border-radius:20px;font-size:12px;font-weight:500;cursor:pointer;
    background:#f1efe8;color:#5f5e5a;border:0.5px solid rgba(0,0,0,.1);transition:all .12s}
.vb.on{background:#fdf6ed;color:#915a00;border:1.5px solid #d4a847}
.leg{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:10px}
.li{display:flex;align-items:center;gap:6px;padding:3px 9px;border-radius:5px;
    cursor:pointer;border:0.5px solid rgba(0,0,0,.1);font-size:11px;font-weight:500;
    color:#555;transition:opacity .15s;user-select:none}
.li.off{opacity:.25}
.sw{width:20px;height:3px;border-radius:2px;flex-shrink:0;margin-top:1px}
.cw{position:relative;width:100%;height:300px;margin-bottom:10px}
.ins{padding:9px 12px;border-radius:8px;font-size:11px;line-height:1.65;margin-bottom:12px}
.wg{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:10px}
.wc{padding:10px 12px;border-radius:8px;border:0.5px solid rgba(0,0,0,.1)}
.wl{font-size:10px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;margin-bottom:4px}
.wt{font-size:12px;font-weight:500;margin-bottom:3px}
.wn{font-size:11px;color:#888;line-height:1.5}
.dn{margin-top:8px;padding:10px 12px;background:#f7f7f6;border:0.5px solid rgba(0,0,0,.1);
    border-radius:8px;font-size:11px;color:#555;line-height:1.7}
</style>
</head>
<body>

<div class="vbtns" id="vb">
  <button class="vb on" onclick="sv('oil',this)">Oil price</button>
  <button class="vb"    onclick="sv('sp',this)">S&P 500 drawdown</button>
  <button class="vb"    onclick="sv('gold',this)">Gold performance</button>
  <button class="vb"    onclick="sv('sc',this)">Duration vs depth</button>
</div>

<div class="leg" id="leg"></div>
<div class="cw"><canvas id="ch"></canvas></div>
<div class="ins" id="ins"></div>

<div class="wg">
  <div class="wc" style="background:#f0f8f4;border-color:#a8d9bc">
    <div class="wl" style="color:#1a6b3c">Past empires</div>
    <div class="wt">Dutch → British → US</div>
    <div class="wn">Each reserve currency lasted 200–250 years. Dutch peaked ~1650. British ~1815–1945. US: 1945–?</div>
  </div>
  <div class="wc" style="background:#fdf6ed;border:1.5px solid #d4a847">
    <div class="wl" style="color:#915a00">Now — 2026 · Year 250</div>
    <div class="wt">US structural inflection</div>
    <div class="wn">102% debt/GDP · petrodollar strain · Iran as catalyst. Not collapse — transition over years.</div>
  </div>
  <div class="wc" style="background:#f7f7f6">
    <div class="wl" style="color:#888">The transition risk</div>
    <div class="wt">Multipolar reserve system</div>
    <div class="wn">Most likely: dollar 30–35%, yuan 35–40%, euro 15%. Dollar dilution, not collapse.</div>
  </div>
</div>
<div class="dn">
  <strong>Why this changes the model:</strong> In 1973 (debt/GDP 35%) and 1990 (55%), the Fed could Volcker its way out.
  At 102%, aggressive rate hikes trigger a debt service crisis. This is baked in as a permanent +5pts Scenario C prior.
  The Iran conflict is not just an oil shock — it is the catalyst for a system already under strain.
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<script>
const C={'1973':'#E24B4A','1979':'#D85A30','1990':'#4a9e4a','2008':'#7b6fd4','2022':'#1D9E75','2026':'#d4a847'};
const D={'1973':[],'1979':[7,3],'1990':[3,3],'2008':[9,4],'2022':[5,4],'2026':[]};
const L={'1973':'1973 Yom Kippur','1979':'1979 Iran revolution','1990':'1990 Gulf War','2008':'2008 Financial crisis','2022':'2022 Russia/Ukraine','2026':'2026 Iran (live)'};
const V={
  oil:{xl:'Months after onset',yl:'Oil ($/barrel)',yt:v=>'$'+Math.round(v),
    tl:(ep,xi,y)=>L[ep]+' · M+'+xi+': $'+Math.round(y)+'/bbl',
    ins:'2026 oil at $100 — fastest spike on record (+68% in 23 days). 1973 took 5 months to triple from $3 to $12. 1990 peaked at $46 in 2 months then reversed. 102% debt/GDP prevents 1990-style fast resolution.',
    ib:'#fdf2f2',ibr:'#f5c6c4',ic:'#c0392b',
    lb:['M+0','M+1','M+2','M+3','M+4','M+5','M+6','M+9','M+12','M+18','M+24'],
    d:{'1973':[3,4.5,7,11,12,11.5,11,10.8,10.5,9.2,8.8],'1979':[13,16,20,25,30,34,36,39.5,39.5,32,24],'1990':[17,23,36,46,34,24,19,17,16.5,16,15.5],'2008':[80,90,105,120,135,147,130,70,45,60,78],'2022':[75,92,105,100,94,88,85,80,75,72,78],'2026':[62,90,100,null,null,null,null,null,null,null,null]},
  },
  sp:{xl:'Months after onset',yl:'S&P (% of peak)',yt:v=>Math.round(v)+'%',
    tl:(ep,xi,y)=>L[ep]+' · M+'+xi+': '+y.toFixed(1)+'% of peak',
    ins:'At day 23 the S&P is only −6.7% from peak. Median oil shock max drawdown is −23%. In 1973 the 200-day break preceded the worst losses by 6 months — which just happened.',
    ib:'#fdf6ed',ibr:'#f0d090',ic:'#915a00',
    lb:['M+0','M+1','M+2','M+3','M+4','M+5','M+6','M+9','M+12','M+18','M+24'],
    d:{'1973':[100,94,87,80,72,65,60,52,55,62,72],'1979':[100,104,100,96,92,94,91,88,84,90,96],'1990':[100,96,90,84,86,91,95,98,100,107,115],'2008':[100,93,82,72,58,48,44,43,50,62,78],'2022':[100,92,84,78,76,79,83,89,94,99,108],'2026':[100,99,96,null,null,null,null,null,null,null,null]},
  },
  gold:{xl:'Months after onset',yl:'Gold ($/oz)',yt:v=>'$'+Math.round(v),
    tl:(ep,xi,y)=>L[ep]+' · M+'+xi+': $'+Math.round(y)+'/oz',
    ins:'Gold tracking closest to 1979 parabolic. In 1979 gold ran from $226 to $843 (+275%) in 12 months before Volcker collapsed it 40% in 8 weeks. 2026 gold at $4,660 is in the accumulation phase.',
    ib:'#fdf6ed',ibr:'#f0d090',ic:'#915a00',
    lb:['M+0','M+1','M+2','M+3','M+6','M+9','M+12','M+18','M+24'],
    d:{'1973':[100,107,116,128,158,182,208,255,310],'1979':[226,256,292,368,560,843,843,620,520],'1990':[365,382,395,408,388,372,355,340,330],'2008':[870,920,960,1010,1050,1010,970,1050,1150],'2022':[1820,1980,2050,1980,1820,1700,1660,1600,1840],'2026':[3820,4100,4660,null,null,null,null,null,null]},
  },
  sc:{isSc:true,xl:'Oil shock duration (months)',yl:'S&P drawdown (%)',yt:v=>v+'%',
    ins:'Duration determines depth. Every short shock (1990, 2022) stayed above −25%. Every long shock (1973, 2008) reached −48% to −57%. 2026 is at month 1, −6.7% — the story is just beginning.',
    ib:'#fdf6ed',ibr:'#f0d090',ic:'#915a00',
    pts:{'1973':{x:21,y:-48,n:'21 months · −48%'},'1979':{x:18,y:-17,n:'18 months · −17%'},'1990':{x:9,y:-20,n:'9 months · −20%'},'2008':{x:17,y:-57,n:'17 months · −57%'},'2022':{x:12,y:-25,n:'12 months · −25%'},'2026':{x:1,y:-6.7,n:'Day 23 · −6.7%'}},
  },
};
const hidden=new Set();let chart=null,cv='oil';

function buildLeg(){
  const l=document.getElementById('leg');l.innerHTML='';
  Object.entries(C).forEach(([ep,col])=>{
    const i=document.createElement('div');i.className='li';i.id='lg-'+ep;
    const s=document.createElement('span');s.className='sw';
    if(D[ep].length){s.style.cssText='width:20px;height:0;border-top:2.5px dashed '+col+';margin-top:5px;border-radius:0';}
    else s.style.background=col;
    const t=document.createElement('span');t.textContent=L[ep];
    i.appendChild(s);i.appendChild(t);
    i.addEventListener('click',()=>{hidden.has(ep)?hidden.delete(ep):hidden.add(ep);document.getElementById('lg-'+ep).classList.toggle('off',hidden.has(ep));rc(cv);});
    l.appendChild(i);
  });
}

function sv(v,btn){cv=v;document.querySelectorAll('.vb').forEach(b=>b.classList.remove('on'));btn.classList.add('on');rc(v);}

function applyIns(vd){const i=document.getElementById('ins');i.textContent=vd.ins;i.style.background=vd.ib;i.style.border='0.5px solid '+vd.ibr;i.style.color=vd.ic;}

function dim(ch,keep){ch.data.datasets.forEach((ds,i)=>{const ep=ds.label;const base=ep==='2026'?2.8:1.5;if(keep===null||i===keep){ds.borderColor=C[ep];ds.borderWidth=ep==='2026'?3:2;ds.pointRadius=ep==='2026'?4:3;}else{ds.borderColor=C[ep]+'2a';ds.borderWidth=0.6;ds.pointRadius=0;}});ch.update('none');}
function reset(ch){ch.data.datasets.forEach(ds=>{const ep=ds.label;ds.borderColor=C[ep];ds.borderWidth=ep==='2026'?2.8:1.5;ds.pointRadius=ep==='2026'?3:1.5;});ch.update('none');}

function rc(v){
  if(chart){chart.destroy();chart=null;}
  const ctx=document.getElementById('ch').getContext('2d');
  const vd=V[v];applyIns(vd);
  if(vd.isSc){
    const ds=Object.entries(vd.pts).filter(([ep])=>!hidden.has(ep)).map(([ep,pt])=>({label:ep,data:[{x:pt.x,y:pt.y}],backgroundColor:C[ep]+'cc',borderColor:C[ep],pointRadius:ep==='2026'?13:10,pointHoverRadius:15,borderWidth:ep==='2026'?2.5:1.5}));
    chart=new Chart(ctx,{type:'scatter',data:{datasets:ds},options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'nearest',intersect:true},plugins:{legend:{display:false},tooltip:{mode:'nearest',intersect:true,callbacks:{title:i=>L[i[0].dataset.label],label:i=>vd.pts[i.dataset.label]?.n||''}}},scales:{x:{title:{display:true,text:vd.xl,color:'#888',font:{size:11}},min:0,max:25,grid:{color:'rgba(128,128,128,.1)'},ticks:{color:'#888',font:{size:11},callback:v=>v+'mo'}},y:{title:{display:true,text:vd.yl,color:'#888',font:{size:11}},min:-65,max:10,grid:{color:'rgba(128,128,128,.1)'},ticks:{color:'#888',font:{size:11},callback:v=>v+'%'}}}}});
    ctx.canvas.addEventListener('mousemove',e=>{const p=chart.getElementsAtEventForMode(e,'nearest',{intersect:true},true);p.length?dim(chart,p[0].datasetIndex):reset(chart);});
    ctx.canvas.addEventListener('mouseleave',()=>reset(chart));
    return;
  }
  const ds=Object.entries(vd.d).filter(([ep])=>!hidden.has(ep)).map(([ep,vals])=>({label:ep,data:vals,borderColor:C[ep],backgroundColor:'transparent',borderWidth:ep==='2026'?2.8:1.5,borderDash:D[ep],pointRadius:ep==='2026'?3:1.5,pointHoverRadius:8,pointHoverBackgroundColor:C[ep],pointHoverBorderColor:'#fff',pointHoverBorderWidth:2,tension:0.35,spanGaps:false}));
  chart=new Chart(ctx,{type:'line',data:{labels:vd.lb,datasets:ds},options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'nearest',intersect:true},plugins:{legend:{display:false},tooltip:{mode:'nearest',intersect:true,callbacks:{title:i=>L[i[0].dataset.label]+' · '+vd.lb[i[0].dataIndex],label:i=>{const y=i.parsed.y;return y==null?null:'  '+vd.yt(y);},labelColor:i=>({borderColor:C[i.dataset.label],backgroundColor:C[i.dataset.label],borderRadius:2})}}},scales:{x:{title:{display:true,text:vd.xl,color:'#888',font:{size:11}},grid:{color:'rgba(128,128,128,.1)'},ticks:{color:'#888',font:{size:11}}},y:{title:{display:true,text:vd.yl,color:'#888',font:{size:11}},grid:{color:'rgba(128,128,128,.1)'},ticks:{color:'#888',font:{size:11},callback:vd.yt}}}}});
  ctx.canvas.addEventListener('mousemove',e=>{if(!chart)return;const p=chart.getElementsAtEventForMode(e,'nearest',{intersect:true},true);p.length?dim(chart,p[0].datasetIndex):reset(chart);});
  ctx.canvas.addEventListener('mouseleave',()=>{if(chart)reset(chart);});
}

buildLeg();
setTimeout(()=>rc('oil'),150);
</script>
</body>
</html>
"""


def render():
    st.markdown("### Dalio historical overlay")
    st.caption(
        "Interactive. Click legend to toggle episodes. "
        "Hover directly on a line to see values — tooltip only shows the hovered episode."
    )
    components.html(DALIO_HTML, height=680, scrolling=False)
