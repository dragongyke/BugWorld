'use strict';
// Browser-only interaction study. Production PaintDocument / native windows are unchanged.
const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];
const SIZE = 1024;
const SPECIES = {butterfly:'蝴蝶',beetle:'独角仙',ladybug:'瓢虫',caterpillar:'毛毛虫'};
const COLORS = [['樱花粉','#e985b6'],['丁香紫','#bc8be0'],['鸢尾紫','#986bd3'],['晴空蓝','#7e9edf'],['薄荷绿','#78c6ac'],['湖水青','#50b3ba'],['蜂蜜黄','#e7b65e'],['珊瑚橙','#eb937d'],['玫瑰灰','#d6a6b6'],['燕麦棕','#c5b49e'],['雾灰','#a6a5b1'],['岩石灰','#777484']];
const STORAGE = 'bugworld-ui-prototype-20261028';
const state = {species:'butterfly',tool:'crayon',color:0,radius:12,strength:.45,mirror:false,ready:false,busy:false,albumOpen:false,layout:'spatial',errorNext:false};
const resources = new Map(), drafts = new Map();
let artworks = [], toastTimer, painting = false, lastPoint = null, strokeChanged = false, strokeBefore = null, framePending = false, pendingOperation = 0;
const paint = $('#paint'), context = paint.getContext('2d');
const layer = document.createElement('canvas');layer.width=layer.height=SIZE;
const layerContext=layer.getContext('2d');
const dialog=$('#dialog');
let focusBeforeDialog;

