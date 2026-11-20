import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {createHash} from "node:crypto";
const root=new URL("../src/",import.meta.url);
const get=p=>readFileSync(new URL(p,root),"utf8");
const meta=JSON.parse(get("vendor/gc-ui/provenance.json"));

test("Metrics uses a SHA256-pinned GoreeCloud UI alpha token source and MIT notice",()=>{
  assert.equal(meta.upstream,"https://github.com/GoreeCloud/gc-ui");
  assert.match(meta.upstreamCommit,/^[0-9a-f]{40}$/);
  assert.deepEqual(Object.keys(meta.sha256).sort(),["tokens.css","LICENSE"].sort());
  for(const [f,sha]of Object.entries(meta.sha256)){
    assert.match(sha,/^[0-9a-f]{64}$/);
    assert.equal(createHash("sha256").update(get("vendor/gc-ui/"+f)).digest("hex"),sha,f);
  }
  assert.match(get("vendor/gc-ui/LICENSE"),/MIT License/);
});
test("Lagoon is selected via source tokens and monitoring layout stays product-specific",()=>{
  const main=get("main.tsx"), css=get("styles.css");
  assert.ok(main.indexOf("import './vendor/gc-ui/tokens.css';")>=0);
  assert.ok(main.indexOf("import './styles.css';")>main.indexOf("import './vendor/gc-ui/tokens.css';"));
  const html=readFileSync(new URL("../index.html",import.meta.url),"utf8");
  assert.match(html,/<html lang="en" data-gc-accent="lagoon">/);
  for(const role of ["--gc-canvas","--gc-surface","--gc-text","--gc-brand",
    "--gc-on-brand","--gc-on-brand-container","--gc-focus-ring","--gc-positive"]){
    assert.ok(css.includes("var("+role+")"),"missing semantic role: "+role);
  }
  for(const name of [".sidebar{",".machine-card{",".network-grid{",".chart{",".login-screen{"]){
    assert.ok(css.includes(name),"Monitoring-specific composition removed: "+name);
  }
  assert.doesNotMatch(css, /--brand:\s*#[a-fA-F0-9]+/);
  assert.doesNotMatch(get("vendor/gc-ui/tokens.css"),/@import\s+(?:url\()?\s*["']?https?:\/\//i);
});
