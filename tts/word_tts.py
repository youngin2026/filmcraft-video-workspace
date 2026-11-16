#!/usr/bin/env python3
"""Selectable TTS voices + measured word timing + cumulative sentence captions."""
import argparse,asyncio,json,math,os,re,subprocess,unicodedata,wave
from pathlib import Path
import edge_tts
from tts import trust_environment_ca,run
CLI='/workspace/filmcraft/bin/filmcraft-cli'
HERE=Path(__file__).resolve().parent
ALIASES={'male':'ko-KR-InJoonNeural','male2':'ko-KR-HyunsuMultilingualNeural','female':'ko-KR-SunHiNeural'}
TICKS=254016000000

def normalize(s):
 return ''.join(c for c in unicodedata.normalize('NFKC',s) if c.isalnum()).casefold()

def sentences(text):
 # One sentence per line is deterministic; .!? also split prose on the same line.
 return [s.strip() for line in text.splitlines() for s in re.findall(r'[^.!?。！？]+(?:[.!?。！？]+[”’\"\']?|$)',line) if s.strip()]

def align_words(text,boundaries):
 words=text.split(); cleaned=[normalize(w) for w in words]
 usable=[b for b in boundaries if normalize(b['text'])]
 raw=''.join(normalize(b['text']) for b in usable)
 if raw!=''.join(cleaned):
  raise ValueError('TTS words differ from script; write numbers/abbreviations as spoken words and retry. No estimated timings were used. '+repr([b['text'] for b in usable]))
 spans=[];cursor=0
 for b in usable:
  n=len(normalize(b['text']));spans.append((cursor,cursor+n,b));cursor+=n
 result=[];cursor=0
 for original,clean in zip(words,cleaned):
  if not clean:continue
  end=cursor+len(clean);hits=[b for left,right,b in spans if left<end and right>cursor]
  # A single service token spanning multiple whitespace words has no exact internal timing.
  if any(left<cursor or right>end for left,right,b in spans if left<end and right>cursor):
   raise ValueError('Service returned a boundary spanning multiple script words; cannot time these words exactly.')
  result.append({'text':original.rstrip('.!?。！？'),'start':min(b['offset'] for b in hits)/1e7,'end':max(b['offset']+b['duration'] for b in hits)/1e7})
  cursor=end
 if not result:raise ValueError('No word boundaries returned')
 return result

async def synthesize(script,out,voice,rate,pitch,gap):
 trust_environment_ca();utterances=[];chunks=[];sample_offset=0
 for index,text in enumerate(sentences(script)):
  mp3=out/f'sentence-{index+1:03}.mp3';wav=mp3.with_suffix('.wav');events=[]
  c=edge_tts.Communicate(text,voice=voice,rate=rate,pitch=pitch,boundary='WordBoundary',proxy=os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy'))
  with mp3.open('wb') as f:
   async for chunk in c.stream():
    if chunk['type']=='audio':f.write(chunk['data'])
    elif chunk['type']=='WordBoundary':events.append(chunk)
  run(['ffmpeg','-v','error','-i',str(mp3),'-ar','48000','-ac','1','-c:a','pcm_s16le',str(wav)])
  with wave.open(str(wav),'rb') as f:n=f.getnframes();pcm=f.readframes(n)
  words=align_words(text,events);base=sample_offset/48000
  if any(w['end']>n/48000+0.05 for w in words):raise ValueError('Boundary exceeds decoded audio')
  for w in words:w['start']+=base;w['end']=min(w['end'],n/48000)+base
  utterances.append({'text':text,'audioStart':base,'audioEnd':base+n/48000,'speechEnd':words[-1]['end'],'words':words,'rawBoundaries':events})
  chunks.append(pcm);sample_offset+=n
  if index<len(sentences(script))-1:
   silence=round(gap*48000);chunks.append(b'\0\0'*silence);sample_offset+=silence
 with wave.open(str(out/'narration.wav'),'wb') as f:
  f.setnchannels(1);f.setsampwidth(2);f.setframerate(48000)
  for pcm in chunks:f.writeframes(pcm)
 run(['ffmpeg','-v','error','-i',str(out/'narration.wav'),'-c:a','libmp3lame','-b:a','192k',str(out/'narration.mp3')])
 states=[]
 for i,s in enumerate(utterances):
  for k,w in enumerate(s['words']):
   end=s['words'][k+1]['start'] if k+1<len(s['words']) else s['speechEnd']
   if end>w['start']:states.append({'sentence':i+1,'wordCount':k+1,'start':w['start'],'end':end,'text':' '.join(x['text'] for x in s['words'][:k+1])})
 return {'voice':voice,'rate':rate,'pitch':pitch,'durationSeconds':sample_offset/48000,'timingSource':'Edge TTS WordBoundary, seconds relative to decoded WAV','sentences':utterances,'states':states}

def timestamp(t):
 ms=round(t*1000);h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);s,ms=divmod(ms,1000)
 return f'{h:02}:{m:02}:{s:02},{ms:03}'

