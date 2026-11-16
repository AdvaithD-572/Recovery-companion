'use strict';
const el=id=>document.getElementById(id);
let token='', roster=[], current='', visitKey='';
async function api(path,body){
 const res=await fetch('/api/v1/'+path,{method:body?'POST':'GET',cache:'no-store',headers:{'Content-Type':'application/json',Authorization:'Bearer '+token},body:body?JSON.stringify(body):undefined});
 if(!res.ok)throw Error((await res.json()).detail||'Request failed');
 return res.json();
}
function displayTime(value) {
 if (!value) return 'Unrecorded';
 if (value.length === 10) return value;
 const zoned = /(?:Z|[+-]\d\d:\d\d)$/.test(value) ? value : value+'Z';
 return new Intl.DateTimeFormat(undefined,{dateStyle:'medium',timeStyle:'short'}).format(new Date(zoned));
}
function node(tag,text){const n=document.createElement(tag);n.textContent=text;return n}
function bind(id,event,fn){el(id).addEventListener(event,async e=>{e.preventDefault();el('message').textContent='';const btn=e.submitter;if(btn)btn.disabled=true;try{await fn(new FormData(e.target instanceof HTMLFormElement?e.target:undefined))}catch(err){el('message').textContent=String(err.message)}finally{if(btn)btn.disabled=false}})}
function table(head,rows){const t=document.createElement('table'),h=t.createTHead().insertRow();for(const title of head)h.append(node('th',title));const b=t.createTBody();for(const row of rows){const tr=b.insertRow();for(const v of row)tr.append(node('td',v??'—'))}return t}
function showRoster(){const box=el('patients');box.replaceChildren();const q=el('search').value.toLowerCase();for(const p of roster.filter(p=>(p.name+' '+p.id).toLowerCase().includes(q))){const btn=node('button',p.name+' · '+(p.dob||p.id.slice(0,8)));btn.onclick=()=>openPatient(p.id).catch(err=>el('message').textContent=err.message);box.append(btn)}if(!box.children.length)box.append(node('p','No matching linked patients.'))}
async function openPatient(id,savedId){current=id;visitKey=crypto.randomUUID();el('selected').hidden=true;const {id:rid,report:r}=(savedId ? await api('care/reports/'+savedId) : await api('care/patients/'+id+'/reports',{}));const archive=await api('care/patients/'+id+'/reports');if(id!==current)return;
 const saved=el('saved');saved.replaceChildren();for(const snapshot of archive){const b=node('button',displayTime(snapshot.at)+' · '+snapshot.id.slice(0,8));b.onclick=()=>openPatient(id,snapshot.id).catch(err=>el('message').textContent=err.message);saved.append(b)}
 const select=el('amend').elements.visit;select.replaceChildren();for(const v of r.visits){const option=node('option',displayTime(v.at)+' · '+v.note);option.value=v.id;select.append(option)}el('amend').parentElement.hidden=!r.visits.length;
 el('clinical').hidden=Boolean(savedId)||el('clinical').dataset.role!=='clinician';el('attendance').hidden=Boolean(savedId);
 el('print').dataset.report=rid;
 document.documentElement.style.setProperty('--report-identity',JSON.stringify(r.name+' · '+rid));
 const d=el('report');d.replaceChildren(node('h2',r.name),node('p','Follow-up report · '+rid),node('p','Patient '+r.id+' · DOB '+(r.dob||'Unknown')+'\n'+(r.condition||'Condition unrecorded')+' · '+(r.procedure||'Procedure unrecorded')),node('p','From '+(r.from?displayTime(r.from):'first entry')+' through '+displayTime(r.as_of)+' · '+Intl.DateTimeFormat().resolvedOptions().timeZone),node('p','Allergies: '+(r.allergies?.join(', ')||'None recorded')),node('p','Height: '+(r.height_cm == null?'Unrecorded':r.height_cm+' cm')+' · Weight: '+(r.weight_kg == null?'Unrecorded':r.weight_kg+' kg')+' · Discharged: '+(r.discharged||'Unrecorded')),node('p','Chronic conditions: '+(r.chronic_diseases?.join(', ')||'None recorded')),node('h3','Patient-reported discharge instructions'),node('p',r.instructions.join('\n')||'None recorded'),node('h3','Medicines'),table(['Name','Dose','Schedule','Supply'],r.medicines.map(m=>[m.name,m.dose,[(m.schedule.times||[]).join(', ')||(m.compulsory===false?'As needed':'Unrecorded'),m.notes].filter(Boolean).join(' · '),m.remaining])),node('h3','Recovery history'));
 const summary=document.createElement('div');summary.className='summary';for(const [name,value] of [['Check-ins',r.events.filter(e=>e.type==='check-in').length],['Taken',r.events.filter(e=>e.type==='taken').length],['Skipped',r.events.filter(e=>e.type==='skipped').length],['Meals',r.events.filter(e=>e.type==='food').length]]){const tile=document.createElement('div');tile.append(node('strong',value),node('span',name));summary.append(tile)}d.insertBefore(summary,d.children[3]);
 const attention=document.createElement('section');attention.className='attention';attention.append(node('h3','Attention tracker'));for(const level of ['Critical','Needs review','Unable to assess']){const count=r.events.filter(e=>e.status===level).length;const line=document.createElement('div');const meter=document.createElement('meter');meter.min=0;meter.max=Math.max(1,r.events.filter(e=>['food','skipped'].includes(e.type)).length);meter.value=count;meter.setAttribute('aria-label',level);line.append(node('span',level),meter,node('b',count));attention.append(line)}d.insertBefore(attention,d.lastChild);
 if(r.events.length)d.append(table(['When','Event','Patient record','Attention'],r.events.map(e=>[displayTime(e.at)+(e.late?" (late entry)":""),e.type,e.detail,[e.status,e.reason,e.rule].filter(Boolean).join(' · ')])));else d.append(node('p','No entries in this interval.'));
 d.append(node('h3','Checkup history'));for(const v of r.visits)d.append(node('p',displayTime(v.at)+' · '+v.note));if(!r.visits.length)d.append(node('p','First follow-up.'));el('selected').hidden=false;el('empty').hidden=true}
