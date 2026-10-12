import {pathToFileURL,fileURLToPath} from 'node:url';
import path from 'node:path';
if (!process.argv[2] || !process.argv[3]) throw Error('Usage: node ops/generate-listening-audio.mjs <transcripts.json> <espeak-ng.js>');
const {default:init}=await import(pathToFileURL(path.resolve(process.argv[3])).href);
import fs from 'node:fs';import {execFileSync} from 'node:child_process';import crypto from 'node:crypto';
const module=await init();const voice=new module.eSpeakNGWorker();voice.set_voice('pl');voice.set_rate(155);
const inputs=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
const directory=fileURLToPath(new URL('../backend/polskiflow/learning/static/polskiflow/audio/practice/',import.meta.url));fs.mkdirSync(directory,{recursive:true});
const manifest={engine:'eSpeak-NG Emscripten 0.3.5',voice:'pl',rate:155,created_at:new Date().toISOString().slice(0,10),origin:'original',created_for:'LingoFlow',clips:{}};
for(const [name,lines] of Object.entries(inputs)){
if(!['dialogue','b1','b2'].includes(name)||!Array.isArray(lines)||lines.some(line=>typeof line!=='string'||!line.trim())) throw Error('Invalid practice transcript input');
const texts={full:lines.join(' ')};if(name==='dialogue')lines.forEach((line,i)=>texts['fragment-'+i]=line);
for(const [part,text] of Object.entries(texts)){
const chunks=[];voice.synthesize(text,samples=>{if(samples.length)chunks.push(Buffer.from(samples.buffer,samples.byteOffset,samples.byteLength));});const pcm=Buffer.concat(chunks),wav=Buffer.alloc(44+pcm.length);wav.write('RIFF');wav.writeUInt32LE(wav.length-8,4);wav.write('WAVEfmt ',8);wav.writeUInt32LE(16,16);wav.writeUInt16LE(1,20);wav.writeUInt16LE(1,22);wav.writeUInt32LE(22050,24);wav.writeUInt32LE(44100,28);wav.writeUInt16LE(2,32);wav.writeUInt16LE(16,34);wav.write('data',36);wav.writeUInt32LE(pcm.length,40);pcm.copy(wav,44);
const id=name+'-'+part;fs.writeFileSync('/tmp/lf-'+id+'.wav',wav);const filename=id+'.m4a';execFileSync('/usr/bin/afconvert',['-f','m4af','-d','aac','-b','64000','/tmp/lf-'+id+'.wav',directory+'/'+filename]);
manifest.clips[id]={path:'polskiflow/audio/practice/'+filename,transcript_sha256:crypto.createHash('sha256').update(text).digest('hex'),sha256:crypto.createHash('sha256').update(fs.readFileSync(directory+'/'+filename)).digest('hex'),duration_seconds:pcm.length/44100};
}}
fs.writeFileSync(fileURLToPath(new URL('../backend/polskiflow/domain/practice_listening_media.json',import.meta.url)),JSON.stringify(manifest,null,2)+'\n');console.log(Object.keys(manifest.clips).length+' synthetic AAC clips generated');
