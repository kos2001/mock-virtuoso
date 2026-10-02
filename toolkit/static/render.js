// Read theme colors at draw time so canvas updates without changing the design.
function canvasColor(name,fallback){return getComputedStyle(document.documentElement).getPropertyValue(name).trim()||fallback;}
window.addEventListener('floor-theme-change',()=>draw());
/* The layout renderer for the agent design floor.
 *
 * Draws rows exactly as `layout_read_geometry` returns them through the bridge:
 * shapes by lpp, instances by their master's shapes under a Cadence orientation
 * transform. A page provides #cv and #lsw, and may define onLayerToggle(layer,
 * visible) to mirror a layer switch into the tool; everything else is here.
 */
const LAYERS = {
  nwell:{c:"#2f6f4f", h:"/"},  diff:{c:"#3fb950", h:"\\"},
  poly:{c:"#f85149", h:"/"},   met1:{c:"#4493f8", h:"\\"},
  met2:{c:"#39c5cf", h:"/"},   met3:{c:"#bc8cff", h:"\\"},
  via:{c:"#e3b341", h:""},     text:{c:"#e6edf3", h:""},
  tap:{c:"#138c57",h:"/"},
  licon1:{c:"#bd7310",h:""},li1:{c:"#2aa9ac",h:"\\"},mcon:{c:"#dc8625",h:""},
  via2:{c:"#d7a324",h:""},via3:{c:"#ca8932",h:""},via4:{c:"#b4823d",h:""},
  met4:{c:"#cf62a3",h:"/"},met5:{c:"#75a14f",h:"\\"},
  nsdm:{c:"#77a879",h:""},psdm:{c:"#b898bd",h:""},boundary:{c:"#73859a",h:""},
};
const vis = Object.fromEntries(Object.keys(LAYERS).map(k=>[k,true]));
let rows=[], masters={}, sel=0, view={x:0,y:0,s:26};

const $=id=>document.getElementById(id);
const cv=$("cv"), ctx=cv.getContext("2d");

function resize(){
  const r=cv.parentElement.getBoundingClientRect(), d=devicePixelRatio||1;
  cv.width=r.width*d; cv.height=r.height*d; ctx.setTransform(d,0,0,d,0,0); draw();
}
addEventListener("resize",resize);

const W=()=>cv.width/(devicePixelRatio||1), H=()=>cv.height/(devicePixelRatio||1);
const sx=x=>(x-view.x)*view.s+W()/2, sy=y=>H()/2-(y-view.y)*view.s;
const wx=px=>(px-W()/2)/view.s+view.x, wy=py=>view.y-(py-H()/2)/view.s;

function hatch(color,dir){
  const c=document.createElement("canvas"); c.width=c.height=8;
  const g=c.getContext("2d"); g.strokeStyle=color; g.lineWidth=1; g.globalAlpha=.85;
  g.beginPath();
  if(dir==="/"){g.moveTo(0,8);g.lineTo(8,0);g.moveTo(-2,2);g.lineTo(2,-2);g.moveTo(6,10);g.lineTo(10,6);}
  else{g.moveTo(0,0);g.lineTo(8,8);g.moveTo(-2,6);g.lineTo(2,10);g.moveTo(6,-2);g.lineTo(10,2);}
  g.stroke(); return ctx.createPattern(c,"repeat");
}
const pat={};
function patternFor(l){const L=LAYERS[l]; if(!L||!L.h) return null;
  if(!pat[l]) pat[l]=hatch(L.c,L.h); return pat[l];}

function grid(){
  const step=view.s>=18?1:view.s>=7?5:10;
  ctx.lineWidth=1;
  for(let gx=Math.floor(wx(0)/step)*step; gx<wx(W()); gx+=step){
    ctx.strokeStyle = Math.abs(gx)<1e-9?canvasColor("--axis","#233043"):canvasColor("--grid","#161d27");
    ctx.beginPath(); ctx.moveTo(sx(gx),0); ctx.lineTo(sx(gx),H()); ctx.stroke();
  }
  for(let gy=Math.floor(wy(H())/step)*step; gy<wy(0); gy+=step){
    ctx.strokeStyle = Math.abs(gy)<1e-9?canvasColor("--axis","#233043"):canvasColor("--grid","#161d27");
    ctx.beginPath(); ctx.moveTo(0,sy(gy)); ctx.lineTo(W(),sy(gy)); ctx.stroke();
  }
}

