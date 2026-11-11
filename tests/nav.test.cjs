// Socket-free interaction tests. Browser geometry is checked separately.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const {attach} = require('../static/nav.js');

class Events {
  constructor() { this.listeners = new Map(); }
  addEventListener(type, fn, capture = false) {
    const list = this.listeners.get(type) || [];
    list.push({fn, capture: capture === true}); this.listeners.set(type,list);
  }
  fire(type, values = {}) {
    const event = {target:this, button:0, pointerId:1, isPrimary:true, clientX:20, clientY:20,
      isTrusted:true, detail:1, defaultPrevented:false, stopped:false,
      preventDefault() { this.defaultPrevented = true; },
      stopImmediatePropagation() { this.stopped = true; }, ...values};
    for (const {fn} of [...(this.listeners.get(type)||[])].sort((a,b) => b.capture-a.capture)) {
      fn(event); if (event.stopped) break;
    }
    return event;
  }
}
class Element extends Events {
  constructor(tag = 'span', doc) {
    super(); this.tagName=tag.toUpperCase(); this.ownerDocument=doc;
    this.children=[]; this.dataset={}; this.style={}; this.attrs={}; this.classes=new Set();
    this.rect={left:0,top:0,width:300,height:44,right:300,bottom:44};
    this.clientLeft=1; this.clientTop=1; this.scrollLeft=0; this.scrollTop=0;
    this.classList={add:(...c) => c.forEach(x => this.classes.add(x)), remove:(...c) => c.forEach(x => this.classes.delete(x)),
      toggle:(c,on) => { if (on ?? !this.classes.has(c)) this.classes.add(c); else this.classes.delete(c); }};
  }
  set className(value) { this.classes=new Set(value.split(' ')); }
  get className() { return [...this.classes].join(' '); }
  append(child) { child.parent=this; this.children.push(child); }
  setAttribute(k,v) { this.attrs[k]=v; }
  getAttribute(k) { return this.attrs[k] ?? null; }
  hasAttribute(k) { return k in this.attrs; }
  getBoundingClientRect() { return this.rect; }
  getClientRects() { return this.hidden ? [] : [this.rect]; }
  contains(node) { return this.children.some(c => c === node || c.contains(node)); }
  matches() { return this.classes.has('active') || this.attrs['aria-pressed']==='true' || this.attrs['aria-current']==='page'; }
  querySelector() { return this.children.find(c => c.classes.has('active')) || null; }
  setPointerCapture(id) { this.capture=id; }
  hasPointerCapture(id) { return this.capture===id; }
  releasePointerCapture() { this.capture=null; }
  click() { this.parent.fire('click',{target:this,isTrusted:false,detail:0}); }
}
function fixture(tag = 'button', reduced = false) {
  const doc = new Events(); doc.createElement = tag => new Element(tag,doc);
  const nav = new Element('nav',doc), env=new Events(), raf=[], timers=[];
  let activations=0, destination=null;
  Object.assign(env, {
    requestAnimationFrame:fn => (raf.push(fn),raf.length),
    setTimeout:(fn,delay) => (timers.push({fn,delay}),timers.length), clearTimeout:() => {},
    matchMedia:() => ({matches:reduced}), getComputedStyle:() => ({visibility:'visible'}),
    ResizeObserver:class { observe() {} }, MutationObserver:class { observe() {} },
    location:{href:'https://example.test/results/',origin:'https://example.test',assign:url => {destination=url;}}
  });
  const items = [0,1,2].map(i => {
    const e=new Element(tag,doc); e.rect={left:5+i*95,top:5,width:90,height:34,right:95+i*95,bottom:39};
    e.href=`https://example.test/results/reports/demo/section${i}.html?d=2`;
    if (i===0) e.classList.add('active'); nav.append(e); return e;
  });
  if (tag==='button') nav.addEventListener('click',e => {
    if (!items.includes(e.target)) return;
    activations++; items.forEach(item => item.classList.toggle('active',item===e.target));
  });
  attach(nav,env);
  const flush = () => { let limit=30; while (raf.length && limit--) raf.shift()(); assert.ok(limit>0); };
  flush();
  const start = () => nav.fire('pointerdown',{target:items[0]});
  const move = (x=140,y=20) => nav.fire('pointermove',{target:items[0],clientX:x,clientY:y});
  const end = (x=140,y=20) => nav.fire('pointerup',{target:nav,clientX:x,clientY:y});
  return {nav,env,doc,items,flush,start,move,end,timers,pill:nav.children[3],preview:nav.children[4],
    get activations() { return activations; }, get destination() { return destination; }};
}

