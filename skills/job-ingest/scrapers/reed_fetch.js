// Reed bulk scraper (fetch + DOMParser). Run on any www.reed.co.uk page via javascript_tool.
// Reed pages are server rendered, so this needs no page rendering and no iframes: a dozen searches
// of up to 14 pages each run in a few minutes and the tab stays responsive (an iframe loop can freeze
// the tab). Pages past the last one return 404, which just ends that search.
//
// Before running, set window.__RURLS to the search paths from `search_plan.py` (for example
// "/jobs/remote-product-manager-jobs"), and optionally window.__SUB (RegExp: clear title mismatches
// from config/filters.md reject_titles) and window.__KNOWN (Set of ids already in jobs.db, from
// known_ids.py). Then window.__go(0, window.__RURLS.length) runs in the background; poll
// window.__prog ({i,n,done}) and window.__stat. Rows are in window.__rows (after the hard gates:
// title, location, pay) and window.__all (every card). Dump them as job-ingest SKILL.md describes.
// Date filter: dateCreatedOffset=LastThreeDays (use LastDay / LastWeek as the window requires).
(() => {
  const FLOOR = window.__FLOOR || 30000;          // set window.__FLOOR to the UK salary_floor in filters.md
  const OFFSET = window.__OFFSET || 'LastThreeDays';
  const SALARY_FROM = window.__SALARY_FROM || 22000; // board filter: floor x board_salary_factor (sources.md)
  const MN = ['January','February','March','April','May','June','July','August','September','October','November','December'];
  const rel = d => { const x = new Date(); x.setDate(x.getDate() - d); return x.getDate() + ' ' + MN[x.getMonth()]; };
  const per = { hour: 1800, day: 260, week: 52, month: 12, annum: 1, year: 1 };
  const topAnnual = s => { if (!s) return null;
    const nums = [...s.matchAll(/£\s?([\d,]+(?:\.\d+)?)\s?(k)?/gi)].map(m => parseFloat(m[1].replace(/,/g, '')) * (m[2] ? 1000 : 1));
    if (!nums.length) return null;
    const m = s.match(/per\s+(hour|day|week|month|annum|year)/i);
    return Math.max(...nums) * (per[(m ? m[1] : 'annum').toLowerCase()] || 1); };
  window.__stat = { tot: 0, dup: 0, known: 0, tf: 0, loc: 0, sal: 0, errs: [] };
  window.__seen = new Set(); window.__rows = []; window.__all = [];
  window.__prog = { i: 0, n: (window.__RURLS || []).length, done: false };
  window.__go = async (from, to) => {
    for (let i = from; i < to; i++) {
      window.__prog.i = i; const base = window.__RURLS[i]; const remoteSearch = /^\/jobs\/remote-/.test(base);
      for (let p = 1; p <= 14; p++) {
        let h = null;
        for (let t = 0; t < 3; t++) {
          const r = await fetch(base + '?salaryFrom=' + SALARY_FROM + '&dateCreatedOffset=' + OFFSET + '&sortBy=DisplayDate' + (p > 1 ? '&pageno=' + p : ''));
          if (r.status === 200) { h = await r.text(); break; }
          if (r.status === 404) break;                // past the last page
          window.__stat.errs.push(i + ':' + r.status); await new Promise(z => setTimeout(z, 5000));
        }
        if (!h) break;
        const arts = [...new DOMParser().parseFromString(h, 'text/html').querySelectorAll('article[data-qa="job-card"]')];
        for (const a of arts) {
          const id = (a.getAttribute('data-id') || '').replace(/\D/g, ''); if (!id) continue;
          window.__stat.tot++;
          if (window.__seen.has(id)) { window.__stat.dup++; continue; } window.__seen.add(id);
          if (window.__KNOWN && window.__KNOWN.has(id)) { window.__stat.known++; continue; }
          const q = s => { const e = a.querySelector(s); return e ? e.textContent.replace(/\s+/g, ' ').trim() : null; };
          const title = q('[data-qa="job-card-title"]'), by = q('[data-qa="job-posted-by"]') || '', sal = q('[data-qa="job-metadata-salary"]'),
                loc = q('[data-qa="job-metadata-location"]'), meta = q('[data-qa="job-metadata"]') || '';
          const mode = (meta.match(/(Remote|Hybrid|On-site)/i) || [])[1] || null;
          const t = a.querySelector('[data-qa="job-card-title"]'); const href = t && t.getAttribute('href');
          const pm = by.match(/^(.*?)\s+by\s+(.*)$/); let posted = null, company = null;
          if (pm) { company = pm[2]; const w = pm[1], k = (re) => w.match(re);
            posted = /^(Today|Just now)$/i.test(w) || /(minute|hour)/i.test(w) ? rel(0) : /Yesterday/i.test(w) ? rel(1)
              : k(/(\d+) days?/) ? rel(+k(/(\d+) days?/)[1]) : k(/(\d+) weeks?/) ? rel(7 * +k(/(\d+) weeks?/)[1]) : w; }
          const remote = (/remote/i.test(mode || '') || remoteSearch && !/hybrid|on-site/i.test(mode || '')) ? 'remote' : (/hybrid/i.test(mode || '') ? 'hybrid' : null);
          const row = { id, url: 'https://www.reed.co.uk' + (href || '/jobs/job/' + id), title, company, location: loc, salary: sal, posted, remote, mode };
          window.__all.push(row);
          if (window.__SUB && window.__SUB.test(title || '')) { window.__stat.tf++; continue; }
          const ta = topAnnual(sal); if (ta !== null && ta < FLOOR) { window.__stat.sal++; continue; }
          window.__rows.push(row);   // location is judged by scrape_ingest (location_allow), not here
        }
        if (arts.length < 20) break; await new Promise(z => setTimeout(z, 600));
      }
      await new Promise(z => setTimeout(z, 500));
    }
    window.__prog.done = true;
  };
  return 'reed_fetch ready: window.__go(0, ' + window.__prog.n + ')';
})()