def filmcraft(a,out,timing):
 destination=a.save_as.resolve();destination.parent.mkdir(parents=True,exist_ok=True)
 src=[CLI]+(['--project',str(a.project.resolve())] if a.project else [])
 imported=json.loads(run(src+['--save-as',str(destination),'import',str(out/'narration.wav')]))
 if imported.get('errors'):raise RuntimeError(imported)
 log=[]
 def cmd(id,params):
  r=json.loads(run([CLI,'--project',str(destination),'--save','exec',id,json.dumps(params,ensure_ascii=False)]));log.append({'id':id,'params':params,'result':r});return r
 if not a.project:cmd('file.newSequence',{'name':'Word by word TTS','width':1080,'height':1920,'fps':30,'video':1,'audio':1})
 info=json.loads(run([CLI,'--project',str(destination),'inspect','sequence']))
 if a.project:
  cmd('sequence.addTracks',{'video':1,'audio':1})
  info=json.loads(run([CLI,'--project',str(destination),'inspect','sequence']))
 atrack=info['audio'][-1]['id'];vindex=len(info['video'])-1
 cmd('timeline.setTrack',{'track':atrack,'name':'TTS '+timing['voice']})
 cmd('timeline.place',{'item':imported['items'][0],'track':atrack,'seconds':a.start,'duration':{'seconds':timing['durationSeconds']},'video':False})
 fps=info['settings']['frame_rate']['num']/info['settings']['frame_rate']['den']
 rendered=[]
 for s in timing['states']:
  first=round((a.start+s['start'])*fps);last=round((a.start+s['end'])*fps)
  if last<=first:continue
  rendered.append({'startFrame':first,'endFrame':last,'text':s['text']})
  r=cmd('graphics.newText',{'text':s['text'],'position':[a.x,a.y],'box':[a.width,a.height],'size':a.size,'font':'Noto Sans CJK KR','fontStyle':'Bold','seconds':(last-first)/fps,'time':round(first*TICKS/fps),'track':vindex,'newClip':True})
  cmd('graphics.set',{'clip':r['clip'],'layer':r['layer'],'props':{'fill_color':'#ffffff','shadow':True,'align':'left'}})
 (out/'filmcraft-edits.json').write_text(json.dumps(log,ensure_ascii=False,indent=2))
 timing['project']=str(destination);timing['timelineStart']=a.start
 timing['renderedStates']=rendered;timing['captionFps']=fps;timing['timingQuantization']='nearest video frame; states shorter than one frame can merge'