function blankDraft(){return {pixels:new Uint8ClampedArray(SIZE*SIZE*4),undo:[],redo:[],revision:0,savedRevision:-1,savedId:null};}
function draft(){return drafts.get(state.species);}
function image(src){return new Promise((resolve,reject)=>{const img=new Image();img.onload=()=>resolve(img);img.onerror=()=>reject(new Error(`无法读取 ${src}`));img.src=src;});}
function notify(message){$('#toast').textContent=message;$('#toast').classList.add('visible');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('#toast').classList.remove('visible'),4500);}
function fit(){
  const viewport=$('#viewport');const width=viewport.clientWidth,height=viewport.clientHeight;
  const left=state.albumOpen?384:0;const extent=state.albumOpen?1870:1490;
  const scale=state.layout==='flat'?Math.min((width-48)/extent,1):Math.min((width-48)/extent,(height-35)/1010,1);
  const workspace=$('#workspace');workspace.style.transform=`scale(${scale})`;
  workspace.style.left=`${Math.max(20,(width-extent*scale)/2)+left*scale}px`;
  workspace.style.top=`${state.layout==='flat'?18:Math.max(10,(height-1010*scale)/2)}px`;
  workspace.classList.toggle('flat',state.layout==='flat');
}
function draw(){if(!state.ready)return;layerContext.putImageData(new ImageData(draft().pixels,SIZE,SIZE),0,0);context.clearRect(0,0,SIZE,SIZE);context.drawImage(layer,0,0);context.drawImage(resources.get(state.species).lines,0,0);}
function requestDraw(){if(framePending)return;framePending=true;requestAnimationFrame(()=>{framePending=false;draw();});}
function snapshot(){return draft().pixels.slice();}
function pushUndo(before){const d=draft();d.undo.push(before);if(d.undo.length>8)d.undo.shift();d.redo=[];d.revision++;update();}
function update(){
  if(!state.ready)return;
  const d=draft();$('#species-name').textContent=SPECIES[state.species];
  $$('.species-items .species').forEach(b=>{const selected=b.dataset.species===state.species;b.classList.toggle('selected',selected);b.setAttribute('aria-pressed',selected);b.disabled=state.busy;});
  $$('.tool-tabs button').forEach(b=>{const selected=b.dataset.tool===state.tool;b.classList.toggle('selected',selected);b.setAttribute('aria-pressed',selected);b.disabled=state.busy;});
  $$('.swatch').forEach((b,i)=>{const selected=state.color===i;b.classList.toggle('selected',selected);b.setAttribute('aria-pressed',selected);b.disabled=state.tool==='eraser'||state.busy;});
  $('#color-name').textContent=state.tool==='eraser'?'橡皮保留画纸轮廓':COLORS[state.color][0];
  $('#brush-color').textContent=state.tool==='eraser'?'擦去涂色':COLORS[state.color][0];
  $('#brush-description').textContent=state.tool==='crayon'?`蜡笔 · ${state.strength<.4?'轻轻涂':state.strength<.75?'慢慢叠色':'浓浓涂'}`:state.tool==='fill'?'填色 · 点一下区域':'橡皮 · 轻轻擦';
  $('#radius').disabled=state.tool==='fill'||state.busy;$('#strength').disabled=state.tool!=='crayon'||state.busy;
  $('#radius-label').classList.toggle('unavailable',state.tool==='fill');$('#strength-label').classList.toggle('unavailable',state.tool!=='crayon');
  $('#radius-value').value=state.tool==='fill'?'区域填色':state.radius;
  $('#strength-value').value=state.tool==='crayon'?(state.strength<.4?'轻涂':state.strength<.75?'适中':'浓涂'):'—';
  $('#radius').style.setProperty('--value',`${(state.radius-4)/20*100}%`);$('#strength').style.setProperty('--value',`${(state.strength*100-8)/92*100}%`);
  $('#mirror').disabled=state.species!=='butterfly'||state.busy;$('#mirror').setAttribute('aria-checked',state.species==='butterfly'&&state.mirror);
  $('#mirror-help').textContent=state.species==='butterfly'?'两边翅膀，一起上色':'蝴蝶画纸支持对称绘画';
  $('#undo').disabled=!d.undo.length||state.busy;$('#redo').disabled=!d.redo.length||state.busy;
  for(const id of ['save','preview','release','new-paper','visit-garden'])$('#'+id).disabled=state.busy;
  const status=$('#save-state');status.textContent=state.busy?'正在准备…':d.savedRevision===d.revision?'已保存到作品册':d.revision?'有新的涂色 · 尚未保存':'一张新画纸';status.classList.toggle('saved',d.savedRevision===d.revision&&!state.busy);
  $('#paint-hint').textContent=state.tool==='fill'?'点一下轮廓内，让颜色住进去':state.tool==='eraser'?'只擦掉颜色，轮廓会留下':state.mirror&&state.species==='butterfly'?'对称已开启 · 两边翅膀一起上色':'挑一种颜色，从这里开始吧';
  drawBrush();
}
function rgb(){const color=COLORS[state.color][1];return [1,3,5].map(i=>parseInt(color.slice(i,i+2),16));}
function noise(x,y){let n=Math.imul(x+37,y+149)^Math.imul(x,374761393)^Math.imul(y,668265263);n=Math.imul(n^(n>>>13),1274126177);return ((n^(n>>>16))>>>0)/4294967295;}
function drawBrush(){
  const c=$('#brush-sample'),ctx=c.getContext('2d');ctx.clearRect(0,0,c.width,c.height);
  if(state.tool==='fill'){ctx.fillStyle=COLORS[state.color][1];ctx.beginPath();ctx.roundRect(32,25,490,40,18);ctx.fill();return;}
  if(state.tool==='eraser'){ctx.fillStyle='#d2c1de';ctx.fillRect(32,25,490,40);ctx.clearRect(155,20,140,50);return;}
  const [r,g,b]=rgb();const data=ctx.createImageData(c.width,c.height);
  for(let x=18;x<542;x++)for(let y=0;y<c.height;y++){const mid=46+Math.sin(x/70)*12;const radius=8+state.radius*.65;if(Math.abs(y-mid)>radius)continue;const q=noise(x,y);const edge=1-Math.abs(y-mid)/radius;const i=(y*c.width+x)*4;data.data[i]=r;data.data[i+1]=g;data.data[i+2]=b;data.data[i+3]=(q>.17?(.24+q*.52)*state.strength*edge:0)*255;}
  ctx.putImageData(data,0,0);
}
function coordinate(event){const rect=paint.getBoundingClientRect();return {x:(event.clientX-rect.left)/rect.width*SIZE,y:(event.clientY-rect.top)/rect.height*SIZE};}
function stamp(x,y){
  const pixels=draft().pixels,mask=resources.get(state.species).mask;const radius=state.radius*1.6;const [r,g,b]=rgb();
  for(let py=Math.max(0,Math.floor(y-radius));py<Math.min(SIZE,Math.ceil(y+radius));py++)for(let px=Math.max(0,Math.floor(x-radius));px<Math.min(SIZE,Math.ceil(x+radius));px++){
    const distance=Math.hypot(px-x,py-y)/radius;if(distance>1||!mask[py*SIZE+px])continue;
    const i=(py*SIZE+px)*4;
    if(state.tool==='eraser'){if(pixels[i+3]){pixels[i+3]=0;strokeChanged=true;}continue;}
    const grain=noise(px,py);if(grain<.16)continue;
    const alpha=(.08+state.strength*.42)*(.25+grain*.75)*Math.min(1,(1-distance)*4);
    const old=pixels[i+3]/255;const a=alpha+old*(1-alpha);if(a<=0)continue;
    pixels[i]=(r*alpha+pixels[i]*old*(1-alpha))/a;pixels[i+1]=(g*alpha+pixels[i+1]*old*(1-alpha))/a;pixels[i+2]=(b*alpha+pixels[i+2]*old*(1-alpha))/a;pixels[i+3]=Math.round(a*255);strokeChanged=true;
  }
}
function mirrorX(x){return 2*(64+251*1.77075099)-x;}
function stroke(point){
  const previous=lastPoint||point,dist=Math.hypot(point.x-previous.x,point.y-previous.y),steps=Math.max(1,Math.ceil(dist/Math.max(2,state.radius*.4)));
  for(let step=1;step<=steps;step++){const x=previous.x+(point.x-previous.x)*step/steps,y=previous.y+(point.y-previous.y)*step/steps;stamp(x,y);if(state.mirror&&state.species==='butterfly')stamp(mirrorX(x),y);}
  lastPoint=point;requestDraw();
}
function fill(point){
  const mask=resources.get(state.species).mask,pixels=draft().pixels;const x=Math.floor(point.x),y=Math.floor(point.y);if(x<0||x>=SIZE||y<0||y>=SIZE)return;
  const target=mask[y*SIZE+x];if(!target)return;const targets=new Set([target]);if(state.mirror&&state.species==='butterfly'){const mx=Math.round(mirrorX(x));if(mx>=0&&mx<SIZE&&mask[y*SIZE+mx])targets.add(mask[y*SIZE+mx]);}
  const [r,g,b]=rgb();for(let i=0;i<mask.length;i++)if(targets.has(mask[i])){pixels[i*4]=r;pixels[i*4+1]=g;pixels[i*4+2]=b;pixels[i*4+3]=230;strokeChanged=true;}requestDraw();
}
paint.addEventListener('pointerdown',e=>{if(!state.ready||state.busy||e.button!==0)return;e.preventDefault();painting=true;lastPoint=null;strokeChanged=false;strokeBefore=snapshot();paint.setPointerCapture(e.pointerId);if(state.tool==='fill')fill(coordinate(e));else stroke(coordinate(e));});
paint.addEventListener('pointermove',e=>{if(painting&&state.tool!=='fill')stroke(coordinate(e));});
function finishStroke(){if(!painting)return;painting=false;lastPoint=null;if(strokeChanged)pushUndo(strokeBefore);strokeBefore=null;}
paint.addEventListener('pointerup',finishStroke);paint.addEventListener('pointercancel',finishStroke);paint.addEventListener('lostpointercapture',finishStroke);

