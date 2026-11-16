pdfjsLib.GlobalWorkerOptions.workerSrc="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";
let scale=+(localStorage.getItem('zoom')||1.4);
const $=s=>document.querySelector(s);

class Viewer{
  constructor(title){
    this.el=document.createElement('div');this.el.className='pane';
    this.el.innerHTML=`<h2>${title}</h2><div class="scroll"><p class="empty">Compilando…</p></div>`;
    this.sc=this.el.querySelector('.scroll');this.url=null;this.doc=null;this.token=0;
    this.io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting)this.render(e.target)}),{root:this.sc,rootMargin:'800px'});
  }
  async load(url){
    if(!url){this.sc.innerHTML='<p class="empty">Compilando…</p>';this.url=null;return}
    if(url===this.url)return; this.url=url; const tok=++this.token;
    let doc; try{doc=await pdfjsLib.getDocument({url,isEvalSupported:false}).promise}catch(e){return}
    if(tok!==this.token)return;
    this.doc=doc; await this.layout(tok);
    const ol=await outlineOf(doc); if(tok!==this.token)return;
    this.outline=ol; if(this===tocViewer())renderToc(); computeLado();
  }
  async layout(tok=++this.token){
    const doc=this.doc; if(!doc)return;
    const p1=await doc.getPage(1); const vp=p1.getViewport({scale}); this.ptH=p1.view[3]-p1.view[1];
    const box=document.createElement('div'); const pages=[];
    for(let i=1;i<=doc.numPages;i++){const d=document.createElement('div');d.className='page';d.dataset.i=i;
      d.style.width=vp.width+'px';d.style.height=vp.height+'px';d.innerHTML=`<span class="n">${i}</span>`;box.appendChild(d);pages.push(d)}
    // pinta antes de cambiar lo que está a la vista, para que no parpadee
    const top=this.sc.scrollTop, h=this.sc.clientHeight, ph=vp.height+14;
    const first=Math.max(0,Math.floor(top/ph)-1), last=Math.min(pages.length-1,Math.ceil((top+h)/ph)+1);
    for(let i=first;i<=last;i++) await this.render(pages[i],tok);
    if(tok!==this.token)return;
    this.io.disconnect(); this.sc.replaceChildren(box); this.sc.scrollTop=top;
    pages.forEach(p=>this.io.observe(p));
  }
  async render(div,tok=this.token){
    if(div.dataset.done||!this.doc)return; div.dataset.done=1;
    const page=await this.doc.getPage(+div.dataset.i); const vp=page.getViewport({scale});
    const dpr=window.devicePixelRatio||1; const c=document.createElement('canvas');
    c.width=Math.floor(vp.width*dpr);c.height=Math.floor(vp.height*dpr);
    await page.render({canvasContext:c.getContext('2d'),viewport:vp,transform:dpr!==1?[dpr,0,0,dpr,0,0]:null}).promise;
    if(!(tok===this.token||!div.isConnected))return;
    div.prepend(c);
    const tl=document.createElement('div');tl.className='textLayer';tl.style.setProperty('--scale-factor',scale);div.appendChild(tl);
    page.getTextContent().then(tc=>pdfjsLib.renderTextLayer({textContentSource:tc,container:tl,viewport:vp,textDivs:[]}).promise)
      .then(()=>bindTextLayer(tl)).catch(()=>{});
    this.drawMarks(div);
  }
}

