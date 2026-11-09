// Offline candidate only. Preserve every source attribute, skin, clip and image byte.
// npm install --prefix .work/meshopt --ignore-scripts meshoptimizer@1.1.1
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {MeshoptSimplifier} from '../.work/meshopt/node_modules/meshoptimizer/index.js';
await MeshoptSimplifier.ready;
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const out=path.join(root,'assets-src/stage111-geometry');
fs.mkdirSync(out,{recursive:true});
const routes=JSON.parse(fs.readFileSync(path.join(root,'assets-src/stage-ring/garden-routes.json')));
const surfaces=new Set(routes.routes.map(r=>r.surface));
surfaces.add('pond_water');
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const sizes={SCALAR:1,VEC2:2,VEC3:3,VEC4:4,MAT4:16};
const bytes={5121:1,5123:2,5125:4,5126:4};
const readers={5121:'readUInt8',5123:'readUInt16LE',5125:'readUInt32LE',5126:'readFloatLE'};
const results=[];
for(const kind of ['butterfly','beetle','ladybug','caterpillar','garden']) {
  const source=path.join(root,kind==='garden'?'assets-src/stage-ring/garden.glb':`assets-src/insects-batched/${kind}.glb`);
  const raw=fs.readFileSync(source);
  const jsonSize=raw.readUInt32LE(12);
  const doc=JSON.parse(raw.subarray(20,20+jsonSize));
  const bin=raw.subarray(28+jsonSize,28+jsonSize+raw.readUInt32LE(20+jsonSize));
  const originalDoc=structuredClone(doc);
  function attr(index) {
    const a=doc.accessors[index],v=doc.bufferViews[a.bufferView];
    if(a.sparse || v.buffer!==0 || !(a.componentType in bytes)) throw Error('Unsupported accessor');
    const n=sizes[a.type],sz=bytes[a.componentType],start=(v.byteOffset||0)+(a.byteOffset||0);
    const data=new Float32Array(a.count*n);
    for(let i=0;i<a.count;i++) for(let j=0;j<n;j++) {
      let x=bin[readers[a.componentType]](start+i*(v.byteStride||n*sz)+j*sz);
      if(a.normalized) x/=a.componentType===5121?255:65535;
      data[i*n+j]=x;
    }
    return data;
  }
  const protectedMeshes=new Set(doc.nodes.filter(n=>surfaces.has(n.name)).map(n=>n.mesh));
  let cursor=bin.length;
  const chunks=[bin],records=[];
  for(const [mi,mesh] of doc.meshes.entries()) for(const prim of mesh.primitives) {
    if((prim.mode??4)!==4 || prim.targets) throw Error('Only indexed triangle meshes without morphs expected');
    const oldIndex=Uint32Array.from(attr(prim.indices));
    const positions=attr(prim.attributes.POSITION);
    const count=positions.length/3;
    let ratio=0.28;
    // Preserve interaction surfaces and thin membranes/fibres rather than erasing them.
    if(kind==='garden' && (protectedMeshes.has(mi) || mesh.name.includes('moss') || oldIndex.length<9000)) ratio=1;
    if(kind!=='garden' && /membrane|setae|vein|rolled_edge/.test(mesh.name)) ratio=1;
    let reduced=oldIndex,error=0;
    if(ratio<1) {
      const normals=attr(prim.attributes.NORMAL);
      const uv=prim.attributes.TEXCOORD_0===undefined?null:attr(prim.attributes.TEXCOORD_0);
      const joints=prim.attributes.JOINTS_0===undefined?null:attr(prim.attributes.JOINTS_0);
      const weights=joints?attr(prim.attributes.WEIGHTS_0):null;
      const used=joints?[...new Set([...joints].filter((_,i)=>weights[i]>0))].sort((a,b)=>a-b):[];
      // Dense weight coordinates avoid treating discrete joint IDs as continuous values.
      // If a merged mesh spans >27 joints, protect vertices on blended joints instead.
      const dense=used.length<=27?used:[];
      const stride=3+(uv?2:0)+dense.length,attributes=new Float32Array(count*stride),lock=new Uint8Array(count);
      for(let i=0;i<count;i++) {
        attributes.set(normals.subarray(i*3,i*3+3),i*stride);
        if(uv) attributes.set(uv.subarray(i*2,i*2+2),i*stride+3);
        if(joints) for(let j=0;j<4;j++) if(weights[i*4+j]>0) {
          if(dense.length) attributes[i*stride+3+(uv?2:0)+dense.indexOf(joints[i*4+j])]+=weights[i*4+j];
          else if(weights[i*4+j]<.999) lock[i]=1;
        }
      }
      const attributeWeights=[.1,.1,.1,...(uv?[.1,.1]:[]),...dense.map(()=>1)];
      [reduced,error]=MeshoptSimplifier.simplifyWithAttributes(oldIndex,positions,3,attributes,stride,
        attributeWeights,lock,Math.floor(oldIndex.length*ratio/3)*3,.002,['Regularize']);
    }
    if(reduced.length<oldIndex.length) {
      const padding=Buffer.alloc((-cursor)&3);chunks.push(padding);cursor+=padding.length;
      const b=Buffer.from(reduced.buffer,reduced.byteOffset,reduced.byteLength);
      const view=doc.bufferViews.length;doc.bufferViews.push({buffer:0,byteOffset:cursor,byteLength:b.length,target:34963});
      chunks.push(b);cursor+=b.length;
      prim.indices=doc.accessors.length;
      doc.accessors.push({bufferView:view,componentType:5125,count:reduced.length,type:'SCALAR'});
    }
    records.push({mesh:mesh.name,before:oldIndex.length/3,after:reduced.length/3,error,protected:ratio===1});
  }
  // Originals are left byte-for-byte at the start of BIN; only new indices are appended.
  doc.buffers[0].byteLength=cursor;
  const content=Buffer.concat(chunks);
  const jp=Buffer.from(JSON.stringify(doc)),jpad=Buffer.alloc((-jp.length)&3,32),bp=Buffer.alloc((-content.length)&3);
  const header=Buffer.alloc(20);header.write('glTF');header.writeUInt32LE(2,4);
  header.writeUInt32LE(28+jp.length+jpad.length+content.length+bp.length,8);
  header.writeUInt32LE(jp.length+jpad.length,12);header.write('JSON',16);
  const bh=Buffer.alloc(8);bh.writeUInt32LE(content.length+bp.length,0);bh.write('BIN\0',4);
  const output=Buffer.concat([header,jp,jpad,bh,content,bp]);
  const target=path.join(out,`${kind}.glb`);fs.writeFileSync(target,output);
  for(const key of ['nodes','skins','animations','materials','textures','images','samplers']) {
    if(JSON.stringify(originalDoc[key])!==JSON.stringify(doc[key])) throw Error(`Unexpected ${key} mutation`);
  }
  const row={kind,source:path.relative(root,source),sourceSha256:hash(raw),sha256:hash(output),
    trianglesBefore:records.reduce((n,r)=>n+r.before,0),trianglesAfter:records.reduce((n,r)=>n+r.after,0),records};
  results.push(row);
  console.log(kind,row.trianglesBefore,'->',row.trianglesAfter);
}
fs.writeFileSync(path.join(out,'manifest.json'),JSON.stringify({tool:'meshoptimizer 1.1.1 (MIT)',
  documentation:'https://github.com/zeux/meshoptimizer/blob/master/js/README.md',
  scope:'Candidate. Lossy triangle indices only; approved attributes/images/rigs/clips and contact surfaces preserved. Needs render and device validation.',
  results},null,2));