function showDialog(html){focusBeforeDialog=document.activeElement;$('#dialog-content').innerHTML=html;const title=$('#dialog-content h2');if(title){title.id='dialog-title';dialog.setAttribute('aria-labelledby','dialog-title');}dialog.showModal();}
function closeDialog(){pendingOperation++;dialog.close();if(state.busy){state.busy=false;update();}focusBeforeDialog?.focus();}
dialog.addEventListener('cancel',e=>{e.preventDefault();closeDialog();});
function confirm(title,message,action,label='确认'){
  showDialog(`<h2>${title}</h2><p>${message}</p><div class="dialog-actions"><button class="button secondary" id="dialog-cancel">取消</button><button class="button primary" id="dialog-confirm">${label}</button></div>`);
  $('#dialog-cancel').onclick=closeDialog;$('#dialog-confirm').onclick=()=>{closeDialog();action();};
}
function tools(visible){$('.tools').hidden=!visible;$('#tools-toggle').setAttribute('aria-expanded',visible);$('#tools-toggle').setAttribute('aria-label',visible?'收起画具':'展开画具');}
function openAlbum(open){state.albumOpen=open;$('#album').hidden=!open;$('#album-toggle').setAttribute('aria-expanded',open);renderAlbum();fit();}
function selectSpecies(key){if(!state.ready||state.busy)return;finishStroke();state.species=key;$('#inline-alert').hidden=true;update();draw();}
$$('.species-items button').forEach(button=>button.onclick=()=>selectSpecies(button.dataset.species));
$('.brand').onclick=()=>{hideStates();notify('画板就在这里，继续涂色吧。');};
$$('.tool-tabs button').forEach(button=>button.onclick=()=>{state.tool=button.dataset.tool;update();});
$('#palette').innerHTML=COLORS.map(([name,color],i)=>`<button class="swatch${i===0?' selected':''}" style="--swatch:${color}" aria-label="${name}" aria-pressed="${i===0}" title="${name}"></button>`).join('');
$$('.swatch').forEach((button,i)=>button.onclick=()=>{state.color=i;update();});
$('#radius').oninput=e=>{state.radius=+e.target.value;update();};$('#strength').oninput=e=>{state.strength=+e.target.value/100;update();};
$('#mirror').onclick=()=>{state.mirror=!state.mirror;update();};
$('#undo').onclick=()=>{const d=draft();if(!d.undo.length)return;d.redo.push(snapshot());d.pixels=d.undo.pop();d.revision++;update();draw();};
$('#redo').onclick=()=>{const d=draft();if(!d.redo.length)return;d.undo.push(snapshot());d.pixels=d.redo.pop();d.revision++;update();draw();};
$('#tools-toggle').onclick=()=>tools($('.tools').hidden);$('#close-tools').onclick=()=>tools(false);
$('#album-toggle').onclick=()=>openAlbum(!state.albumOpen);$('#close-album').onclick=()=>openAlbum(false);
$('#new-paper').onclick=()=>{const fresh=()=>{drafts.set(state.species,blankDraft());$('#inline-alert').hidden=true;draw();update();notify('新画纸准备好了。已保存的作品仍在作品册。');};if(draft().revision>0&&draft().savedRevision!==draft().revision)confirm('换一张新画纸？','当前还没保存的涂色会被替换。你可以取消，先把它保存到作品册。',fresh,'换新画纸');else fresh();};

