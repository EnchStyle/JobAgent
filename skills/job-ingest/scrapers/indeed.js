// Indeed extractor. Read-only, low volume. Run on an indeed.com/jobs?q=..&l=..&fromage=14 page.
// Accumulates compact dicts in sessionStorage '__acc' and exposes them as window.__acc.
(() => {
  let acc=[]; try{acc=JSON.parse(sessionStorage.getItem('__acc')||'[]');}catch(e){}
  const have=new Set(acc.map(x=>x.id));
  const skip=(()=>{try{return new Set((JSON.parse(sessionStorage.getItem('__known')||'[]')).map(String));}catch(e){return new Set();}})();
  let n=0;
  document.querySelectorAll('[data-jk]').forEach(el=>{
    const id=el.getAttribute('data-jk'); if(!id) return; n++; if(have.has(id)||skip.has(id)) return;
    const card=el.closest('li')||el.closest('.job_seen_beacon')||el;
    const q=s=>{const x=card.querySelector(s);return x?x.innerText.trim():null;};
    const t=card.innerText||'';
    const title=q('h2 span[title]')||q('h2')||(el.innerText||'').trim();
    const loc=q('[data-testid="text-location"]');
    const sal=((t.match(/[£€$]\s?\d[^\n]*|\d[\d.,\s]*\s?(?:€|EUR|USD|GBP|CHF)[^\n]*/)||[])[0]||'').trim()||null;
    const remote=/remote|work from home/i.test((loc||'')+' '+t)?(/hybrid/i.test((loc||'')+' '+t)?'hybrid':'remote'):(/hybrid/i.test(t)?'hybrid':null);
    have.add(id);
    acc.push({id,title,company:q('[data-testid="company-name"]'),location:loc,salary:sal,
      posted:(t.match(/(\d+\+?\s*days?\s*ago|vor\s+\d+\+?\s*Tag\w*|il y a\s+\d+\s*jours?|Just posted|Today|Heute)/i)||[])[1]||null,remote,easyApply:/Easily apply/i.test(t)});
  });
  sessionStorage.setItem('__acc',JSON.stringify(acc));
  window.__acc=acc;
  return 'indeed cards='+n+' acc='+acc.length;
})()
