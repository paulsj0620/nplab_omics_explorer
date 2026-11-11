// Optional real Chromium QA. All requests are fulfilled with synthetic/local source.
const {test,expect} = require('@playwright/test');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname,'../static');
const synthetic = {generated:'2000-01-01', studies:[{id:'demo',name:'Example study',kind:'rnaseq'}],
  reports:[{study:'demo',name:'Example study',path:'home/index.html',url:'reports/demo/home/index.html'}]};
async function openPortal(page) {
  await page.route('**/*',route => {
    const url=new URL(route.request().url()), name=url.pathname.replace('/results/','') || 'index.html';
    if (name==='catalog.js') return route.fulfill({contentType:'text/javascript',body:'window.RESULTS='+JSON.stringify(synthetic)});
    if (!['index.html','style.css','theme.css','nav.css','app.js','nav.js','favicon.svg'].includes(name)) return route.abort();
    const types={'.html':'text/html','.css':'text/css','.js':'text/javascript','.svg':'image/svg+xml'};
    return route.fulfill({contentType:types[path.extname(name)],body:fs.readFileSync(path.join(root,name))});
  });
  await page.goto('http://example.test/results/');
  await expect(page.locator('[data-drag-nav]')).toHaveAttribute('data-omics-nav','ready');
}
async function drag(page,from,to,finish=true) {
  const a=await from.boundingBox(), b=await to.boundingBox();
  await page.mouse.move(a.x+a.width/2,a.y+a.height/2); await page.mouse.down();
  await page.mouse.move(b.x+b.width/2,b.y+b.height/2,{steps:8});
  if (finish) await page.mouse.up();
}
async function assertIndicator(page,button) {
  await expect.poll(async () => {
    const a=await button.boundingBox(), b=await page.locator('.nav-selection-indicator').boundingBox();
    return b ? Math.max(...['x','y','width','height'].map(k => Math.abs(a[k]-b[k]))) : 999;
  }).toBeLessThan(1);
}

for (const [width,height] of [[1920,1080],[1920,900],[1280,800],[1100,720],[600,800]]) {
  test(`portal geometry, click, drag, keyboard and screenshot ${width}x${height}`,async ({page},info) => {
    await page.setViewportSize({width,height}); await openPortal(page);
    const buttons=page.locator('[data-drag-nav] > button');
    await buttons.nth(1).click(); await assertIndicator(page,buttons.nth(1));
    expect(await page.locator('.nav-selection-indicator').evaluate(e => getComputedStyle(e).transitionDuration)).toContain('0.26s');
    await drag(page,buttons.nth(1),buttons.nth(2),false);
    await expect(buttons.nth(1)).toHaveAttribute('aria-pressed','true');
    await expect(page.locator('.nav-drag-indicator')).toBeVisible();
    await page.mouse.up(); await expect(buttons.nth(2)).toHaveAttribute('aria-pressed','true');
    await assertIndicator(page,buttons.nth(2));
    await buttons.nth(0).focus(); await page.keyboard.press('Enter'); await assertIndicator(page,buttons.nth(0));
    await drag(page,buttons.nth(0),buttons.nth(2),false); await page.keyboard.press('Escape'); await page.mouse.up();
    await expect(buttons.nth(0)).toHaveAttribute('aria-pressed','true');
    expect(await page.evaluate(() => document.documentElement.scrollWidth<=document.documentElement.clientWidth)).toBe(true);
    await page.screenshot({path:info.outputPath(`portal-${width}-${height}.png`),fullPage:true});
  });
}
test('hidden tabs, language width changes, resize cancellation and reduced motion',async ({page}) => {
  await openPortal(page);
  const buttons=page.locator('[data-drag-nav] > button');
  await buttons.nth(1).evaluate(e => { e.textContent='RNA sequencing reports'; });
  await buttons.nth(1).click(); await assertIndicator(page,buttons.nth(1));
  await buttons.nth(2).evaluate(e => {e.hidden=true;});
  await drag(page,buttons.nth(1),buttons.nth(0),false);
  await page.setViewportSize({width:1100,height:720}); await page.mouse.up();
  await expect(buttons.nth(1)).toHaveAttribute('aria-pressed','true'); await assertIndicator(page,buttons.nth(1));
  await page.emulateMedia({reducedMotion:'reduce'});
  expect(await page.locator('.nav-selection-indicator').evaluate(e => getComputedStyle(e).transitionDuration)).toBe('0s');
});
test('legacy report navigation follows original link on drag release, retaining query',async ({page}) => {
  await page.route('**/*',route => route.fulfill({contentType:'text/html',body:'<p>Example destination</p>'}));
  await page.goto('http://example.test/results/reports/demo/home/index.html');
  await page.setContent('<html><head></head><body id="page-top"><nav class="menu_item_box"><a href="../home/index.html"><span class="menu_item active">Overview</span></a><a href="../deg/index.html?d=2"><span class="menu_item">DEG</span></a></nav></body></html>');
  for (const file of ['theme.css','nav.css']) await page.addStyleTag({content:fs.readFileSync(path.join(root,file),'utf8')});
  await page.addScriptTag({content:fs.readFileSync(path.join(root,'nav.js'),'utf8')});
  const links=page.locator('.menu_item_box > a');
  await drag(page,links.nth(0),links.nth(1),false);
  expect(page.url()).toContain('/home/index.html');
  await page.mouse.up(); await expect(page).toHaveURL('http://example.test/results/reports/demo/deg/index.html?d=2');
});
