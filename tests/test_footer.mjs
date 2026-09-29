import { readFileSync } from "fs";
import { JSDOM } from "jsdom";
const repo = new URL("..", import.meta.url).pathname;
const js = readFileSync(repo + "/index.html", "utf8").match(/<script>([\s\S]*?)<\/script>/)[1];
const data = JSON.parse(readFileSync(repo + "/mpt/data/progress.json", "utf8"));
const index = JSON.parse(readFileSync(repo + "/classrooms.json", "utf8"));
let failures = 0;
const check = (n, c) => { console.log((c ? "ok       " : "FAIL     ") + n); if (!c) failures++; };
async function run(lastRun) {
  const dom = new JSDOM('<div id="app"></div>', { url: "https://x/cp/?classroom=mpt", runScripts: "outside-only" });
  const files = { "mpt/data/progress.json": data, "classrooms.json": { ...index, last_run: lastRun } };
  dom.window.fetch = async (url) => {
    const p = new dom.window.URL(url, "https://x/cp/").pathname.replace("/cp/", "");
    return { ok: true, json: async () => files[p] };
  };
  dom.window.eval(js);
  await new Promise(r => setTimeout(r, 150));
  const doc = dom.window.document;
  return { text: doc.body.textContent, footer: doc.querySelector("footer"), links: [...doc.querySelectorAll("footer a")] };
}
let r = await run({ conclusion: "success", created_at: "2026-09-29T03:09:34Z" });
check("success: no per-assignment list", !r.text.includes("Оценки собраны"));
check("success: has Обновлено", r.text.includes("Обновлено:"));
check("success: date is a link to Actions", r.links.some(a => a.href.includes("publish-progress.yaml")));
check("success: no failure marker", !r.text.includes("с ошибкой"));
check("success: keeps pr hint", r.text.includes("pull request"));
r = await run({ conclusion: "failure", created_at: "2026-09-29T03:09:34Z" });
check("failure: indicator shown", r.text.includes("обновление с ошибкой"));
check("failure: indicator links to Actions", r.links.filter(a => a.href.includes("publish-progress.yaml")).length >= 2);
r = await run(null);
check("no last_run: falls back to generated_at", r.links.some(a => a.href.includes("publish-progress.yaml")));
process.exit(failures ? 1 : 0);
