from pathlib import Path
import json, html, re, argparse
parser=argparse.ArgumentParser(description="Render a saved discussion as a standalone HTML reader")
parser.add_argument("input", type=Path)
parser.add_argument("--output", type=Path)
args=parser.parse_args()
source=args.input

d=json.loads(source.read_text()); e=lambda x:html.escape(str(x),quote=True)
def rich(s):
 s=e(s)
 return re.sub(r'\*\*([^\n]+?)\*\*',r'<strong>\1</strong>',s)
parts=[]
for i,m in enumerate(d['messages']):
 r=m['round_num']; a=m['sender_id']; sources=m.get('sources_used',[])
 evidence=''
 for s in sources:
  url=s.get('source',''); label=e(url)
  if url.startswith(('https://','http://')): label=f'<a href="{e(url)}" target="_blank" rel="noopener noreferrer">{label}</a>'
  evidence+=f'<div class="source">{label}<p>{e(s.get("content",""))}</p></div>'
 extra={k:v for k,v in m.items() if k not in ('content','sources_used')}
 parts.append(f'''<article data-round="{r}" data-agent="{e(a)}"><div class="label">MESSAGE {i+1} · {'INITIAL OPINION' if r==0 else 'ROUND '+str(r)}</div><h2>{e(a.replace('_',' ').title())}</h2><div class="route">Sent to: {e(', '.join(m.get('recipient_ids',[])).replace('_',' '))}</div><div class="content">{rich(m['content'])}</div><details><summary>Retrieved evidence ({len(sources)} passages)</summary>{evidence or 'No source passages recorded for this message.'}</details><details><summary>Message details and tool records</summary><pre>{e(json.dumps(extra,indent=2,ensure_ascii=False))}</pre></details></article>''')
options=''.join(f'<option value="{e(a)}">{e(a.replace("_"," ").title())}</option>' for a in d['config']['agent_ids'])
page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Football discussion reader</title><style>
*{box-sizing:border-box}body{margin:0;background:#f1f5f4;color:#18342e;font:16px/1.7 system-ui,sans-serif}header,main{max-width:980px;margin:auto;padding:28px}header{padding-bottom:15px}h1{font-size:34px;line-height:1.2;margin:8px 0}h2{font-size:23px;margin:4px 0}.label{font-size:12px;letter-spacing:1.2px;color:#52766c;font-weight:700}.muted,.route{color:#63746d;font-size:14px}.controls{position:sticky;top:0;background:#f1f5f4f5;z-index:1;padding:14px 28px;border-bottom:1px solid #cadbd5;display:flex;gap:10px;flex-wrap:wrap;justify-content:center}select,input,button{font:inherit;border:1px solid #b9ccc3;background:white;border-radius:8px;padding:9px;max-width:100%}input{flex:1;max-width:350px}article{background:#fff;border:1px solid #d6e2dc;border-radius:14px;margin:0 0 24px;padding:28px;box-shadow:0 4px 16px #17372c06}.content{white-space:pre-wrap;margin-top:24px;overflow-wrap:anywhere}details{border-top:1px solid #e0e8e4;margin-top:20px;padding-top:12px}summary{cursor:pointer;font-weight:600}.source{padding:14px 0;border-bottom:1px solid #e0e8e4;font-size:14px}.source p{white-space:pre-wrap}a{color:#176751;overflow-wrap:anywhere}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}#count{max-width:924px;margin:16px auto 0;padding:0 12px}[hidden]{display:none!important}@media(max-width:600px){header,main{padding:18px}article{padding:18px}.controls{position:static;padding:12px}h1{font-size:27px}}@media print{.controls{display:none}body{background:white}article{box-shadow:none}header,main{max-width:none}}
</style><header><div class="label">WEEK 3 · DISCUSSION READER</div><h1>Six analysts. Three discussion rounds.</h1><p>TOPIC</p><div class="muted">24 messages · MODEL · Saved discussion; model claims are not independently verified.</div></header><div class="controls"><select id="round" aria-label="Round"><option value="">All rounds</option><option value="0">Initial opinions</option><option value="1">Round 1</option><option value="2">Round 2</option><option value="3">Round 3</option></select><select id="agent" aria-label="Analyst"><option value="">All analysts</option>OPTIONS</select><input id="query" type="search" aria-label="Search messages" placeholder="Search message text…"><button id="reset">Reset filters</button></div><div id="count" class="muted" role="status"></div><main>CARDS</main><script>
const cards=[...document.querySelectorAll('article')],round=document.getElementById('round'),agent=document.getElementById('agent'),query=document.getElementById('query');function filter(){let n=0;cards.forEach(c=>{const show=(!round.value||c.dataset.round===round.value)&&(!agent.value||c.dataset.agent===agent.value)&&c.querySelector('.content').textContent.toLowerCase().includes(query.value.toLowerCase());c.hidden=!show;if(show)n++});document.getElementById('count').textContent=n+' of '+cards.length+' messages shown'}[round,agent,query].forEach(x=>x.addEventListener('input',filter));document.getElementById('reset').onclick=()=>{round.value=agent.value=query.value='';filter()};filter();</script></html>'''
page=page.replace('24 messages',f'{len(d["messages"])} messages')
page=page.replace('TOPIC',e(d['config']['topic'])).replace('MODEL',e(d['config']['llm_model'])).replace('OPTIONS',options).replace('CARDS',''.join(parts))
out=args.output or source.with_suffix('.html')
if out.resolve()==source.resolve(): raise ValueError('Output must differ from input')
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(page,encoding='utf-8')
assert page.count('<article ')==len(d['messages'])
assert all(e(m['sender_id']) in page for m in d['messages'])
print(f'Created {out} with {len(d["messages"])} messages.')
