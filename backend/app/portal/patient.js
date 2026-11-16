'use strict';
async function enter(path, data) {
  const session = await api(path, 'POST', data);
  access = session.access_token;
  const profile = await api('patients/me');
  el('name').textContent = profile.full_name; el('email').textContent = profile.email;
  el('register').reset(); signedIn(access);
}
form('login', data => enter('auth/patient/login', data));
form('register', data => enter('auth/patient/register', data));
form('remove', async data => {
  await api('patients/me','DELETE', data);
  access = ''; el('remove').reset(); el('name').textContent = ''; el('email').textContent = '';
  el('workspace').hidden = true; el('logout').hidden = true; el('signin').hidden = false;
  el('message').textContent = 'Your profile has been deleted.';
});
