const {chromium} = require('playwright');
const {spawn} = require('node:child_process');
const {createInterface} = require('node:readline');
const {once} = require('node:events');
const net = require('node:net');
const assert = require('node:assert/strict');

async function main() {
  const probe = net.createServer();
  probe.listen(0,'127.0.0.1'); await once(probe,'listening');
  const port = probe.address().port; await new Promise(resolve => probe.close(resolve));
  const origin = 'http://127.0.0.1:' + port;
  const server = spawn(process.env.RC_PYTHON || (process.platform==='win32'?'venv/Scripts/python.exe':'venv/bin/python'),
    ['-X','utf8','-u','demo.py'], {cwd:'backend',windowsHide:true,env:{...process.env, RC_DEMO_PORT:String(port)},stdio:['ignore','pipe','ignore']});
  let browser;
  try {
    let adminPassword, password;
    for await (const line of createInterface({input:server.stdout})) {
      if (line.startsWith('Temporary admin password: ')) adminPassword=line.split(' ').at(-1);
      if (line.startsWith('Temporary demo password: ')) { password=line.split(' ').at(-1);break; }
    }
    assert.ok(adminPassword && password);
    browser = await chromium.launch({channel:process.env.RC_BROWSER || (process.platform==='win32'?'msedge':'chromium')});
    const admin=await browser.newPage(), patient=await browser.newPage(), staff=await browser.newPage();
    await admin.goto(origin+'/clinic/'); await admin.getByRole('link',{name:'Station administrator'}).click();
    await admin.getByLabel('Administrator email').fill('admin@example.org');
    await admin.getByLabel('Password',{exact:true}).fill(adminPassword);await admin.getByRole('button',{name:'Sign in'}).click();
    await admin.getByText('Create a clinic',{exact:true}).click();
    await admin.getByLabel('Clinic name',{exact:true}).fill('Harbor Test Clinic');
    await admin.getByLabel('First clinician’s name').fill('Harbor Clinician');
    await admin.getByLabel('Clinician email').fill('harbor@example.org');
    await admin.getByLabel('Clinician password').fill(password);
    await admin.getByRole('button',{name:'Create clinic'}).click();
    await admin.getByText(/Clinic created\./).waitFor();
    await staff.goto(origin+'/clinic/');await staff.getByLabel('Staff email').fill('harbor@example.org');
    await staff.getByLabel('Password').fill(password);await staff.getByRole('button',{name:'Sign in'}).click();
    await staff.getByRole('heading',{name:'Harbor Test Clinic'}).waitFor();
    await patient.goto(origin+'/clinic/');await patient.getByRole('link',{name:'Patient account'}).click();
    await patient.getByText('Create my profile',{exact:true}).click();
    await patient.getByLabel('Full name').fill('Harbor Patient');
    await patient.getByLabel('Account email').fill('harborpatient@example.org');
    await patient.getByLabel('Choose password').fill(password);
    await patient.getByRole('button',{name:'Create profile'}).click();
    await patient.getByRole('heading',{name:'Harbor Patient'}).waitFor();
    await admin.getByLabel('Patient name or email').fill('Harbor Patient');await admin.getByRole('button',{name:'Search',exact:true}).click();
    await admin.getByRole('button',{name:/Harbor Patient ·/}).click();
    await admin.locator('#fields').getByText('harborpatient@example.org',{exact:true}).waitFor();
    await admin.getByRole('button',{name:'Delete Harbor Test Clinic'}).click();await admin.getByRole('button',{name:'Cancel'}).click();
    await admin.getByRole('button',{name:'Delete Harbor Test Clinic'}).click();
    await admin.getByRole('dialog').getByRole('button',{name:'Delete clinic',exact:true}).click();
    await admin.getByText('Clinic deleted.',{exact:true}).waitFor();
    await patient.getByText('Delete my profile',{exact:true}).click();await patient.getByLabel('Confirm your current password').fill(password);
    await patient.getByRole('button',{name:'Permanently delete my profile'}).click();
    await patient.getByText('Your profile has been deleted.').waitFor();
    await admin.getByRole('button',{name:'Search',exact:true}).click();
    await admin.getByText('No matching profiles.').waitFor();
    console.log('Verified administrator login, clinic creation, staff login, patient signup, profile lookup, deletion cancellation, clinic deletion and patient self-deletion in the browser.');
  } finally { if(browser) await browser.close(); server.kill(); }
}
main().catch(err=>{ console.error(err.message);process.exitCode=1; });