async def refresh_voices():
 trust_environment_ca();v=await edge_tts.list_voices(proxy=os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy'))
 (HERE/'voices.json').write_text(json.dumps(v,ensure_ascii=False,indent=2))

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--list-voices',action='store_true');p.add_argument('--refresh-voices',action='store_true');p.add_argument('--locale',default='ko-KR',help='Use all to list every locale')
 p.add_argument('--script',type=Path);p.add_argument('--out',type=Path)
 p.add_argument('--timing',type=Path,help='Attach previously synthesized timing.json and narration.wav without another network call')
 p.add_argument('--voice',default='male',help='male, male2, female, or any exact voice ID from the catalog')
 p.add_argument('--rate',default='+0%');p.add_argument('--pitch',default='+0Hz');p.add_argument('--gap',type=float,default=.25)
 p.add_argument('--project',type=Path);p.add_argument('--save-as',type=Path);p.add_argument('--start',type=float,default=0)
 p.add_argument('--x',type=float,default=90);p.add_argument('--y',type=float,default=1300);p.add_argument('--width',type=float,default=900);p.add_argument('--height',type=float,default=480);p.add_argument('--size',type=float,default=64)
 a=p.parse_args()
 if a.refresh_voices:asyncio.run(refresh_voices())
 voices=json.loads((HERE/'voices.json').read_text())
 if a.list_voices:
  for v in voices:
   if a.locale=='all' or v['Locale']==a.locale:print(v['ShortName'],v['Gender'],v['Locale'])
  return
 if a.refresh_voices and not a.script:return
 if a.timing:
  if not a.save_as or a.save_as.exists():p.error('--timing requires a new --save-as project')
  if a.project and not a.project.is_file():p.error('Input project not found')
  out=a.timing.resolve().parent;timing=json.loads(a.timing.read_text())
  filmcraft(a,out,timing)
  a.timing.write_text(json.dumps(timing,ensure_ascii=False,indent=2))
  print('Attached measured audio and captions:',a.save_as)
  return
 if not a.script or not a.out:p.error('--script and --out are required')
 if a.gap<0 or a.start<0 or min(a.width,a.height,a.size)<=0:p.error('Invalid timing or caption dimensions')
 voice=ALIASES.get(a.voice,a.voice)
 if voice not in {v['ShortName'] for v in voices}:p.error('Unknown voice. Use --list-voices --locale all')
 if a.project and not a.save_as:p.error('--project requires --save-as')
 if a.save_as and a.save_as.exists():p.error('--save-as must be a new project file')
 if a.project and not a.project.is_file():p.error('Input project not found')
 text=a.script.read_text(encoding='utf-8-sig').strip()
 if not sentences(text):p.error('No readable sentences')
 # Stop instead of silently clipping paragraphs that exceed the subtitle box.
 # This conservative character estimate is a guard; inspect line wrapping on rendered frames.
 capacity=max(1,math.floor(a.width/a.size))*max(1,math.floor(a.height/(a.size*1.6)))
 if any(len(s)>capacity for s in sentences(text)):p.error('Sentence too long for caption box; split it into shorter sentences or enlarge the box')
 out=a.out.resolve()
 if out.exists() and any(out.iterdir()):p.error('Use a fresh output folder')
 out.mkdir(parents=True,exist_ok=True)
 timing=asyncio.run(synthesize(text,out,voice,a.rate,a.pitch,a.gap))
 (out/'script.txt').write_text(text,encoding='utf-8')
 (out/'narration.srt').write_text('\n'.join(f'{i}\n{timestamp(s["start"])} --> {timestamp(s["end"])}\n{s["text"]}\n' for i,s in enumerate(timing['states'],1)),encoding='utf-8')
 # Save measured timing before optional editor integration so it survives integration errors.
 (out/'timing.json').write_text(json.dumps(timing,ensure_ascii=False,indent=2))
 if a.save_as:filmcraft(a,out,timing)
 (out/'timing.json').write_text(json.dumps(timing,ensure_ascii=False,indent=2))
 print(json.dumps({k:v for k,v in timing.items() if k not in ['sentences','states']},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
