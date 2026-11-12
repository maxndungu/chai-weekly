// Renders https://eatta.co.ke/statistics in a headless browser (its figures load via JavaScript)
// and prints the Mombasa auction figures as markdown. Also lists the data/download URLs the
// page requests, so a lighter scraper can use them later.
import { chromium } from "playwright";

const url = "https://eatta.co.ke/statistics";
const browser = await chromium.launch();
const page = await browser.newPage();
const requests = [];
page.on("response", (r) => {
  const t = r.request().resourceType();
  if (["xhr", "fetch", "document"].includes(t) || /\.(json|csv|xlsx?|pdf)(\?|$)/i.test(r.url()))
    requests.push(`${r.status()} ${t} ${r.url()}`);
});
await page.goto(url, { waitUntil: "networkidle", timeout: 60000 });
await page.waitForFunction(() => !document.body.innerText.includes("Loading the latest figures"), null, { timeout: 30000 }).catch(() => {});

const text = await page.evaluate(() => document.querySelector("main")?.innerText || document.body.innerText);
const rows = await page.$$eval("table tr", (trs) => trs.map((tr) => [...tr.cells].map((c) => c.innerText.trim()).join(" | ")));
const links = await page.$$eval("a[href], button[data-href]", (els) =>
  els.map((e) => `${e.innerText.trim()} -> ${e.getAttribute("href") || e.dataset.href}`).filter((s) => /excel|pdf|xls|csv|report/i.test(s)));

const glance = text.split("\n").map((l) => l.trim()).filter(Boolean);
const start = glance.findIndex((l) => /^Sale \d+ Auction Data/.test(l));
const end = glance.findIndex((l) => /^Average price \(USD per kg\)/.test(l));
console.log(`\n## Mombasa auction (EATTA, rendered ${new Date().toISOString().slice(0, 10)}) <${url}>\n`);
console.log((start >= 0 ? glance.slice(start, end > start ? end : start + 25) : glance.slice(0, 40)).join(" · "));
console.log("\n| Sale | Date | Sold (kg) | Avg USD/kg |\n|---|---|---|---|");
for (const r of rows.slice(1, 7)) console.log(`| ${r.replace("Latest", " (latest)")} |`);
if (process.env.EATTA_DEBUG) console.log("\nData requests:\n" + requests.join("\n"));
await browser.close();