bind('login','submit',async f=>{const s=await api('auth/clinician/login',Object.fromEntries(f));token=s.access_token;const r=await api('care/patients');roster=r.patients;el('clinicName').textContent=r.clinic;el('clinical').dataset.role=r.role;el('clinical').hidden=r.role!=='clinician';el('signin').hidden=true;el('workspace').hidden=false;el('logout').hidden=false;el('login').reset();showRoster()});
el('search').oninput=showRoster;el('logout').onclick=()=>location.reload();bind('print','click',async()=>{await api('care/reports/'+el('print').dataset.report+'/print',{});window.print()});
bind('attendance','click',async()=>{await api('care/patients/'+current+'/attendance',{});await openPatient(current);el('message').textContent='Arrival recorded.'});
bind('refresh','click',()=>openPatient(current));
bind('invite','submit',async f=>{const v=await api('care/invitations',Object.fromEntries(f));el('code').textContent='Share privately with this patient: '+v.code});
bind('visit','submit',async f=>{await api('care/patients/'+current+'/visits',{text:f.get('text'),request_id:visitKey});el('visit').reset();await openPatient(current);el('message').textContent='Checkup finalized.'});
bind('amend','submit',async f=>{await api('care/visits/'+f.get('visit')+'/amendments',{text:f.get('text')});el('amend').reset();await openPatient(current);el('message').textContent='Amendment saved.'});
bind('rule','submit',async f=>{await api('care/patients/'+current+'/rules',Object.fromEntries(f));el('rule').reset();el('message').textContent='Rule saved for future entries.'});
