'use strict';
const el = id => document.getElementById(id);
let access = '';
async function api(path, method = 'GET', body) {
  const headers = {'Content-Type': 'application/json'};
  if (access) headers.Authorization = 'Bearer ' + access;
  const res = await fetch('/api/v1/' + path, {method, headers, body: body && JSON.stringify(body), cache: 'no-store'});
  if (!res.ok) {
    if (res.status === 401 && access) { location.reload(); throw Error('Sign in again.'); }
    const detail = (await res.json()).detail;
    throw Error(typeof detail === 'string' ? detail : 'Check the details you entered.');
  }
  return res.status === 204 ? null : res.json();
}
function action(node, event, callback) {
  node.addEventListener(event, async e => {
    e.preventDefault();
    const button = e.submitter || (node.tagName === 'BUTTON' ? node : null);
    if (button) button.disabled = true;
    el('message').textContent = '';
    try { await callback(); }
    catch (err) { el('message').textContent = err.message; }
    finally { if (button && button.isConnected && !button.hidden) button.disabled = false; }
  });
}
function form(id, callback) {
  const node = el(id);
  action(node, 'submit', () => callback(Object.fromEntries(new FormData(node))));
}
function signedIn(token) {
  access = token;
  el('login').reset();
  el('signin').hidden = true;
  el('workspace').hidden = false;
  el('logout').hidden = false;
}
el('logout').onclick = () => location.reload();
window.addEventListener('pageshow', event => { if (event.persisted) location.reload(); });