const ORIENT={
  R0:[1,0,0,1], R90:[0,-1,1,0], R180:[-1,0,0,-1], R270:[0,1,-1,0],
  MX:[1,0,0,-1], MY:[-1,0,0,1], MXR90:[0,1,1,0], MYR90:[0,-1,-1,0],
};
function xf(p,off,o){const m=ORIENT[o]||ORIENT.R0;
  return [m[0]*p[0]+m[1]*p[1]+off[0], m[2]*p[0]+m[3]*p[1]+off[1]];}
function xfBox(b,off,o){
  const c=[xf(b[0],off,o),xf([b[1][0],b[0][1]],off,o),xf(b[1],off,o),xf([b[0][0],b[1][1]],off,o)];
  const xs=c.map(p=>p[0]), ys=c.map(p=>p[1]);
  return [[Math.min(...xs),Math.min(...ys)],[Math.max(...xs),Math.max(...ys)]];}

function drawShape(r, off, o, dim){
  const lay=r.layer||"met1"; if(!vis[lay]) return false;
  const L=LAYERS[lay]||{c:"#888"};
  ctx.globalAlpha = dim?0.55:1;
  if(r.objType==="label"){
    if(!vis.text){ctx.globalAlpha=1;return false;}
    const p=xf(r.xy||[0,0],off,o);
    const light=document.documentElement.dataset.theme==='light';
    if(light)ctx.globalAlpha=1;
    ctx.fillStyle=light||lay==='text'?canvasColor('--ink',L.c):L.c;
    ctx.font=(light?'600 13px':dim?'11px':'600 12px')+' ui-monospace,Consolas,"Malgun Gothic",monospace';
    ctx.textAlign="center";ctx.strokeStyle=canvasColor('--canvas','#07090d');ctx.lineWidth=3;
    ctx.strokeText(r.text||'',sx(p[0]),sy(p[1])+4);
    ctx.fillText(r.text||"", sx(p[0]), sy(p[1])+4); ctx.textAlign="left";
    ctx.globalAlpha=1; return true;
  }
  const b0=r.bbox; if(!b0){ctx.globalAlpha=1;return false;}
  if(r.objType==='polygon'&&r.points?.length>=3){
    ctx.beginPath();
    r.points.forEach((point,index)=>{const p=xf(point,off,o);if(index===0)ctx.moveTo(sx(p[0]),sy(p[1]));else ctx.lineTo(sx(p[0]),sy(p[1]));});
    ctx.closePath();
    const pattern=patternFor(lay);
    if(pattern){ctx.fillStyle=pattern;ctx.globalAlpha=dim?.3:.55;ctx.fill();}
    ctx.globalAlpha=dim?.5:1;ctx.fillStyle=L.c+'22';ctx.fill();ctx.strokeStyle=L.c;ctx.lineWidth=dim?1:1.4;ctx.stroke();
    ctx.globalAlpha=1;return true;
  }
  const b=xfBox(b0,off,o);
  const x=sx(b[0][0]), y=sy(b[1][1]),
        w=Math.max((b[1][0]-b[0][0])*view.s,1), h=Math.max((b[1][1]-b[0][1])*view.s,1);
  if(r.objType==="via"){
    ctx.fillStyle=L.c; ctx.fillRect(x-4,y-4,8,8);
    ctx.strokeStyle=canvasColor("--ink","#fff"); ctx.lineWidth=1; ctx.strokeRect(x-4,y-4,8,8);
    ctx.globalAlpha=1; return true;
  }
  const p=patternFor(lay);
  if(p){ctx.fillStyle=p; ctx.globalAlpha=(dim?.3:.55); ctx.fillRect(x,y,w,h);}
  ctx.globalAlpha=dim?0.5:1;
  ctx.fillStyle=L.c+"22"; ctx.fillRect(x,y,w,h);
  ctx.strokeStyle=L.c; ctx.lineWidth=dim?1:1.4; ctx.strokeRect(x,y,w,h);
  ctx.globalAlpha=1; return true;
}

