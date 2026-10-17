const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'learning/static/polskiflow/visible-focus.js'),'utf8');
function setup({sidebar=false,dialog=false,outside=false,missing=false,bottom=650,height=44}={}){
 const frames=[],scrolls=[];let focus;
 const target={closest:()=>dialog?{}:null,getBoundingClientRect:()=>({height,bottom})};
 const other={};const doc={activeElement:target,querySelector:()=>missing?null:{getBoundingClientRect:()=>({width:sidebar?240:390,top:580})},getElementById:()=>({contains:e=>!outside&&e===target}),addEventListener:(_,fn)=>focus=fn};
 vm.runInNewContext(source,{document:doc,window:{innerWidth:390,innerHeight:664,scrollBy:value=>scrolls.push(value)},getComputedStyle:()=>({position:'fixed'}),requestAnimationFrame:fn=>frames.push(fn)});
 return{target,other,doc,scrolls,focus:()=>focus?.({target}),flush:()=>frames.splice(0).forEach(fn=>fn())};
}
let f=setup();f.focus();assert.equal(f.scrolls.length,0,'wait for native focus scrolling');f.flush();assert.equal(f.scrolls[0].top,82);assert.equal(f.scrolls[0].behavior,'instant');assert.equal(f.doc.activeElement,f.target,'retain focus');
for(const options of [{sidebar:true},{dialog:true},{outside:true},{missing:true},{bottom:400},{height:0}]){f=setup(options);f.focus();f.flush();assert.equal(f.scrolls.length,0,JSON.stringify(options));}
f=setup();f.focus();f.doc.activeElement=f.other;f.flush();assert.equal(f.scrolls.length,0,'do not act on stale focus');console.log('Visible focus behavior PASS');