function thumbnail(){const c=document.createElement('canvas');c.width=c.height=300;const ctx=c.getContext('2d');ctx.fillStyle='#fffcf5';ctx.fillRect(0,0,300,300);ctx.drawImage(paint,0,0,300,300);return c.toDataURL('image/png');}
function saveError(message){$('#inline-alert').replaceChildren();const text=document.createElement('span');text.textContent=message;const retry=document.createElement('button');retry.textContent='重新保存';retry.onclick=()=>save();$('#inline-alert').append(text,retry);$('#inline-alert').hidden=false;}
async function save(){
  if(state.busy||!state.ready)return false;state.busy=true;update();$('#save').setAttribute('aria-busy','true');$('#save span').textContent='保存中';$('#inline-alert').hidden=true;
  // Deliberately visible in a design study; no real storage latency is implied.
  await new Promise(resolve=>setTimeout(resolve,650));
  try{
    if(state.errorNext){state.errorNext=false;throw new Error('demo');}
    draw();const d=draft(),existing=artworks.find(a=>a.id===d.savedId);const item={id:existing?.id||crypto.randomUUID(),species:state.species,date:new Date().toISOString(),pixels:layer.toDataURL('image/png'),thumbnail:thumbnail()};
    const next=existing?artworks.map(a=>a.id===item.id?item:a):[item,...artworks];localStorage.setItem(STORAGE,JSON.stringify(next));artworks=next;d.savedId=item.id;d.savedRevision=d.revision;renderAlbum();notify('已保存到作品册，随时可以继续画。');return true;
  }catch(error){saveError(error.message==='demo'?'暂时没能保存。你的涂色还在画板上。':'浏览器没有足够空间保存。涂色仍保留在画板，可稍后重试。');return false;}
  finally{state.busy=false;$('#save').removeAttribute('aria-busy');$('#save span').textContent='保存';update();}
}
$('#save').onclick=()=>save();
function renderAlbum(){
  $('#album-count').textContent=artworks.length;const list=$('#album-list');list.replaceChildren();
  if(!artworks.length){list.innerHTML='<div class="empty-album"><img src="assets/album.svg" alt=""><h3>留住第一只小生命</h3><p>画好后，点一下「保存」。<br>你的颜色就会留在这里。</p></div>';return;}
  artworks.forEach(item=>{const card=document.createElement('article');card.className='art-card';const thumb=document.createElement('img');thumb.src=item.thumbnail;thumb.alt=`${SPECIES[item.species]}作品缩略图`;const meta=document.createElement('div');meta.className='art-meta';const title=document.createElement('span');title.textContent=SPECIES[item.species];const date=document.createElement('small');date.textContent=new Date(item.date).toLocaleDateString('zh-CN',{month:'numeric',day:'numeric'});meta.append(title,date);const buttons=document.createElement('div');buttons.className='art-buttons';
    const edit=document.createElement('button');edit.className='button secondary';edit.textContent='继续画';edit.onclick=async()=>{if(state.busy)return;const resume=async()=>{state.busy=true;update();try{const img=await image(item.pixels);state.species=item.species;const d=blankDraft();layerContext.clearRect(0,0,SIZE,SIZE);layerContext.drawImage(img,0,0);d.pixels=layerContext.getImageData(0,0,SIZE,SIZE).data;d.savedId=item.id;d.savedRevision=0;drafts.set(item.species,d);draw();notify('已打开这张作品，可以继续画。');}catch{notify('这张原型作品暂时无法读取，当前草稿没有改变。');}finally{state.busy=false;update();}};const target=drafts.get(item.species);if(target.revision>0&&target.savedRevision!==target.revision)confirm('打开作品继续画？','这类昆虫还有未保存的草稿。继续会用选中的作品替换它。',resume,'继续画');else await resume();};
    const release=document.createElement('button');release.className='button secondary';release.textContent='放入花园';release.onclick=()=>gardenDemo(item.thumbnail);
    const remove=document.createElement('button');remove.className='button secondary delete';remove.textContent='×';remove.setAttribute('aria-label',`删除${SPECIES[item.species]}作品`);remove.onclick=()=>confirm('删除这张作品？','它会从当前浏览器的原型作品册中移除，正式应用的作品不会改变。',()=>{const next=artworks.filter(a=>a.id!==item.id);try{localStorage.setItem(STORAGE,JSON.stringify(next));artworks=next;for(const d of drafts.values())if(d.savedId===item.id){d.savedId=null;d.savedRevision=-1;}renderAlbum();update();}catch{notify('未能删除，作品仍然保留。');}},'删除');
    buttons.append(edit,release,remove);card.append(thumb,meta,buttons);list.append(card);
  });
}
function previewDemo(){
  if(!state.ready||state.busy)return;draw();showDialog('<div class="prototype-label">空间预览 · 衔接示意</div><h2>让它立体起来</h2><p>正式应用中，昆虫会出现在画板前方。用手捏住旋转，轻触它，看看它的回应。</p><img class="art-preview" id="preview-image" alt="当前画作，二维示意"><p>这里展示当前二维画作；真实 3D 模型与手势由原生应用承接。</p><div class="dialog-actions"><button class="button primary" id="dialog-done">继续画</button></div>');$('#preview-image').src=thumbnail();$('#dialog-done').onclick=closeDialog;
}
async function gardenDemo(thumb){
  if(state.busy)return;const operation=++pendingOperation;state.busy=true;update();showDialog('<div class="prototype-label">前往花园 · 流程示意</div><h2>等花园准备好</h2><p>先让场景完整出现，再让新昆虫带着光点来到你面前。</p><div class="dialog-actions"><button class="button secondary" id="cancel-garden">返回画板</button></div>');$('#cancel-garden').onclick=closeDialog;
  await new Promise(resolve=>setTimeout(resolve,1400));if(operation!==pendingOperation)return;state.busy=false;update();$('#dialog-content').innerHTML='<div class="prototype-label">场景就绪后的入场 · 流程示意</div><div class="success-mark">✦</div><h2 id="dialog-title">带着你的颜色，去自然里</h2><p>这一步由原生 Stage 接手：沿固定路线活动，凝视目标后用手互动；魔法球带你回到画板。</p><p style="margin-top:12px">当前浏览器仅演示界面衔接，没有加载森林或生成昆虫。</p><div class="dialog-actions"><button class="button primary" id="return-board">回到画板</button></div>';$('#return-board').onclick=closeDialog;$('#return-board').focus();
}
$('#preview').onclick=previewDemo;$('#release').onclick=async()=>{if(await save())gardenDemo(thumbnail());};$('#visit-garden').onclick=()=>gardenDemo();
$('#sound-button').onclick=()=>{showDialog('<h2>花园声音</h2><p>调到你觉得舒服的音量。</p><label><span>音乐 <output id="music-level">35%</output></span><input id="music-volume" aria-label="音乐音量" type="range" min="0" max="100" value="35"></label><label><span>自然声 <output id="nature-level">60%</output></span><input id="nature-volume" aria-label="自然声音量" type="range" min="0" max="100" value="60"></label><p>原型仅展示控件，不播放声音。</p><div class="dialog-actions"><button class="button primary" id="sound-done">完成</button></div>');$('#music-volume').oninput=e=>$('#music-level').value=e.target.value+'%';$('#nature-volume').oninput=e=>$('#nature-level').value=e.target.value+'%';$('#sound-done').onclick=closeDialog;};
function hideStates(){$('#state-sheet').hidden=true;$('#states-button').setAttribute('aria-pressed','false');}
$('#states-button').onclick=()=>{$('#state-sheet').hidden=!$('#state-sheet').hidden;$('#states-button').setAttribute('aria-pressed',!$('#state-sheet').hidden);};$('#close-states').onclick=hideStates;
$$('[data-layout]').forEach(button=>button.onclick=()=>{state.layout=button.dataset.layout;$$('[data-layout]').forEach(b=>b.setAttribute('aria-pressed',b===button));hideStates();fit();});
$('#demo-error').onclick=()=>{hideStates();state.errorNext=true;save();};
$('#example-color').onclick=()=>{
  if(!state.ready||state.busy)return;const before=snapshot(),pixels=draft().pixels,mask=resources.get(state.species).mask;
  const palette=[[233,133,182],[188,139,224],[126,158,223],[120,198,172],[231,182,94]];
  for(let i=0;i<mask.length;i++)if(mask[i]){const x=i%SIZE,y=Math.floor(i/SIZE),c=palette[(mask[i]-1)%palette.length],q=noise(x,y),i4=i*4;pixels[i4]=c[0];pixels[i4+1]=c[1];pixels[i4+2]=c[2];pixels[i4+3]=q<.17?25:Math.round(75+q*120);}
  pushUndo(before);draw();notify('已加入示例配色，可继续画，也可以撤销。');
};
window.addEventListener('resize',fit);
window.addEventListener('beforeunload',e=>{if([...drafts.values()].some(d=>d.revision>0&&d.revision!==d.savedRevision)){e.preventDefault();e.returnValue='';}});
async function init(){
  fit();for(const species of Object.keys(SPECIES))drafts.set(species,blankDraft());
  try{const saved=JSON.parse(localStorage.getItem(STORAGE)||'[]');artworks=Array.isArray(saved)?saved.filter(a=>SPECIES[a.species]&&typeof a.id==='string'&&typeof a.pixels==='string'&&a.pixels.startsWith('data:image/png;')&&typeof a.thumbnail==='string'&&a.thumbnail.startsWith('data:image/png;')):[];}catch{artworks=[];notify('暂时无法读取原型作品册，可以继续绘画。');}
  renderAlbum();
  try{
    await Promise.all(Object.keys(SPECIES).map(async species=>{const [lines,maskImage]=await Promise.all([image(`assets/${species}-lines.png`),image(`assets/${species}-mask.png`)]);const buffer=document.createElement('canvas');buffer.width=buffer.height=SIZE;const ctx=buffer.getContext('2d',{willReadFrequently:true});ctx.drawImage(maskImage,0,0);const data=ctx.getImageData(0,0,SIZE,SIZE).data,mask=new Uint8Array(SIZE*SIZE);for(let i=0;i<mask.length;i++)mask[i]=data[i*4];resources.set(species,{lines,mask});}));
    state.ready=true;$('#paper-loading').hidden=true;update();draw();
  }catch{const target=$('#paper-loading');target.textContent='画纸暂时没能加载。请重新打开本地原型服务。';}
}
init();
