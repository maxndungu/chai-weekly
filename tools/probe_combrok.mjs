import { chromium } from "playwright";
const browser = await chromium.launch();
const page = await browser.newPage();
const seen = [];
page.on("response", async (r) => {
  const t = r.request().resourceType();
  if (!["xhr", "fetch"].includes(t) && !/\.(json|csv)(\?|$)/i.test(r.url())) return;
  let body = ""; try { body = await r.text(); } catch {}
  seen.push(`${r.status()} ${t} ${r.url()}\n${body.slice(0, 2500)}`);
});
await page.goto("https://combrok.co.ke/market-reports?tea=ctc&src=auction&year=2026&from=1&to=46", { waitUntil: "networkidle", timeout: 90000 });
await page.waitForTimeout(4000);
console.log("=== RESPONSES\n" + seen.join("\n---\n"));
const rows = await page.$$eval("table tr", (trs) => trs.slice(0, 8).map((tr) => [...tr.cells].map((c) => c.innerText.trim()).join(" | ")));
console.log("=== TABLE\n" + rows.join("\n"));
const links = await page.$$eval("a[href]", (as) => as.map((a) => a.innerText.trim().slice(0, 40) + " -> " + a.href).filter((s) => /term|legal|privacy|disclaim|copyright|condition/i.test(s)));
console.log("=== LEGAL LINKS\n" + links.join("\n"));
const scripts = await page.$$eval("script[src]", (s) => s.map((x) => x.src));
console.log("=== SCRIPTS\n" + scripts.join("\n"));
for (const u of links.map((l) => l.split(" -> ")[1]).slice(0, 3)) {
  await page.goto(u, { waitUntil: "networkidle", timeout: 60000 }).catch(() => {});
  console.log("=== PAGE " + u + "\n" + (await page.evaluate(() => document.body.innerText)).slice(0, 6000));
}
await browser.close();