// ---------- selección de texto
// Puerto del TextLayerBuilder de pdf.js 3.11: un div «endOfContent» detrás del texto que se mueve
// junto al punto donde va la selección. Sin él, al pasar el cursor por el hueco entre renglones el
// navegador estira la selección hasta el final de la página y parpadea.
const textLayers=new Map();
function resetEnd(end,tl){tl.append(end);end.style.width='';end.style.height='';end.classList.remove('active')}
function bindTextLayer(tl){
  const end=document.createElement('div');end.className='endOfContent';tl.append(end);textLayers.set(tl,end);
  tl.addEventListener('mousedown',()=>end.classList.add('active'));
}
(()=>{let down=false, prev=null;
  const resetAll=()=>{for(const [tl,end] of textLayers){if(!tl.isConnected)textLayers.delete(tl);else resetEnd(end,tl)}};
  document.addEventListener('pointerdown',()=>{down=true});
  document.addEventListener('pointerup',()=>{down=false;resetAll()});
  window.addEventListener('blur',()=>{down=false;resetAll()});
  document.addEventListener('keyup',()=>{if(!down)resetAll()});
  document.addEventListener('selectionchange',()=>{
    const sel=document.getSelection(); if(!sel.rangeCount){resetAll();return}
    const range=sel.getRangeAt(0);
    for(const [tl,end] of textLayers){if(!tl.isConnected){textLayers.delete(tl);continue}
      if(range.intersectsNode(tl))end.classList.add('active');else resetEnd(end,tl)}
    const modStart=prev&&(range.compareBoundaryPoints(Range.END_TO_END,prev)===0||range.compareBoundaryPoints(Range.START_TO_END,prev)===0);
    let a=modStart?range.startContainer:range.endContainer; if(a.nodeType===3)a=a.parentNode;
    const tl=a.parentElement?.closest('.textLayer'), end=tl&&textLayers.get(tl);
    if(end&&a.parentElement){end.style.width=tl.style.width;end.style.height=tl.style.height;
      a.parentElement.insertBefore(end,modStart?a:a.nextSibling)}
    prev=range.cloneRange();
  });
})();
// En huecos y márgenes el navegador no sabe a qué texto apunta el cursor: se lleva la selección al
// punto más cercano del renglón que está a esa altura (como en Preview).
function caretNear(tl,x,y){
  let best=null, bd=1e9;
  for(const sp of tl.querySelectorAll('span')){const t=sp.firstChild; if(!t||t.nodeType!==3||!t.length)continue;
    const r=sp.getBoundingClientRect(); if(!r.width)continue;
    const dy=y<r.top?r.top-y:y>r.bottom?y-r.bottom:0, dx=x<r.left?r.left-x:x>r.right?x-r.right:0, d=dy*1000+dx;
    if(d<bd){bd=d;best={sp,t,r}}}
  if(!best)return null; const {t,r}=best;
  if(x<=r.left)return {node:t,off:0}; if(x>=r.right)return {node:t,off:t.length};
  const c=document.caretRangeFromPoint?.(x,(r.top+r.bottom)/2);
  if(c&&c.startContainer===t)return {node:t,off:c.startOffset};
  return {node:t,off:Math.round(t.length*(x-r.left)/r.width)};
}
const layerAt=(x,y)=>{const pg=document.elementsFromPoint(x,y).find(e=>e.classList?.contains('page'));return pg?.querySelector('.textLayer')};
let selDrag=null;
// El arrastre lo maneja el visor completo (si el navegador y el visor se turnan, la selección
// parpadea); doble y triple clic siguen siendo del navegador.
document.addEventListener('mousedown',e=>{selDrag=null; if(e.button!==0||e.detail>1)return;
  const tl=e.target.closest?.('.textLayer'); if(!tl)return;
  const p=caretNear(tl,e.clientX,e.clientY); if(!p)return;
  e.preventDefault(); selDrag={tl,x:e.clientX,y:e.clientY,sc:tl.closest('.scroll')}; textLayers.get(tl)?.classList.add('active');
  const s=getSelection(); if(e.shiftKey&&s.rangeCount)s.extend(p.node,p.off);else s.collapse(p.node,p.off)});
function selExtend(){const d=selDrag; if(!d)return;
  const tl=layerAt(d.x,d.y)||d.tl; d.tl=tl;
  const p=caretNear(tl,d.x,d.y), s=getSelection(); if(p&&s.rangeCount)s.extend(p.node,p.off)}
document.addEventListener('mousemove',e=>{if(!selDrag)return; if(!(e.buttons&1)){selDrag=null;return}
  selDrag.x=e.clientX; selDrag.y=e.clientY; selExtend()});
// arrastrar hasta el borde desplaza (el navegador ya no lo hace porque el arrastre es del visor)
setInterval(()=>{const d=selDrag; if(!d?.sc)return; const r=d.sc.getBoundingClientRect(), m=40;
  const v=d.y>r.bottom-m?d.y-(r.bottom-m):d.y<r.top+m?d.y-(r.top+m):0; if(!v)return;
  d.sc.scrollTop+=Math.max(-40,Math.min(40,v/2)); selExtend()},30);
document.addEventListener('mouseup',()=>{selDrag=null},true);
// El PDF parte el texto en renglones y trae números de página: se limpia al copiar y al citar.
function cleanSel(s){
  return s.split('\n').filter(l=>!/^\s*\d{1,4}\s*$/.test(l)).join('\n')
    .replace(/(\p{L})-\n(?=\p{Ll})/gu,'$1').replace(/\s*\n\s*/g,' ').replace(/[ \t]{2,}/g,' ').trim();
}
document.addEventListener('copy',e=>{const sel=getSelection(); if(!sel.rangeCount)return;
  const n=sel.anchorNode, el=n&&(n.nodeType===1?n:n.parentElement); if(!el?.closest('.textLayer,.page'))return;
  e.clipboardData.setData('text/plain',cleanSel(sel.toString())); e.preventDefault()});

// posición (en px dentro del scroll) de un destino del índice
Viewer.prototype.yOf=function(it){
  const div=it&&it.page&&this.sc.querySelector(`.page[data-i="${it.page}"]`); if(!div)return null;
  return div.offsetTop+(it.top!=null?Math.max(0,(this.ptH-it.top)*scale):0);
};
Viewer.prototype.goto=function(it){const y=this.yOf(it); if(y!=null)this.sc.scrollTop=Math.max(0,y-24)};

let tab='actual', view='marcado', refs=null, st=null, viewers=[], shown='', noSync=0;

