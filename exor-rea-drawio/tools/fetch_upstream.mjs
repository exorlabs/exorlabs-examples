import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';

const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const manifest=JSON.parse(await fs.readFile(path.join(root,'upstream-manifest.json'),'utf8'));
for(const entry of manifest.files){
  const destination=path.join(root,'upstream',entry.destination);
  let existing;
  try{existing=await fs.readFile(destination);}catch(error){if(error.code!=='ENOENT')throw error;}
  if(existing&&createHash('sha256').update(existing).digest('hex')===entry.sha256){
    console.log('Verified '+entry.destination);continue;
  }
  const url=`https://raw.githubusercontent.com/${entry.repository}/${entry.revision}/${entry.path}`;
  const response=await fetch(url,{signal:AbortSignal.timeout(30000)});
  if(!response.ok)throw Error(`Download failed: ${response.status} for ${entry.destination}`);
  const bytes=Buffer.from(await response.arrayBuffer());
  if(createHash('sha256').update(bytes).digest('hex')!==entry.sha256)throw Error('Digest mismatch: '+entry.destination);
  await fs.mkdir(path.dirname(destination),{recursive:true});
  await fs.writeFile(destination+'.part',bytes);await fs.rename(destination+'.part',destination);
  console.log('Downloaded '+entry.destination);
}
