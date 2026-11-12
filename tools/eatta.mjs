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

console.log(`# EATTA statistics (rendered ${new Date().toISOString().slice(0, 10)})\n`);
console.log("## Page text\n\n" + text.split("\n").filter(Boolean).slice(0, 80).join("\n"));
console.log("\n## Table rows\n\n" + rows.slice(0, 15).map((r) => `- ${r}`).join("\n"));
console.log("\n## Download links\n\n" + (links.join("\n") || "(none found)"));
console.log("\n## Data requests\n\n" + requests.join("\n"));
await browser.close();
