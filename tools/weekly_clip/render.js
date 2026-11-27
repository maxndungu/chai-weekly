// Films stage.html frame by frame: node render.js <workdir> <square|tall> <framesdir>
const {chromium}=require('playwright');const fs=require('fs');const path=require('path');
const [,,dir,mode,out]=process.argv;const W=540,H=mode==='tall'?960:540,FPS=30;
fs.mkdirSync(out,{recursive:true});
(async()=>{const b=await chromium.launch();const p=await (await b.newContext({viewport:{width:W,height:H},deviceScaleFactor:2})).newPage();
 p.on('pageerror',e=>{console.error('page error:',e.message);process.exitCode=1;});
 await p.goto('file://'+path.resolve(dir,'stage.html')+(mode==='tall'?'#tall':''));
 await p.waitForFunction(()=>window.ready,null,{timeout:30000});
 const T=await p.evaluate(()=>TOTAL);
 for(let i=0;i<Math.round(T*FPS);i++){await p.evaluate(t=>render(t),i/FPS);await p.screenshot({path:`${out}/f${String(i).padStart(4,'0')}.png`});}
 await b.close();})();