// ---------- diferencias visibles en «lado a lado»
// Se compara el texto que realmente sale en cada PDF, palabra por palabra (Myers). Los números
// sueltos (páginas, llamadas a notas) no cuentan: si la paginación se corre llenarían todo de ruido.
const textCache=new Map();
async function pdfWords(doc,url){
  if(textCache.has(url))return textCache.get(url);
  const toks=[], items={}, p1=await doc.getPage(1), view=p1.view;
  for(let p=1;p<=doc.numPages;p++){
    const tc=await (await doc.getPage(p)).getTextContent(); items[p]=tc.items;
    const pt=[], lastOnLine=new Map();
    tc.items.forEach((it,ii)=>{const s=it.str||'', y=Math.round(it.transform[5]);
      for(const m of s.matchAll(/[\p{L}\p{N}]+/gu)){
        const t={w:m[0].normalize('NFKC').toLowerCase(),p,ii,s:m.index,e:m.index+m[0].length,x:it.transform[4]+it.width*(m.index/Math.max(1,s.length))};
        pt.push(t); const prev=lastOnLine.get(y); if(!prev||t.x>prev.x)lastOnLine.set(y,t)}});
    // números al final de un renglón: páginas al pie y en índice/cuadros/figuras
    const drop=new Set([...lastOnLine.values()].filter(t=>/^\d+$/.test(t.w)));
    for(const t of pt)if(!drop.has(t))toks.push(t);
  }
  const r={toks,items,view}; textCache.set(url,r); if(textCache.size>6)textCache.delete(textCache.keys().next().value); return r;
}
function myers(A,B){ // devuelve [borradoEnA, agregadoEnB] como Uint8Array; null si son demasiado distintos
  const n0=A.length,m0=B.length; let pre=0; while(pre<n0&&pre<m0&&A[pre]===B[pre])pre++;
  let suf=0; while(suf<n0-pre&&suf<m0-pre&&A[n0-1-suf]===B[m0-1-suf])suf++;
  const a=A.slice(pre,n0-suf), b=B.slice(pre,m0-suf), n=a.length, m=b.length, max=n+m;
  const del=new Uint8Array(n0), add=new Uint8Array(m0);
  if(!n||!m){for(let i=0;i<n;i++)del[pre+i]=1;for(let j=0;j<m;j++)add[pre+j]=1;return [del,add]}
  const V=new Int32Array(2*max+3), off=max+1, trace=[]; let done=false;
  for(let d=0;d<=max&&!done;d++){
    if(d>6000)return null;
    trace.push(V.slice(off-d-1,off+d+2));
    for(let k=-d;k<=d;k+=2){
      let x=(k===-d||(k!==d&&V[off+k-1]<V[off+k+1]))?V[off+k+1]:V[off+k-1]+1, y=x-k;
      while(x<n&&y<m&&a[x]===b[y]){x++;y++}
      V[off+k]=x; if(x>=n&&y>=m){done=true;break}
    }
  }
  let x=n,y=m;
  for(let d=trace.length-1;d>=0;d--){
    const v=trace[d], g=k=>v[k+d+1], k=x-y;
    const pk=(k===-d||(k!==d&&g(k-1)<g(k+1)))?k+1:k-1, px=g(pk), py=px-pk;
    while(x>px&&y>py){x--;y--}
    if(d>0){if(x===px)add[pre+y-1]=1;else del[pre+x-1]=1}
    x=px;y=py;
  }
  return [del,add];
}
// Myers solo aguanta pocas diferencias (memoria ~D²). Para capítulos reescritos se ancla primero
// con palabras que salen una sola vez en cada lado (patience diff) y Myers corre en los huecos.
function diffTokens(A,B){
  const del=new Uint8Array(A.length), add=new Uint8Array(B.length), stack=[[0,A.length,0,B.length]];
  const markAll=(a0,a1,b0,b1)=>{for(let i=a0;i<a1;i++)del[i]=1;for(let j=b0;j<b1;j++)add[j]=1};
  while(stack.length){
    let [a0,a1,b0,b1]=stack.pop();
    while(a0<a1&&b0<b1&&A[a0]===B[b0]){a0++;b0++}
    while(a0<a1&&b0<b1&&A[a1-1]===B[b1-1]){a1--;b1--}
    if(a0===a1||b0===b1){markAll(a0,a1,b0,b1);continue}
    let anchors=[];
    if((a1-a0)+(b1-b0)>3000){
      const cA=new Map(), cB=new Map();
      for(let i=a0;i<a1;i++){const v=cA.get(A[i]);cA.set(A[i],v===undefined?i:-1)}
      for(let j=b0;j<b1;j++){const v=cB.get(B[j]);cB.set(B[j],v===undefined?j:-1)}
      const pairs=[]; for(let i=a0;i<a1;i++){const pa=cA.get(A[i]),pb=cB.get(A[i]); if(pa===i&&pb!==undefined&&pb>=0)pairs.push([i,pb])}
      // subsecuencia creciente más larga en posición de B
      const tails=[], prev=new Int32Array(pairs.length).fill(-1), tIdx=[];
      pairs.forEach((p,k)=>{let lo=0,hi=tails.length; while(lo<hi){const m=(lo+hi)>>1; if(tails[m]<p[1])lo=m+1;else hi=m}
        tails[lo]=p[1]; tIdx[lo]=k; prev[k]=lo?tIdx[lo-1]:-1});
      for(let k=tails.length?tIdx[tails.length-1]:-1;k>=0;k=prev[k])anchors.push(pairs[k]);
      anchors.reverse();
    }
    if(anchors.length){
      let pa=a0,pb=b0;
      for(const [i,j] of anchors){stack.push([pa,i,pb,j]);pa=i+1;pb=j+1}
      stack.push([pa,a1,pb,b1]); continue;
    }
    const r=myers(A.slice(a0,a1),B.slice(b0,b1));
    if(!r){markAll(a0,a1,b0,b1);continue}
    r[0].forEach((v,k)=>{if(v)del[a0+k]=1}); r[1].forEach((v,k)=>{if(v)add[b0+k]=1});
  }
  return [del,add];
}
let lado={key:'',hunks:[],cur:-1};
async function computeLado(){
  const [L,R]=viewers; if(view!=='lado'||tab!=='comparar'||!L?.doc||!R?.doc)return;
  const key=L.url+'|'+R.url; if(key===lado.key)return; lado.key=key; $('#navc').textContent='comparando…';
  const [a,b]=await Promise.all([pdfWords(L.doc,L.url),pdfWords(R.doc,R.url)]); if(lado.key!==key)return;
  const ids=new Map(), id=w=>{let v=ids.get(w);if(v===undefined){v=ids.size;ids.set(w,v)}return v};
  const res=diffTokens(a.toks.map(t=>id(t.w)),b.toks.map(t=>id(t.w)));
  if(!res){$('#navc').textContent='demasiados cambios';return}
  const [del,add]=res, hA=new Int32Array(a.toks.length).fill(-1), hB=new Int32Array(b.toks.length).fill(-1), hunks=[];
  let i=0,j=0;
  while(i<a.toks.length||j<b.toks.length){
    if((i<a.toks.length&&del[i])||(j<b.toks.length&&add[j])){
      // un cambio = borrados/agregados seguidos, uniendo los que quedan a ≤3 palabras iguales
      const h={a:i,b:j}; let gap=0;
      while(i<a.toks.length||j<b.toks.length){
        if(i<a.toks.length&&del[i]){hA[i++]=hunks.length;gap=0}
        else if(j<b.toks.length&&add[j]){hB[j++]=hunks.length;gap=0}
        else{let k=0;while(k<4&&i+k<a.toks.length&&j+k<b.toks.length&&!del[i+k]&&!add[j+k])k++;
          if(k<4&&(del[i+k]||add[j+k])){i+=k;j+=k}else break}
      }
      hunks.push(h);
    }else{i++;j++}
  }
  // bloques que solo se movieron (p. ej. una figura que LaTeX reacomodó): mismo texto borrado en
  // un lugar y agregado en otro. No cuentan como cambio.
  const txt=hunks.map(()=>({d:[],a:[]}));
  a.toks.forEach((t,k)=>{if(hA[k]>=0)txt[hA[k]].d.push(t.w)}); b.toks.forEach((t,k)=>{if(hB[k]>=0)txt[hB[k]].a.push(t.w)});
  const pureDel=new Map(), moved=new Set();
  txt.forEach((t,h)=>{if(t.d.length>=3&&!t.a.length){const k=t.d.join(' ');(pureDel.get(k)||pureDel.set(k,[]).get(k)).push(h)}});
  // igual, o uno contenido en el otro (el bloque movido a veces arrastra una palabra vecina)
  const wrap=s=>' '+s+' ';
  txt.forEach((t,h)=>{if(t.a.length<3||t.d.length)return; const A=t.a.join(' ');
    for(const [D,l] of pureDel){if(!l.length)continue;
      if(D===A||wrap(D).includes(wrap(A))||wrap(A).includes(wrap(D))){moved.add(l.shift());moved.add(h);break}}});
  const remap=new Int32Array(hunks.length).fill(-1); let nh=0; hunks.forEach((h,k)=>{if(!moved.has(k))remap[k]=nh++});
  for(let k=0;k<hA.length;k++)if(hA[k]>=0)hA[k]=remap[hA[k]];
  for(let k=0;k<hB.length;k++)if(hB[k]>=0)hB[k]=remap[hB[k]];
  const kept=hunks.filter((h,k)=>!moved.has(k)); hunks.length=0; hunks.push(...kept);
  const marks=(side,hs,cls)=>{const out={}; let last=null;
    side.toks.forEach((t,k)=>{const h=hs[k]; if(h<0){last=null;return}
      if(last&&last.p===t.p&&last.ii===t.ii&&last.h===h){last.e=t.e;return}
      last={p:t.p,ii:t.ii,s:t.s,e:t.e,h,cls}; (out[t.p]=out[t.p]||[]).push(last)});
    return {byPage:out,items:side.items,view:side.view}};
  L.marks=marks(a,hA,'del'); R.marks=marks(b,hB,'add');
  hunks.forEach(h=>{h.pa=a.toks[Math.min(h.a,a.toks.length-1)]; h.pb=b.toks[Math.min(h.b,b.toks.length-1)]});
  lado.hunks=hunks; lado.sides=[a,b]; lado.cur=-1;
  [L,R].forEach(v=>v.sc.querySelectorAll('.page[data-done]').forEach(d=>v.drawMarks(d)));
  navLabel();
}
Viewer.prototype.drawMarks=function(div){
  div.querySelectorAll('.hl').forEach(e=>e.remove());
  const M=this.marks; if(!M||view!=='lado')return; const list=M.byPage[+div.dataset.i]; if(!list)return;
  const [vx,,,vy]=M.view;
  for(const r of list){const it=M.items[r.p][r.ii]; if(!it)continue; const t=it.transform, len=Math.max(1,it.str.length);
    const fh=Math.hypot(t[2],t[3])||it.height||10, x0=t[4]+it.width*r.s/len, x1=t[4]+it.width*r.e/len;
    const el=document.createElement('div'); el.className=`hl ${r.cls}${r.h===lado.cur?' cur':''}`; el.dataset.h=r.h;
    Object.assign(el.style,{left:(x0-vx)*scale-1+'px',top:(vy-t[5]-fh*.9)*scale+'px',width:(x1-x0)*scale+2+'px',height:fh*1.12*scale+'px'});
    div.appendChild(el)}
};
function navLabel(){const n=lado.hunks.length;
  $('#navc').textContent=n?(lado.cur<0?`${n} cambio${n>1?'s':''}`:`${lado.cur+1} / ${n}`):'sin cambios'}