test('ordinary and keyboard click keep existing handler; selection follows real rectangles',() => {
  const f=fixture(); f.start(); f.move(24);
  assert.equal(f.nav.capture,undefined); f.end(24);
  f.nav.fire('click',{target:f.items[1],detail:0}); f.flush();
  assert.equal(f.activations,1); assert.equal(f.pill.style.left,'99px');
  assert.equal(f.pill.style.width,'90px'); assert.equal(f.pill.getAttribute('aria-hidden'),'true');
});
test('drag previews only, commits once on release, suppresses pointer click but preserves keyboard',() => {
  const f=fixture(); f.start(); f.move();
  assert.equal(f.activations,0); assert.equal(f.nav.capture,1);
  assert.equal(f.preview.hidden,false); assert.equal(f.pill.hidden,true);
  f.end(); f.flush(); assert.equal(f.activations,1); assert.ok(f.items[1].classes.has('active'));
  const generated=f.nav.fire('click',{target:f.items[1]});
  assert.equal(generated.defaultPrevented,true); assert.equal(f.activations,1);
  f.nav.fire('click',{target:f.items[2],detail:0}); assert.equal(f.activations,2);
});
test('every cancellation restores original selection without activating a page',() => {
  for (const cancel of [f => f.doc.fire('keydown',{key:'Escape'}), f => f.nav.fire('pointercancel'),
    f => f.nav.fire('lostpointercapture'), f => f.env.fire('blur'), f => f.env.fire('resize'),
    f => f.end(301), f => f.end(100,61)]) {
    const f=fixture(); f.start(); f.move(); cancel(f); f.flush();
    assert.equal(f.activations,0); assert.equal(f.preview.hidden,true); assert.equal(f.pill.hidden,false);
    assert.equal(f.pill.style.left,'4px');
  }
});
test('a new physical press after a cancelled drag is not suppressed',() => {
  const f=fixture(); f.start(); f.move(); f.nav.fire('pointercancel');
  f.nav.fire('pointerdown',{target:f.items[1],clientX:140}); f.end();
  const click=f.nav.fire('click',{target:f.items[1]});
  assert.equal(click.defaultPrevented,false); assert.equal(f.activations,1);
});
test('hidden and disabled targets are excluded; nonprimary and modified gestures ignored',() => {
  const f=fixture(); f.items[1].hidden=true; f.items[2].disabled=true;
  f.start(); f.move(240); f.end(240); assert.ok(f.items[0].classes.has('active'));
  for (const values of [{isPrimary:false},{button:2},{ctrlKey:true},{metaKey:true}]) {
    const g=fixture(); g.nav.fire('pointerdown',{target:g.items[0],...values}); g.move(); g.end();
    assert.equal(g.activations,0); assert.equal(g.nav.capture,undefined);
  }
});
test('report links preserve URL/query and modified click; reduced motion skips delay',() => {
  const f=fixture('a');
  assert.equal(f.nav.fire('click',{target:f.items[1],ctrlKey:true}).defaultPrevented,false);
  const click=f.nav.fire('click',{target:f.items[1],detail:0});
  assert.equal(click.defaultPrevented,true); assert.equal(f.timers[0].delay,260);
  assert.equal(f.destination,null); f.timers[0].fn();
  assert.equal(f.destination,f.items[1].href);
  const g=fixture('a',true); g.start(); g.move(); g.end();
  assert.equal(g.timers[0].delay,0); g.timers[0].fn(); assert.equal(g.destination,g.items[1].href);
});
