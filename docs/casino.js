// Casino layer: slot-reel hero, "Call it" card game (GM's bottom 10), "Pull the lever" hit-rate simulator.
(function(){
const RM=matchMedia('(prefers-reduced-motion: reduce)').matches;
const SYM=['♠','♥','♦','♣','7','★','BAR','♛'];
// ---------- 1. Slot reels in the hero ----------
const FINAL=['LUCK','LOCATION','LEAK'],H=66,N=22;
function buildReels(){const box=$('#slots');if(!box)return;
 box.innerHTML=FINAL.map((w,i)=>`<div class="reel" aria-hidden="true"><div class="strip" id="strip${i}">${Array.from({length:N},(_,k)=>`<div class="sym${k===N-1?' fin':''}">${k===N-1?w:SYM[(k*3+i*5)%SYM.length]}</div>`).join('')}</div></div>`).join('')+
  `<button class="lever" id="lever" aria-label="Spin the reels"><span class="knob"></span><span class="arm"></span></button><p class="sr" id="slotsTxt" aria-live="polite"></p>`;
 $('#lever').onclick=spin;}
function spin(){const strips=[0,1,2].map(i=>document.getElementById('strip'+i));if(!strips[0])return;
 $('#lever').classList.add('pulled');setTimeout(()=>$('#lever').classList.remove('pulled'),500);
 document.querySelectorAll('.reel').forEach(r=>r.classList.remove('won'));
 strips.forEach((s,i)=>{s.style.transition='none';s.style.transform='translateY(0)';s.offsetHeight;
  const d=RM?0:1.1+i*0.45;s.style.transition=`transform ${d}s cubic-bezier(.15,.85,.25,1.04)`;s.style.transform=`translateY(${-(N-1)*H}px)`;
  setTimeout(()=>s.parentElement.classList.add('won'),d*1000)});
 setTimeout(()=>{$('#slotsTxt').textContent='The reels land on luck, location and leak: all three are at work on this floor.'},RM?0:2100);}
// ---------- 2. "Call it" card game ----------
const OPTS=[['luck','🍀 Luck'],['location','📍 Location'],['leak','🚨 Leak'],['new','🆕 Too new']];
let G={deck:[],i:0,score:0,answered:false};
function keysOf(r){const k=new Set(),t=r.tags.map(x=>x[1]);if(t.some(x=>x.startsWith('Hit-rate'))||r.z<=-3)k.add('leak');if(r.days<90)k.add('new');if(t.includes('Location'))k.add('location');if(r.z<=-2&&!k.has('leak'))k.add('luck');if(!k.size)k.add('luck');return k}
function primary(k){return ['leak','new','location','luck'].find(x=>k.has(x))}
function explain(r,k){const zone=D.zones[r.zone],b=[];
 if(k.has('leak'))b.push(`<b>Leak.</b> It pays on <b>${fmt(r.hrate*100,1)}%</b> of spins vs <b>${fmt(r.hp*100,1)}%</b> configured (hit-rate z <b>${fmt(r.hz,0)}</b>), and payouts are beyond luck (z ${fmt(r.z,1)}). Inspect it.`);
 if(k.has('new'))b.push(`<b>Too new to judge.</b> Only <b>${r.days} days</b> on the floor, so its six-month total is small by construction.`);
 if(k.has('location'))b.push(`<b>Location.</b> It sits in <b>${zone}</b>, where a machine earns about ${usd(r.zmed)} of theo a day; its own play is <b>${fmt(r.cirel*100,0)}%</b> of the zone median, so it draws normal play for where it is.`);
 if(r.rtp>=0.95)b.push(`Also a <b>5%-hold game</b>: it earns less per dollar played by design.`);
 if(k.has('luck')&&!k.has('leak'))b.push(`<b>Luck.</b> Luck score ${fmt(r.z,2)}: inside what pure chance produces.`);
 return b.join('<br>')}
function deal(){const bottom=R.slice().sort((a,b)=>a.hw-b.hw).slice(0,10);G={deck:bottom,i:0,score:0,answered:false};drawCard()}
function drawCard(){const box=$('#callit_game');if(!box)return;
 if(G.i>=G.deck.length){const pct=G.score/G.deck.length;
  box.innerHTML=`<div class="cfinal"><div class="chipbig">${G.score}<small>/${G.deck.length}</small></div><h3>${pct>=0.8?'Sharp eye. You read the floor like an analyst.':pct>=0.5?'Not bad. The data tells the rest.':'Tough table. That is why the GM needs this dashboard.'}</h3>
   <p>The GM would have replaced all ten for <b>$33,800</b>. None of them draws weak play for its zone, nine sit in Back Forty, and one is leaking. Replacing them treats a location and inspection problem as a machine problem.</p>
   <div class="cta2"><button class="btn primary" id="cg_again">Deal again</button><button class="btn" data-go="leakt">See the leak evidence →</button><button class="btn" data-go="plant">See the plan →</button></div></div>`;
  $('#cg_again').onclick=deal;if(pct>=0.8)burst($('#callit_game'));return}
 const r=G.deck[G.i],k=keysOf(r);G.answered=false;
 box.innerHTML=`<div class="cgrow"><div class="pcard" id="pcard"><div class="pface front">
   <div class="pc-top"><span class="suit">♠</span><span>#${G.i+1} lowest earner</span></div>
   <div class="pc-id">${r.id}</div><div class="pc-sub">${r.theme} · ${r.mf}</div>
   <div class="pc-stats"><div><b>${usd(r.hw)}</b><span>house win, 6 months</span></div><div><b>${D.zones[r.zone]}</b><span>zone · bank ${r.bank}</span></div><div><b>${r.days}</b><span>days on floor</span></div><div><b>${fmt((1-r.rtp)*100,0)}%</b><span>configured hold</span></div></div>
   <div class="pc-q">Why did it earn so little?</div></div>
  <div class="pface back"><div class="pc-top"><span class="suit red">♦</span><span>the evidence</span></div><div class="verdict2" id="cg_v"></div><div class="pc-exp">${explain(r,k)}</div>
   <div class="pc-mini"><span>luck z <b>${fmt(r.z,2)}</b></span><span>hit-rate z <b>${fmt(r.hz,1)}</b></span><span>play vs zone <b>${fmt(r.cirel*100,0)}%</b></span></div></div></div>
  <div class="cgside"><div class="cgprog">${G.deck.map((_,j)=>`<i class="${j<G.i?'done':j===G.i?'now':''}"></i>`).join('')}</div>
   <p class="cgscore">Score <b>${G.score}</b> / ${G.i}</p><p class="cghint">Call the main reason this machine is on the GM's list.</p>
   <div class="cgopts">${OPTS.map(([v,l])=>`<button class="optb" data-v="${v}">${l}</button>`).join('')}</div>
   <div class="cgnext"><button class="btn" id="cg_profile">Open full profile</button><button class="btn primary" id="cg_next" disabled>Next card →</button></div></div></div>`;
 box.querySelectorAll('.optb').forEach(b=>b.onclick=()=>{if(G.answered)return;G.answered=true;const ok=k.has(b.dataset.v);if(ok)G.score++;
  box.querySelectorAll('.optb').forEach(x=>{x.disabled=true;if(k.has(x.dataset.v))x.classList.add('right');else if(x===b)x.classList.add('wrong')});
  $('#cg_v').innerHTML=(ok?'<span class="ok">✓ Good call</span>':'<span class="bad">✗ Not quite</span>')+` · main reason: <b>${OPTS.find(o=>o[0]===primary(k))[1]}</b>`;
  $('#pcard').classList.add('flip');$('#cg_next').disabled=false;$('.cgscore').innerHTML=`Score <b>${G.score}</b> / ${G.i+1}`;$('#cg_next').focus()});
 $('#cg_next').onclick=()=>{G.i++;drawCard()};$('#cg_profile').onclick=()=>openDrawer(r.id);}
// ---------- 3. Pull the lever: fair machine vs M-1158 ----------
let L=null;
function leverInit(){const m=R.find(r=>r.id==='M-1158');if(!m)return;const p0=m.hp,p1=m.hi/m.sp;
 L={p0,p1,n:0,h0:0,h1:0,x:[0],z0:[0],z1:[0],cross:null,timer:null};
 $('#lv_p0').textContent=fmt(p0*100,1)+'%';$('#lv_p1').textContent=fmt(p1*100,1)+'%';
 $('#lv_theory').textContent=fmt(Math.ceil((5*Math.sqrt(p0*(1-p0))/(p1-p0))**2));leverDraw();leverStats();}
const zf=(h,n,p)=>n?(h-p*n)/Math.sqrt(p*(1-p)*n):0;
function pull(k){for(let i=0;i<k;i++){L.n++;const a=Math.random()<L.p0,b=Math.random()<L.p1;L.h0+=a;L.h1+=b;
  if(L.n%Math.max(1,Math.floor(L.n/400))===0){L.x.push(L.n);L.z0.push(zf(L.h0,L.n,L.p0));L.z1.push(zf(L.h1,L.n,L.p0))}
  if(!L.cross&&zf(L.h1,L.n,L.p0)>=5)L.cross=L.n;}
 L.last=[Math.random()<L.p0,Math.random()<L.p1];}
function reelHtml(win){const s=win?Array(3).fill(SYM[5]):[0,1,2].map(()=>SYM[Math.floor(Math.random()*SYM.length)]);if(!win&&s[0]===s[1]&&s[1]===s[2])s[2]=s[2]==='7'?'♣':'7';
 return s.map(x=>`<span class="${win?'w':''}">${x}</span>`).join('')}
function leverStats(){const s=[['fair',L.h0,L.p0],['leak',L.h1,L.p0]];
 s.forEach(([id,h,p])=>{$(`#lv_${id}_n`).textContent=fmt(L.n);$(`#lv_${id}_r`).textContent=L.n?fmt(h/L.n*100,1)+'%':'–';const z=zf(h,L.n,p);$(`#lv_${id}_z`).textContent=(z>0?'+':'')+fmt(z,1);
  $(`#lv_${id}_z`).className=Math.abs(z)>=5?'bad':''});
 if(L.last){$('#lv_fair_reel').innerHTML=reelHtml(L.last[0]);$('#lv_leak_reel').innerHTML=reelHtml(L.last[1])}
 $('#lv_msg').innerHTML=L.cross?`🚨 <b>Alarm.</b> M-1158 crossed z = +5 after <b>${fmt(L.cross)}</b> spins. The real hourly monitor in Tiger Data fired after <b>1,276</b> spins on January 1.`:
  L.n?`After ${fmt(L.n)} spins the gap is ${zf(L.h1,L.n,L.p0)<3?'still easy to blame on luck':'getting hard to explain by luck'}. Keep pulling.`:'Pull the lever to start. Both machines run the same game; only one pays out like its configuration says.';}
function leverDraw(){plot('c_lever',[{type:'scatter',mode:'lines',x:L.x.slice(),y:L.z0.slice(),name:'Fair Desert Gold',line:{color:css('--s1'),width:2},hovertemplate:'%{x:,} spins: z = %{y:.1f}<extra>Fair</extra>'},
  {type:'scatter',mode:'lines',x:L.x.slice(),y:L.z1.slice(),name:'M-1158',line:{color:css('--crit'),width:2.5},hovertemplate:'%{x:,} spins: z = %{y:.1f}<extra>M-1158</extra>'}],
  {datarevision:L.n,xaxis:{title:'Spins',gridcolor:css('--grid'),rangemode:'tozero'},yaxis:{title:'Hit-rate z vs configured 31.5%',gridcolor:css('--grid'),range:[-4,Math.max(8,...L.z1)+1]},
   shapes:[{type:'rect',xref:'paper',x0:0,x1:1,y0:-2,y1:2,fillcolor:css('--s3'),opacity:0.08,line:{width:0}},{type:'line',xref:'paper',x0:0,x1:1,y0:5,y1:5,line:{color:css('--crit'),dash:'dot',width:1.5}}],
   annotations:[{xref:'paper',x:1,y:5,xanchor:'right',yanchor:'bottom',text:'alarm: z ≥ 5',showarrow:false,font:{color:css('--crit'),size:11}},{xref:'paper',x:0.01,y:0,xanchor:'left',yanchor:'bottom',text:'ordinary luck',showarrow:false,font:{size:11,color:css('--good')}}].concat(L.cross?[{x:L.cross,y:5,text:'alarm at '+fmt(L.cross),ax:-50,ay:-35,arrowcolor:css('--crit'),font:{color:css('--text')}}]:[])});}
function auto(target){if(L.timer)return;$('#lever2').classList.add('pulled');
 const step=()=>{const k=Math.max(5,Math.floor(L.n/25));pull(Math.min(k,target-L.n));leverStats();leverDraw();if(L.n<target)L.timer=requestAnimationFrame(step);else{L.timer=null;$('#lever2').classList.remove('pulled');if(L.cross)burst($('#lv_leak'),true)}};
 if(RM){pull(target-L.n);leverStats();leverDraw();$('#lever2').classList.remove('pulled');return}L.timer=requestAnimationFrame(step)}
// ---------- coin burst ----------
function burst(el,alarm){if(RM||!el)return;const r=el.getBoundingClientRect();for(let i=0;i<26;i++){const c=document.createElement('span');c.className='coin'+(alarm?' alarm':'');c.textContent=alarm?'!':'$';
  c.style.left=(r.left+r.width/2)+'px';c.style.top=(r.top+r.height/3)+'px';const a=Math.random()*Math.PI*2,d=80+Math.random()*160;
  c.style.setProperty('--dx',Math.cos(a)*d+'px');c.style.setProperty('--dy',(Math.sin(a)*d-80)+'px');document.body.appendChild(c);setTimeout(()=>c.remove(),1100)}}
// ---------- boot ----------
(function wait(){if(typeof D==='undefined'||!D||!R||!R.length){setTimeout(wait,80);return}
 buildReels();setTimeout(spin,RM?0:500);deal();leverInit();
 $('#lv_1').onclick=()=>{if(L.timer)return;pull(1);leverStats();leverDraw();$('#lever2').classList.add('pulled');setTimeout(()=>$('#lever2').classList.remove('pulled'),300)};
 $('#lv_100').onclick=()=>auto(L.n+100);$('#lv_auto').onclick=()=>auto(Math.max(L.n,0)+3000);$('#lever2').onclick=()=>auto(L.n+300);
 $('#lv_reset').onclick=()=>{if(L.timer){cancelAnimationFrame(L.timer);L.timer=null}leverInit()};
 window.casinoRefresh=()=>{if(L)leverDraw()};})();
})();
