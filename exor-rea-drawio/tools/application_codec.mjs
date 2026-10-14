// Run unchanged codec functions from draw.io's pinned published bundle.
// This exercises a real application component, not the full browser UI.
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';

const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const manifest=JSON.parse(fs.readFileSync(path.join(root,'upstream-manifest.json'),'utf8'));
function verified(destination){
  const entry=manifest.files.find(e=>e.destination===destination);
  const bytes=fs.readFileSync(path.join(root,'upstream',destination));
  if(!entry||createHash('sha256').update(bytes).digest('hex')!==entry.sha256)throw Error('Unverified artifact: '+destination);
  return bytes.toString('utf8');
}
const bundle=verified('drawio/app.min.js');
const context=vm.createContext({Graph:{},Uint8Array,
  atob:s=>Buffer.from(s,'base64').toString('binary'),
  btoa:s=>Buffer.from(s,'binary').toString('base64')});
vm.runInContext(verified('drawio/pako.min.js'),context,{timeout:3000});
for(const name of ['arrayBufferToString','stringToArrayBuffer','compress','decompress']){
  const marker=`Graph.${name}=function`;
  const start=bundle.indexOf(marker);
  if(start<0||bundle.indexOf(marker,start+marker.length)>=0)throw Error('Missing/ambiguous function: '+name);
  // These four definitions in the hash-verified version terminate at the first };.
  const end=bundle.indexOf('};',start)+2;
  if(end<=start)throw Error('Unterminated function: '+name);
  vm.runInContext(bundle.slice(start,end),context,{timeout:3000});
}
const requests=JSON.parse(fs.readFileSync(0,'utf8'));
const results=requests.map(request=>{
  if(request.operation==='compress')return context.Graph.compress(request.value,false);
  // checked=true returns the decoded text before the application's XML-control cleanup.
  if(request.operation==='decompress')return context.Graph.decompress(request.value,false,true);
  throw Error('Unknown operation');
});
process.stdout.write(JSON.stringify(results));