function navGo(dir){
  const n=lado.hunks.length; if(!n||viewers.length<2)return;
  lado.cur=lado.cur<0?(dir>0?0:n-1):(lado.cur+dir+n)%n; const h=lado.hunks[lado.cur];
  noSync=Date.now()+500;
  viewers.forEach((v,s)=>{const t=s?h.pb:h.pa; if(!t)return; const it=lado.sides[s].items[t.p][t.ii];
    v.goto({page:t.p,top:it.transform[5]+Math.hypot(it.transform[2],it.transform[3])*3})});
  document.querySelectorAll('.hl').forEach(e=>e.classList.toggle('cur',+e.dataset.h===lado.cur));
  navLabel();
}
const setHl=on=>{$('#hlon').checked=on;document.body.classList.toggle('nohl',!on);try{localStorage.setItem('hl',on?'1':'0')}catch(e){}};
$('#hlon').onchange=e=>setHl(e.target.checked); try{setHl(localStorage.getItem('hl')!=='0')}catch(e){}
$('#navn').onclick=()=>navGo(1); $('#navp').onclick=()=>navGo(-1);
document.addEventListener('keydown',e=>{if(view!=='lado'||tab!=='comparar'||e.target.closest('input,textarea'))return;
  if(e.key==='c')setHl(!$('#hlon').checked);
  if(e.key==='j')navGo(1); if(e.key==='k')navGo(-1)});
