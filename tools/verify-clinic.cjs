// Run from the repository root with Playwright and Chromium or Edge installed.
const { chromium } = require('playwright');
const { spawn } = require('node:child_process');
const { createInterface } = require('node:readline');
const { mkdir } = require('node:fs/promises');
const path = require('node:path');

async function main() {
  const python = process.env.RC_PYTHON || (process.platform === 'win32' ? 'venv/Scripts/python.exe' : 'venv/bin/python');
  const server = spawn(python, ['-u', 'demo.py'], { cwd: process.env.RC_BACKEND || 'backend', windowsHide: true, stdio: ['ignore','pipe','ignore'] });
  const lines = createInterface({ input: server.stdout });
  let browser;
  try {
    let password;
    for await (const line of lines) {
      const match = line.match(/^Temporary demo password: (\S+)/);
      if (match) { password = match[1]; break; }
    }
    if (!password) throw Error('Synthetic account setup failed.');
    browser = await chromium.launch({ channel: process.env.RC_BROWSER || (process.platform === 'win32' ? 'msedge' : 'chromium') });
    const page = await browser.newPage({ viewport: {width: 1365, height: 920} });
    const origin = 'http://127.0.0.1:8000';
    for (let attempt=0; attempt<50; attempt++) {
      try { if ((await page.request.get(origin+'/health')).ok()) break; } catch {}
      await new Promise(resolve=>setTimeout(resolve,100));
    }
    await page.goto(origin + '/clinic/');
    await page.getByLabel('Staff email').fill('doctor@example.org');
    await page.getByLabel('Password').fill(password);
    await page.getByRole('button', {name:'Sign in'}).click();
    await page.getByRole('button', {name:/^Mira Sample/}).click();
    await page.getByRole('heading', {name:'Attention tracker'}).waitFor();
    const folder = path.resolve('docs/demo');
    await mkdir(folder, {recursive:true});
    await page.screenshot({path:path.join(folder, 'clinic-desk.png'), fullPage:true});
    await page.evaluate(()=>{window.print=()=>{document.body.dataset.printed="yes"}});
    await page.getByRole('button',{name:'Print / save PDF'}).click();
    await page.waitForFunction(()=>document.body.dataset.printed==="yes");
    await page.pdf({path:path.join(folder, 'follow-up.pdf'), preferCSSPageSize:true, printBackground:true});
    await page.getByText('Complete checkup', {exact:true}).click();
    await page.getByLabel('Checkup notes').fill('Synthetic follow-up completed.');
    await page.getByRole('button', {name:'Finalize checkup'}).click();
    await page.getByText('Checkup finalized.', {exact:true}).waitFor();
    await page.getByText('Previously prepared reports', {exact:true}).click();
    await page.locator('#saved button').last().click();
    await page.getByText('First follow-up.', {exact:true}).waitFor();
    console.log('Verified clinic sign-in, report, checkup finalization and snapshot reprint.');
  } finally {
    if (browser) await browser.close();
    server.kill();
  }
}
// Companion to the Android smoke test. Both clients use its running demo server.
async function completeAndroidFollowup() {
  const lines = createInterface({ input: process.stdin });
  const { value: password } = await lines[Symbol.asyncIterator]().next();
  lines.close();
  if (!password) throw Error('Missing temporary demo credential.');
  const browser = await chromium.launch({channel: process.env.RC_BROWSER || (process.platform === 'win32' ? 'msedge' : 'chromium')});
  try {
    const page = await browser.newPage();
    await page.goto('http://127.0.0.1:8000/clinic/');
    await page.getByLabel('Staff email').fill('doctor@example.org');
    await page.getByLabel('Password').fill(password);
    await page.getByRole('button', {name:'Sign in'}).click();
    await page.getByRole('button', {name:/^Mira Sample/}).click();
    await page.locator('#report').getByText(/EmulatorMeal/).first().waitFor();
    await page.getByText('Complete checkup', {exact:true}).click();
    await page.getByLabel('Checkup notes').fill('Emulator follow-up reviewed');
    await page.getByRole('button', {name:'Finalize checkup'}).click();
    await page.getByText('Checkup finalized.', {exact:true}).waitFor();
  } finally {
    await browser.close();
  }
}

const run = process.argv.includes('--android-return') ? completeAndroidFollowup : main;
run().catch(error => {console.error(error.message); process.exitCode=1});
