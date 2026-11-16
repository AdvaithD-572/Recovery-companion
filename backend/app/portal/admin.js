'use strict';
let offset = 0, query = '', clinicToDelete, directoryRequest = 0, profileRequest = 0;
function button(text, fn) {
  const node = document.createElement('button');
  node.type = 'button'; node.textContent = text;
  action(node, 'click', fn);
  return node;
}
async function clinics() {
  const rows = await api('admin/clinics');
  el('clinics').replaceChildren();
  if (!rows.length) el('clinics').textContent = 'No clinics yet.';
  for (const clinic of rows) {
    const line = document.createElement('div');
    line.className = 'directory-row';
    line.append(document.createTextNode(clinic.name), button('Delete ' + clinic.name, () => {
      clinicToDelete = clinic;
      el('consequence').textContent = 'Remove ' + clinic.name + ', disable its staff access and invitations, and disconnect its patients? Patient accounts and finalized records are retained.';
      el('confirm').returnValue = 'cancel';
      el('confirm').showModal();
    }));
    el('clinics').append(line);
  }
}
const labels = {full_name:'Full name',email:'Email',dob:'Date of birth',gender:'Gender',height_cm:'Height (cm)',weight_kg:'Weight (kg)',primary_condition:'Condition',surgery_type:'Procedure',discharge_date:'Discharge date',allergies:'Allergies',chronic_diseases:'Chronic conditions',preferred_language:'Language',onboarding_complete:'Discharge setup complete',clinic:'Linked clinic',id:'Patient ID'};
async function details(id) {
  const sequence = ++profileRequest;
  const data = await api('admin/patients/' + id);
  if (sequence !== profileRequest) return;
  const dl = el('fields'); dl.replaceChildren();
  for (const [key, label] of Object.entries(labels)) {
    const term = document.createElement('dt'), value = document.createElement('dd');
    term.textContent = label;
    const v = data[key];
    value.textContent = Array.isArray(v) ? v.join(', ') || 'None recorded' : v ?? 'Unrecorded';
    dl.append(term,value);
  }
  el('profile').hidden = false;
}
async function patients() {
  const sequence = ++directoryRequest;
  profileRequest++; el('profile').hidden = true; el('fields').replaceChildren();
  const result = await api('admin/patients?' + new URLSearchParams({offset,q:query}));
  if (sequence !== directoryRequest) return;
  el('people').replaceChildren();
  if (!result.patients.length) el('people').textContent = 'No matching profiles.';
  for (const p of result.patients) el('people').append(button(p.name + ' · ' + p.email, () => details(p.id)));
  el('prev').hidden = offset === 0; el('next').hidden = !result.more;
}
form('login', async data => {
  const session = await api('admin/login','POST',data);
  signedIn(session.access_token); await Promise.all([clinics(), patients()]);
});
form('create', async data => {
  await api('admin/clinics','POST',data); el('create').reset();
  await clinics(); el('message').textContent = 'Clinic created. Its clinician can sign in at the clinic desk.';
});
el('confirm').addEventListener('close', async () => {
  if (el('confirm').returnValue !== 'delete') return;
  try { await api('admin/clinics/' + clinicToDelete.id,'DELETE'); await Promise.all([clinics(),patients()]); el('message').textContent = 'Clinic deleted.'; }
  catch (err) { el('message').textContent = err.message; }
});
form('searchForm', async data => { query = data.q; offset = 0; await patients(); });
action(el('next'),'click',async () => { offset += 50; await patients(); });
action(el('prev'),'click',async () => { offset = Math.max(0,offset-50); await patients(); });