async function outlineOf(doc){
  const out=[]; let ol=null; try{ol=await doc.getOutline()}catch(e){}
  async function walk(items,level){for(const it of items||[]){
    let page=null,top=null;
    try{let d=it.dest; if(typeof d==='string')d=await doc.getDestination(d);
      if(Array.isArray(d)){page=(typeof d[0]==='object'?await doc.getPageIndex(d[0]):d[0])+1;
        const k=d[1]&&d[1].name; if(k==='XYZ'&&typeof d[3]==='number')top=d[3]; else if((k==='FitH'||k==='FitBH')&&typeof d[2]==='number')top=d[2];}}catch(e){}
    out.push({title:(it.title||'').replace(/\s+/g,' ').trim(),level,page,top}); await walk(it.items,level+1)}}
  await walk(ol,0); return out;
}
// el índice sigue al PDF principal: el actual, el de cambios marcados o el derecho en lado a lado
const tocViewer=()=>view==='lado'&&tab==='comparar'?viewers[1]:viewers[0];
function renderToc(){
  const v=tocViewer(), el=$('#tocl');
  if(tab==='comparar'&&view==='fuente'){el.innerHTML='<p class="empty">El índice es para las vistas PDF.</p>';return}
  if(!v||!v.outline){el.innerHTML='<p class="empty">Cargando…</p>';return}
  if(!v.outline.length){el.innerHTML='<p class="empty">Este PDF no trae índice.</p>';return}
  // cambios por sección: propios (punto lleno) o solo en subsecciones (aro)
  const own=v.outline.map(it=>chg?.sections[tkey(it.title)]||0), tot=own.slice();
  for(let i=v.outline.length-1;i>=0;i--)for(let j=i+1;j<v.outline.length&&v.outline[j].level>v.outline[i].level;j++)if(v.outline[j].level===v.outline[i].level+1)tot[i]+=tot[j];
  const n=Object.values(chg?.sections||{}).reduce((a,b)=>a+b,0)+(chg?.outside||0);
  let h='';
  if(chg){h+=n?`<div class="chgleg">${n} cambio${n>1?'s':''} ${tab==='comparar'?`desde ${esc(label(cmpBase))}`:'sin commit'}</div>`
            :`<div class="chgleg" style="opacity:.6">${tab==='comparar'?'sin cambios en las fuentes':'sin cambios sin commit'}</div>`;
          if(chg.outside)h+=`<div class="chgleg">${chg.outside} fuera del índice (portada, resumen…)</div>`}
  h+=v.outline.map((it,i)=>{const c=tot[i]?`<span class="chg${own[i]?'':' sub'}" title="${own[i]?own[i]+' cambio(s) aquí':''}${own[i]&&tot[i]>own[i]?' · ':''}${tot[i]>own[i]?(tot[i]-own[i])+' en subsecciones':''}">${tot[i]}</span>`:'';
    return `<a class="l${Math.min(it.level,3)}" data-i="${i}" title="${esc(it.title)} · p. ${it.page}"><span class="tt">${esc(it.title)}</span>${c}</a>`}).join('');
  el.innerHTML=h;
  hlToc();
}
const tkey=t=>((t||'').normalize('NFKC').toLowerCase().match(/[\p{L}\p{N}_]+/gu)||[]).join(' ');
let chg=null, chgKey='';
async function loadChanges(force){
  const b=tab==='comparar'?cmpBase:'HEAD', t=tab==='comparar'?cmpTarget:'WORKTREE';
  if(!b)return; const key=b+'|'+t+'|'+(st?.actual.v||0)+'|'+(refs?.head||'');
  if(key===chgKey&&!force)return; chgKey=key;
  try{chg=await (await fetch(`/api/changes?base=${b}&target=${t}`)).json(); if(chg.error)chg=null}catch(e){chg=null}
  renderToc();
}
let hlPending=false;
function hlToc(){
  const v=tocViewer(); if(!v||!v.outline)return;
  const y=v.sc.scrollTop+80; let cur=-1;
  v.outline.forEach((it,i)=>{const yy=v.yOf(it); if(yy!=null&&yy<=y)cur=i});
  document.querySelectorAll('#tocl a').forEach((a,i)=>a.classList.toggle('on',i===cur));
  const on=document.querySelector('#tocl a.on'); if(on)on.scrollIntoView({block:'nearest'});
}
// mismo título y misma aparición en el otro PDF (lado a lado); si no está, misma posición en la lista
function matchItem(list,it,src){
  if(!list)return null; const nth=src.slice(0,src.indexOf(it)).filter(x=>x.title===it.title).length;
  return list.filter(x=>x.title===it.title)[nth]||list[src.indexOf(it)]||null;
}
$('#tocl').onclick=e=>{const a=e.target.closest('a'); if(!a)return; const v=tocViewer(); const it=v.outline[+a.dataset.i];
  noSync=Date.now()+500; viewers.forEach(w=>w.goto(w===v?it:matchItem(w.outline,it,v.outline)));};
