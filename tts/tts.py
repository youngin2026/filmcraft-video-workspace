#!/usr/bin/env python3
"""UTF-8 script -> Korean narration, SRT and optional FilmCraft audio track."""
import argparse,asyncio,importlib,json,os,subprocess
from pathlib import Path
import edge_tts
CLI='/workspace/filmcraft/bin/filmcraft-cli'
def run(args):
 return subprocess.run(args,check=True,capture_output=True,text=True).stdout

def trust_environment_ca():
 # Extend certifi trust with the managed environment's CA; TLS verification stays on.
 ca=os.environ.get('SSL_CERT_FILE') or '/etc/ssl/certs/ca-certificates.crt'
 if Path(ca).is_file():
  for name in ['edge_tts.communicate','edge_tts.voices']:
   importlib.import_module(name)._SSL_CTX.load_verify_locations(cafile=ca)

async def synthesize(text,args,out):
 sub=edge_tts.SubMaker()
 speech=edge_tts.Communicate(text,voice=args.voice,rate=args.rate,pitch=args.pitch,boundary='SentenceBoundary',proxy=os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy'))
 tmp=out/'narration.partial.mp3'
 try:
  with tmp.open('wb') as f:
   async for chunk in speech.stream():
    if chunk['type']=='audio':f.write(chunk['data'])
    elif chunk['type'] in ('WordBoundary','SentenceBoundary'):sub.feed(chunk)
  if tmp.stat().st_size==0:raise RuntimeError('TTS returned no audio')
  tmp.replace(out/'narration.mp3')
  (out/'narration.srt').write_text(sub.get_srt(),encoding='utf-8')
 except BaseException:
  tmp.unlink(missing_ok=True)
  raise

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--script',required=True,type=Path)
 p.add_argument('--out',required=True,type=Path)
 p.add_argument('--voice',default='ko-KR-InJoonNeural')
 p.add_argument('--rate',default='+0%');p.add_argument('--pitch',default='+0Hz')
 p.add_argument('--project',type=Path);p.add_argument('--save-as',type=Path)
 p.add_argument('--start',type=float,default=0)
 a=p.parse_args()
 if bool(a.project)!=bool(a.save_as):p.error('--project and --save-as must be used together')
 if a.start<0:p.error('--start must be nonnegative')
 if a.project and (not a.project.is_file() or a.project.resolve()==a.save_as.resolve() or a.save_as.exists()):
  p.error('Input project must exist; --save-as must be a different, new file')
 text=a.script.read_text(encoding='utf-8-sig').strip()
 if not text:p.error('Script is empty')
 out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
 if any((out/n).exists() for n in ['narration.mp3','narration.wav','narration.srt','manifest.json']):p.error('Use a fresh output folder to preserve previous narration')
 trust_environment_ca();asyncio.run(synthesize(text,a,out))
 run(['ffmpeg','-v','error','-i',str(out/'narration.mp3'),'-ar','48000','-ac','1','-c:a','pcm_s16le',str(out/'narration.wav')])
 probe=json.loads(run(['ffprobe','-v','error','-show_entries','format=duration','-of','json',str(out/'narration.wav')]))
 duration=float(probe['format']['duration'])
 result={'provider':'edge-tts','voice':a.voice,'rate':a.rate,'pitch':a.pitch,'durationSeconds':duration,'script':str(a.script.resolve()),'srtTimeOrigin':'narration start, not timeline start','startSeconds':a.start,'files':['narration.mp3','narration.wav','narration.srt']}
 if a.project:
  a.save_as.parent.mkdir(parents=True,exist_ok=True)
  imported=json.loads(run([CLI,'--project',str(a.project.resolve()),'--save-as',str(a.save_as.resolve()),'import',str(out/'narration.wav')]))
  if imported.get('errors') or not imported.get('items'):raise RuntimeError(imported)
  def command(id,params):
   return json.loads(run([CLI,'--project',str(a.save_as.resolve()),'--save','exec',id,json.dumps(params)]))
  sequence=json.loads(run([CLI,'--project',str(a.save_as.resolve()),'inspect','sequence']))
  video_duration=0 # Prefer exact engine ticks; do not guess the sequence frame rate
  if 'duration' in sequence:video_duration=sequence['duration']/254016000000
  command('sequence.addTracks',{'video':0,'audio':1})
  sequence=json.loads(run([CLI,'--project',str(a.save_as.resolve()),'inspect','sequence']))
  track=sequence['audio'][-1]['id']
  command('timeline.setTrack',{'track':track,'name':'TTS Korean Male'})
  placed=command('timeline.place',{'item':imported['items'][0],'seconds':a.start,'duration':{'seconds':duration},'track':track,'video':False})
  result.update(project=str(a.save_as.resolve()),audioTrack=track,clips=placed['clips'])
  if video_duration and a.start+duration>video_duration:result['warning']='Narration extends beyond picture. Adjust picture timing before final export.'
 (out/'manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
