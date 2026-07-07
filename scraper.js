<<<<<<< HEAD
const puppeteer = require('puppeteer');

async function scrape() {
  const browser = await puppeteer.launch({ headless: false });
  const page = await browser.newPage();

  const url = "https://www.industritorget.se/";

  await page.goto(url, { waitUntil: "domcontentloaded" });

  console.log("Vi är inne på sidan:", url);

  await page.waitForTimeout(5000);

  await browser.close();
}

=======
const puppeteer = require('puppeteer');

async function scrape() {
  const browser = await puppeteer.launch({ headless: false });
  const page = await browser.newPage();

  const url = "https://www.industritorget.se/";

  await page.goto(url, { waitUntil: "domcontentloaded" });

  console.log("Vi är inne på sidan:", url);

  await page.waitForTimeout(5000);

  await browser.close();
}

>>>>>>> 7f123d51918647eba740bee272440863e47d10d7
scrape();