const setToc=open=>{document.body.classList.toggle('notoc',!open);try{localStorage.setItem('toc',open?'1':'0')}catch(e){}};
$('#tocbtn').onclick=()=>setToc(document.body.classList.contains('notoc'));
try{setToc(localStorage.getItem('toc')!=='0')}catch(e){}

function link(a,b){let lock=false;const f=(x,y)=>x.sc.addEventListener('scroll',()=>{
  if(lock||Date.now()<noSync||!$('#sync').checked)return;lock=true;
  const r=x.sc.scrollTop/Math.max(1,x.sc.scrollHeight-x.sc.clientHeight);y.sc.scrollTop=r*(y.sc.scrollHeight-y.sc.clientHeight);
  requestAnimationFrame(()=>lock=false)});f(a,b);f(b,a)}

let cmpBase=null, cmpTarget='WORKTREE';
function fmtDate(s){const d=new Date(s); if(isNaN(d))return s;
  const o={day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'}; if(d.getFullYear()!==new Date().getFullYear())o.year='numeric';
  return d.toLocaleString('es-MX',o)}
const label=sha=>sha==='WORKTREE'?'ahora':(()=>{const r=refs?.refs.find(x=>x.sha===sha);return r?fmtDate(r.date):(sha||'').slice(0,7)})();
function setup(){
  const key=[tab,view,cmpBase,cmpTarget].join('|'); if(key===shown)return; shown=key;
  const m=$('#main'); m.replaceChildren(); viewers=[];
  $('#bar2').style.display=tab==='comparar'?'flex':'none';
  $('#synclbl').style.display=view==='lado'?'':'none'; $('#nav').style.display=view==='lado'?'':'none'; $('#hllbl').style.display=view==='lado'?'':'none'; lado={key:'',hunks:[],cur:-1};
  $('#leg').style.display=view==='marcado'?'':'none';
  $('#cmptitle').textContent=tab==='comparar'?`Cambios desde ${label(cmpBase)} hasta ${label(cmpTarget)}`:'';
  const cap=s=>s.charAt(0).toUpperCase()+s.slice(1);
  if(tab==='actual'){viewers=[new Viewer('Ahora')]}
  else if(view==='marcado'){viewers=[new Viewer('Cambios marcados')]}
  else if(view==='lado'){viewers=[new Viewer(cap(label(cmpBase))),new Viewer(cap(label(cmpTarget)))];link(...viewers)}
  else {const d=document.createElement('div');d.id='src';d.innerHTML='<p class="empty">Cargando…</p>';m.appendChild(d);loadSrc();}
  viewers.forEach(v=>{m.appendChild(v.el);v.sc.addEventListener('scroll',()=>{
    if(v!==tocViewer()||hlPending)return;hlPending=true;requestAnimationFrame(()=>{hlPending=false;hlToc()})})});
  renderToc(); refresh(); loadChanges();
}
async function loadSrc(){
  if(!cmpBase)return;
  const r=await fetch(`/api/source-diff?base=${cmpBase}&target=${cmpTarget}`); const el=$('#src'); if(el) el.innerHTML=await r.text();
}
function pillOf(s){const p=$('#pill');
  if(!s){p.className='pill';p.textContent='…';return}
  if(s.building){p.className='pill run';p.textContent='compilando…'}
  else if(s.ok===false){p.className='pill bad';p.textContent='error de compilación'}
  else if(s.ok){p.className='pill ok';p.textContent='compilado'}
  else{p.className='pill';p.textContent='en cola'}
  $('#took').textContent=s.ok&&!s.building&&s.took?`${s.took}s`:'';
  const e=$('#err'); e.hidden=!(s.ok===false&&!s.building); e.textContent=s.error||'';
}
function refresh(){
  if(!st)return; const a=st.actual, c=st.compare;
  if(tab==='actual'){pillOf(a); viewers[0]?.load(a.v&&a.ok!==null&&(a.ok||a.v>1)?`/pdf/actual.pdf?v=${a.v}`:null);
    if(a.ok===false&&viewers[0]&&!viewers[0].url) viewers[0].sc.innerHTML='<p class="empty">No compila todavía. Mira el error arriba.</p>';
    $('#open').href='/pdf/actual.pdf';return}
  if(!c.base){pillOf(null);return}
  const tgtPdf=c.target==='WORKTREE'?{s:a,u:`/pdf/actual.pdf?v=${a.v}`}:{s:c.target_pdf,u:`/pdf/ref-${c.target}.pdf?v=${c.target_pdf.v}`};
  if(view==='marcado'){pillOf(c.diff);viewers[0]?.load(c.diff.ok?`/pdf/diff.pdf?v=${c.diff.v}`:null);$('#open').href='/pdf/diff.pdf';
    if(c.diff.ok&&c.diff_mode&&c.diff_mode!=='completo')$('#took').textContent+=` · modo ${c.diff_mode}`}
  else if(view==='lado'){const bs=c.base_pdf; pillOf(bs.building||!bs.ok?bs:tgtPdf.s);
    viewers[0]?.load(bs.ok?`/pdf/ref-${c.base}.pdf?v=${bs.v}`:null);viewers[1]?.load(tgtPdf.s.ok?tgtPdf.u:null);
    $('#open').href=`/pdf/ref-${c.base}.pdf`}
  else pillOf({ok:true});
}
async function poll(){
  try{const r=await fetch('/api/status');const prev=st?JSON.stringify([st.actual.v,st.compare.diff.v]):'';st=await r.json();
    refresh(); loadChanges(); if(tab==='comparar'&&view==='fuente'&&prev&&prev!==JSON.stringify([st.actual.v,st.compare.diff.v]))loadSrc();
  }catch(e){$('#pill').className='pill bad';$('#pill').textContent='servidor apagado'}
  setTimeout(poll,1000);
}
// ---------- versiones
async function loadRefs(){
  try{refs=await (await fetch('/api/refs')).json()}catch(e){return}
  renderVersions();
}
function renderVersions(){
  if(!refs)return;
  const cmp=tab==='comparar', n=refs.dirty.length;
  const nowTag=!cmp?'viendo':(cmpTarget==='WORKTREE'?'hasta':'');
  let h='<div class="hint">Clic en una versión: ves lo que cambió desde ella hasta ahora. ⌥clic en otra: comparas esas dos versiones.</div>';
  h+=`<div class="ver now${nowTag?' tgt':''}" data-sha="WORKTREE"><span class="dot"></span>
    <div class="d">Ahora${nowTag?`<span class="tag">${nowTag}</span>`:''}</div><div class="s">Lo que tienes en disco</div>
    <div class="m">${n?`${n} archivo${n>1?'s':''} sin commit`:'sin cambios sin commit'} · rama ${esc(refs.branch)}</div></div>`;
  h+=refs.refs.map(r=>{const b=cmp&&r.sha===cmpBase, t=cmp&&r.sha===cmpTarget;
    return `<div class="ver${b?' base':''}${t?' tgt':''}" data-sha="${r.sha}" title="${esc(r.subject)}"><span class="dot"></span>
      <div class="d">${esc(fmtDate(r.date))}${b?'<span class="tag">desde</span>':''}${t?'<span class="tag">hasta</span>':''}</div>
      <div class="s">${esc(r.subject)}</div><div class="m">${r.short} · ${r.files} archivo${r.files===1?'':'s'}</div></div>`}).join('');
  if(!refs.refs.length)h+='<p class="empty">Todavía no hay commits de la tesis.</p>';
  $('#verl').innerHTML=h;
}
function goActual(){tab='actual';setup();renderVersions()}
async function compare(){
  tab='comparar';
  const r=await fetch('/api/compare',{method:'POST',body:JSON.stringify({base:cmpBase,target:cmpTarget})});
  if(!r.ok){alert((await r.json()).error);return}
  try{st=await (await fetch('/api/status')).json()}catch(e){}
  setup();renderVersions();if(view==='fuente')loadSrc();
}
$('#verl').onclick=e=>{const v=e.target.closest('.ver'); if(!v)return; const sha=v.dataset.sha;
  if(e.altKey&&tab==='comparar'){if(sha!==cmpBase){cmpTarget=sha;compare()}return}
  if(sha==='WORKTREE'){goActual();return}
  cmpBase=sha; if(cmpTarget===sha)cmpTarget='WORKTREE'; compare();};
$('#back').onclick=goActual;
const setSide=s=>{document.querySelectorAll('.stabs button').forEach(b=>b.classList.toggle('on',b.dataset.s===s));
  $('#tocl').hidden=s!=='toc';$('#verl').hidden=s!=='ver';try{localStorage.setItem('side',s)}catch(e){}if(s==='ver')loadRefs()};
document.querySelectorAll('.stabs button').forEach(b=>b.onclick=()=>setSide(b.dataset.s));
try{setSide(localStorage.getItem('side')||'toc')}catch(e){setSide('toc')}
document.querySelectorAll('#views button').forEach(b=>b.onclick=()=>{
  document.querySelectorAll('#views button').forEach(x=>x.classList.toggle('on',x===b));view=b.dataset.v;setup()});
$('#rebuild').onclick=()=>fetch('/api/build',{method:'POST'});
const zoom=f=>{scale=Math.min(3,Math.max(.6,scale*f));localStorage.setItem('zoom',scale);viewers.forEach(v=>v.layout())};
$('#zin').onclick=()=>zoom(1.15);$('#zout').onclick=()=>zoom(1/1.15);
setInterval(loadRefs,15000);loadRefs();
// ---------- comentarios
const esc=s=>s.replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
let pending=null, comments=[];
function toast(m){const t=$('#toast');t.textContent=m;t.style.display='block';clearTimeout(t._h);t._h=setTimeout(()=>t.style.display='none',4000)}
document.addEventListener('mouseup',e=>{
  if(e.target.closest('#cbtn,#cmodal,#cpanel'))return;
  setTimeout(()=>{const sel=getSelection(),q=cleanSel(sel.toString()),b=$('#cbtn');
    const node=sel.anchorNode&&(sel.anchorNode.nodeType===1?sel.anchorNode:sel.anchorNode.parentElement);
    if(!q||!node||!node.closest('.textLayer')){b.style.display='none';return}
    const r=sel.getRangeAt(0).getBoundingClientRect(), pane=node.closest('.pane');
    pending={quote:q,page:node.closest('.page')?.dataset.i||'',view:pane?.querySelector('h2')?.textContent||''};
    b.style.left=Math.min(innerWidth-120,r.right+6)+'px';b.style.top=Math.min(innerHeight-40,r.bottom+6)+'px';b.style.display='block'},0)});
$('#cbtn').onmousedown=e=>e.preventDefault();
$('#cbtn').onclick=()=>{if(!pending)return;$('#cbtn').style.display='none';$('#cquote').textContent=pending.quote;
  $('#ctext').value='';$('#cmodal').style.display='flex';$('#ctext').focus()};
const closeModal=()=>{$('#cmodal').style.display='none'};
$('#ccancel').onclick=closeModal;
$('#cmodal').onclick=e=>{if(e.target.id==='cmodal')closeModal()};
$('#ctext').onkeydown=e=>{if(e.key==='Escape')closeModal();if(e.key==='Enter'&&(e.metaKey||e.ctrlKey))$('#csave').click()};
$('#csave').onclick=async()=>{const text=$('#ctext').value.trim();if(!text)return;
  const r=await fetch('/api/comments',{method:'POST',body:JSON.stringify({...pending,text})});const j=await r.json();
  if(!r.ok){alert(j.error);return}
  closeModal();getSelection().removeAllRanges();
  toast(j.located?`Guardado en ${j.file}:${j.line}`:`No encontré ese texto en las fuentes; quedó en ${j.file}`);loadComments()};
async function loadComments(){
  try{comments=await (await fetch('/api/comments')).json()}catch(e){return}
  $('#cpanelbtn').textContent=`Comentarios (${comments.length})`;
  $('#clist').innerHTML=comments.length?comments.map((c,i)=>`<div class="cm${c.unplaced?' un':''}">
    <button class="loc" data-i="${i}" data-a="open">${esc(c.file)}:${c.line} ↗</button>
    <div class="q">${esc(c.head)}</div><div class="t">${esc(c.text)}</div>
    <div class="acts"><button class="b" data-i="${i}" data-a="resolve">Resolver</button></div></div>`).join('')
    :'<p class="empty">Sin comentarios. Selecciona texto en un PDF y presiona «Comentar».</p>';
}
$('#clist').onclick=async e=>{const b=e.target.closest('button');if(!b)return;const c=comments[+b.dataset.i];
  if(b.dataset.a==='open'){fetch('/api/open',{method:'POST',body:JSON.stringify(c)});return}
  if(!confirm('¿Borrar este comentario del .tex?'))return;
  const j=await (await fetch('/api/comments/resolve',{method:'POST',body:JSON.stringify(c)})).json();
  if(!j.ok)alert(j.error);loadComments()};
const panel=open=>{$('#cpanel').style.display=open?'flex':'none';document.body.classList.toggle('cp',open)};
$('#cpanelbtn').onclick=()=>{panel($('#cpanel').style.display!=='flex');loadComments()};
$('#cclose').onclick=()=>panel(false);
setInterval(loadComments,4000);loadComments();
setup();poll();
