// LinkedIn extractor. Run on a jobs-guest search page, NOT on the logged-in app.
//
// Why: the logged-in /jobs/search app virtualises its result list. Only about 7 of the 25 cards
// are ever rendered, the rest stay as empty <li data-occludable-job-id> shells, and programmatic
// scrolling (scrollTop or scrollIntoView) does not make LinkedIn fill them. LinkedIn also
// neuters sessionStorage reads in an injected context, so the accumulate-across-pages pattern
// used for Reed and CV-Library does not work there either.
//
// What works instead: LinkedIn's server-rendered guest endpoints.
//   Search: https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=..&location=..&f_TPR=r1209600[&f_WT=2]&start=N
//           10 fully rendered cards per call, paginate with start=0,10,20.
//   Advert: https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/<JOB_ID>
//           the full description as plain text, which the logged-in job page does not give.
//
// Run this on a search page, then read window.__acc. Rows are compact arrays:
//   [id, title, company, location, salary, posted]
// Salary is usually missing on LinkedIn cards, so most rows arrive salary_unknown and are kept for
// review. The posted date is read from the card's <time datetime> (language independent), with
// the visible relative age as a fallback.
(() => {
  window.__acc = window.__acc || [];
  const have = new Set(window.__acc.map(x => x[0]));
  let n = 0;
  document.querySelectorAll('li').forEach(li => {
    const a = li.querySelector('a[href*="/jobs/view/"]'); if (!a) return;
    const h = (a.getAttribute('href') || '').split('?')[0];
    const m = h.match(/-(\d{6,})$/) || h.match(/\/jobs\/view\/(\d+)/); if (!m) return;
    const id = m[1]; n++; if (have.has(id)) return;
    const raw = li.innerText || '';
    const lines = [...new Set(raw.split('\n').map(s => s.trim()).filter(Boolean))];
    const title = lines[0] || null;
    const tm = li.querySelector('time');
    const posted = (tm && tm.getAttribute('datetime')) || (tm && tm.innerText.trim()) ||
      (raw.match(/(\d+\s*(?:minute|hour|day|week|month)s?\s*ago)/i) || [])[1] || null;
    const salLine = lines.find(l => /[£€$]\s?\d|\d[\d.,\s]*\s?(?:€|EUR|USD|GBP|CHF|zł|kr)\b/.test(l)) || null;
    const salary = salLine;
    const rest = lines.slice(1).filter(l => l !== title && l !== salLine && !(tm && l === tm.innerText.trim())
      && !/(ago|vor .*|il y a .*)$/i.test(l)
      && !/^(Actively Hiring|Be an early applicant|Promoted)$/i.test(l));
    have.add(id);
    window.__acc.push([id, title, rest[0] || null, rest[1] || null, salary, posted]);
  });
  return 'cards=' + n + ' acc=' + window.__acc.length;
})()
