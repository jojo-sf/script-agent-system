#!/usr/bin/env node
/**
 * Screenshots every slide of every carousel HTML file.
 *
 * Output: output/carousels/screenshots/
 *   carousel_01_stat_bomb_slide_01.png
 *   carousel_01_stat_bomb_slide_02.png
 *   ... etc for all 10 carousels × 6–7 slides each
 *
 * Usage:
 *   node tools/screenshot_carousels.js
 */

const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const CAROUSEL_DIR  = path.join(__dirname, '../output/carousels');
const SCREENSHOT_DIR = path.join(CAROUSEL_DIR, 'screenshots');

async function main() {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });

  const files = fs.readdirSync(CAROUSEL_DIR)
    .filter(f => f.endsWith('.html'))
    .sort();

  console.log(`Found ${files.length} carousels\n`);

  const browser = await chromium.launch();

  for (const file of files) {
    const filePath = path.join(CAROUSEL_DIR, file);
    const baseName  = file.replace('.html', '');

    console.log(`→ ${file}`);

    const page = await browser.newPage();

    // Viewport bigger than carousel so layout renders correctly
    await page.setViewportSize({ width: 800, height: 700 });
    await page.goto(`file://${filePath}`);

    // Wait for Google Fonts + slide transition to settle
    await page.waitForTimeout(1500);

    // Read total slide count from the counter element ("1 / 7")
    const counterText = await page.textContent('#counter');
    const totalSlides = parseInt(counterText.split('/')[1].trim(), 10);
    console.log(`  ${totalSlides} slides`);

    // Make sure we're on slide 1
    const carousel = page.locator('#carousel');

    for (let i = 0; i < totalSlides; i++) {
      const slideNum = String(i + 1).padStart(2, '0');
      const outPath = path.join(SCREENSHOT_DIR, `${baseName}_slide_${slideNum}.png`);

      await carousel.screenshot({ path: outPath });
      process.stdout.write(`  slide ${slideNum} saved\r`);

      if (i < totalSlides - 1) {
        await page.click('#next');
        await page.waitForTimeout(550); // let transition finish
      }
    }

    await page.close();
    console.log(`  all ${totalSlides} slides done          `);
  }

  await browser.close();

  const saved = fs.readdirSync(SCREENSHOT_DIR).filter(f => f.endsWith('.png'));
  console.log(`\n✓ ${saved.length} PNGs saved to output/carousels/screenshots/`);
}

main().catch(err => { console.error(err); process.exit(1); });