function draw(){
  ctx.fillStyle=canvasColor("--canvas","#07090d"); ctx.fillRect(0,0,W(),H()); grid();
  let ns=0, ni=0;const labels=[];
  for(const r of rows){
    if(r.kind==="instance"){
      ni++;
      const off=r.xy||[0,0], o=r.orient||"R0";
      const kids = masters[`${r.lib}/${r.cell}`]||[];
      for(const k of kids){if(k.objType==='label')labels.push([k,off,o,true]);else drawShape(k,off,o,true);}
      const b=r.bbox;
      if(b){
        const x=sx(b[0][0]), y=sy(b[1][1]),
              w=(b[1][0]-b[0][0])*view.s, h=(b[1][1]-b[0][1])*view.s;
        ctx.setLineDash([5,4]); ctx.strokeStyle="#8b949e"; ctx.lineWidth=1.1;
        ctx.strokeRect(x,y,w,h); ctx.setLineDash([]);
        ctx.fillStyle=canvasColor("--dim","#8b949e"); ctx.font="11px ui-monospace,monospace";
        ctx.fillText(`${r.name} (${r.cell}) ${o}`, x+5, y+14);
      }
      continue;
    }
    if(r.objType==='label')labels.push([r,[0,0],'R0',false]);
    else if(drawShape(r,[0,0],"R0",false)) ns++;
  }
  for(const [r,off,orient,dim] of labels)if(drawShape(r,off,orient,dim)&&!dim)ns++;
  // Host pages opt into the counters by defining these; a page without
  // them still draws.
  if($("hudShapes")) $("hudShapes").textContent=ns;
  if($("hudInsts")) $("hudInsts").textContent=ni;
}

function fit(){
  const bs=rows.map(r=>r.bbox).filter(Boolean);
  if(!bs.length){view={x:0,y:0,s:26};draw();return;}
  const x0=Math.min(...bs.map(b=>b[0][0])), y0=Math.min(...bs.map(b=>b[0][1]));
  const x1=Math.max(...bs.map(b=>b[1][0])), y1=Math.max(...bs.map(b=>b[1][1]));
  view.x=(x0+x1)/2; view.y=(y0+y1)/2;
  view.s=Math.min(W()/Math.max(x1-x0,1), H()/Math.max(y1-y0,1))*0.78;
  draw();
}

// pan / zoom / coords
let drag=null;
cv.addEventListener("mousedown",e=>drag={px:e.offsetX,py:e.offsetY,vx:view.x,vy:view.y});
addEventListener("mouseup",()=>drag=null);
cv.addEventListener("mousemove",e=>{
  // Pan first. The readout is optional decoration and used not to be: writing
  // to a #hudX that a host page did not have threw here, and the drag below
  // never ran — zoom worked, panning did not, and nothing said why.
  if(drag){view.x=drag.vx-(e.offsetX-drag.px)/view.s;
           view.y=drag.vy+(e.offsetY-drag.py)/view.s; draw();}
  if($("hudX")) $("hudX").textContent=wx(e.offsetX).toFixed(3);
  if($("hudY")) $("hudY").textContent=wy(e.offsetY).toFixed(3);
});
cv.addEventListener("wheel",e=>{
  e.preventDefault();
  const bx=wx(e.offsetX), by=wy(e.offsetY);
  view.s*=e.deltaY<0?1.12:1/1.12; view.s=Math.max(2,Math.min(400,view.s));
  view.x=bx-(e.offsetX-W()/2)/view.s; view.y=by+(e.offsetY-H()/2)/view.s; draw();
},{passive:false});

function lsw(){
  const counts={};
  const bump=l=>{if(l){counts[l]=(counts[l]||0)+1;if(!LAYERS[l]){LAYERS[l]={c:'#77869b',h:''};vis[l]=true;}}};
  rows.forEach(r=>{
    if(r.kind==="instance"){ (masters[`${r.lib}/${r.cell}`]||[]).forEach(k=>bump(k.layer)); }
    else bump(r.layer);
  });
  $("lsw").innerHTML="";
  for(const [name,L] of Object.entries(LAYERS)){
    if(!counts[name])continue;
    const d=document.createElement("div");
    d.className="layer"+(vis[name]?"":" off");
    const sw=document.createElement('div');sw.className='sw';sw.style.background=L.c;
    const label=document.createElement('div');label.className='nm';label.textContent=name;
    const count=document.createElement('div');count.className='ct';count.textContent=counts[name]||0;
    d.append(sw,label,count);
    d.onclick=()=>{vis[name]=!vis[name]; lsw(); draw();
      if(typeof onLayerToggle==="function") onLayerToggle(name, vis[name]);};
    $("lsw").appendChild(d);
  }
}
