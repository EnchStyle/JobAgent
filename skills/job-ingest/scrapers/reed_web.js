// Reed WEBSITE extractor (remote-filtered search). Run on a reed.co.uk /jobs/remote-<keyword>-jobs
// page. The reed.co.uk website has a remote filter and shows a "Work from home" or
// "Part Remote" badge, so we can actually target remote roles. Stores cards in window.__jobs.
(() => {
  const seen = new Set(); const out = [];
  const skip=(()=>{try{return new Set((JSON.parse(sessionStorage.getItem('__known')||'[]')).map(String));}catch(e){return new Set();}})();
  const badges = new Set(['Easy Apply','See more','Featured','New','Expiring soon','Work from home']);
  document.querySelectorAll('a[href*="/jobs/"]').forEach(a => {
    const href = (a.getAttribute('href') || '').split('?')[0];
    const m = href.match(/\/(\d{6,})\b/); if (!m) return; const id = m[1];
    const title = (a.textContent || '').trim(); if (title.length < 5) return; if (seen.has(id) || skip.has(id)) return;
    let card = a.closest('article');
    if (!card) { card = a; for (let i = 0; i < 12 && card; i++) { const c = card.textContent || ''; if ((/£/.test(c) || / by /.test(c)) && card.querySelectorAll('a[href*="/jobs/"]').length) break; card = card.parentElement; } }
    if (!card) return; seen.add(id);
    const t = card.innerText || '';
    const lines = t.split('\n').map(s => s.trim()).filter(Boolean);
    const pb = (t.match(/((?:\d{1,2} [A-Z][a-z]+)|Today|Yesterday|Just now|\d+ (?:minute|hour|day|week)s? ago) by ([^\n]+)/) || []);
    // Reed shows relative dates ('4 days ago', '1 week ago'); convert to 'D Month' for normalize.py
    const MN = ['January','February','March','April','May','June','July','August','September','October','November','December'];
    const rel = (d) => { const x = new Date(); x.setDate(x.getDate() - d); return x.getDate() + ' ' + MN[x.getMonth()]; };
    if (pb[1]) { let mm; if (/^(Today|Just now)$/.test(pb[1]) || /(minute|hour)s? ago/.test(pb[1])) pb[1] = rel(0); else if (pb[1] === 'Yesterday') pb[1] = rel(1); else if ((mm = pb[1].match(/(\d+) days? ago/))) pb[1] = rel(+mm[1]); else if ((mm = pb[1].match(/(\d+) weeks? ago/))) pb[1] = rel(7 * (+mm[1])); }
    const salary = ((t.match(/£[^\n]*/) || [])[0] || '').replace(/\s+/g, ' ').trim() || null;
    let loc = null;
    for (const ln of lines) {
      if (ln === title || badges.has(ln) || /^£/.test(ln) || / by /.test(ln) || /Permanent|Contract|Temporary|full-time|part-time/i.test(ln) || /remote|work from home/i.test(ln)) continue;
      if (/,/.test(ln) || /London|Manchester|shire|Kingdom|Scotland|Wales|Bristol|Leeds|Birmingham|Edinburgh/.test(ln)) { loc = ln; break; }
    }
    // Remote only when the search itself was remote-filtered (/jobs/remote-...) or the card shows the
    // "Work from home" badge; the city searches are not remote-filtered, so their cards stay
    // unknown and the location gate flags them for a check when the advert is read.
    const remoteSearch = /\/jobs\/remote-/.test(location.pathname);
    const rmode = /part remote|hybrid/i.test(t + ' ' + title) ? 'hybrid'
      : ((remoteSearch || /work from home/i.test(t)) ? 'remote' : null);
    out.push({ id, url: 'https://www.reed.co.uk' + href, title, company: (pb[2] || '').trim() || null, location: loc, salary, posted: pb[1] || null, remote: rmode });
  });
  window.__jobs = out; return 'reed_web N=' + out.length;
})()
