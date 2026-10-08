// CV-Library results extractor. Run on a cv-library.co.uk search page via javascript_tool.
// Pages: add &page_number=N to the search url (the site ignores 'page'); &posted=3 limits to the last 3 days.
// Stores all cards in window.__jobs and returns the count. Read them back as job-ingest SKILL.md
// describes: accumulate across page clicks, then dump the JSON into a <pre> and use get_page_text.
(() => {
  const seen = new Set(); const out = [];
  const skip=(()=>{try{return new Set((JSON.parse(sessionStorage.getItem('__known')||'[]')).map(String));}catch(e){return new Set();}})();
  const badges = new Set(['Featured','Easy Apply','Expiring soon','Permanent','Contract','Temporary','Part Time','Full Time','Also in other locations']);
  document.querySelectorAll('a[class*="JobCard_titleText"]').forEach(a => {
    const m = (a.getAttribute('href') || '').match(/\/job\/(\d+)/); if (!m) return;
    const id = m[1]; if (seen.has(id) || skip.has(id)) return;
    let card = a; for (let i = 0; i < 8 && card; i++) { if (String(card.className || '').includes('Card_card')) break; card = card.parentElement; }
    if (!card) return; seen.add(id);
    const t = card.innerText || '';
    const lines = t.split('\n').map(s => s.trim()).filter(Boolean);
    const title = (a.textContent || '').trim(); let loc = null;
    for (const ln of lines) { if (ln === title || /^Posted/.test(ln) || /£/.test(ln) || badges.has(ln)) continue;
      if (/\(\d+ miles?\)/.test(ln) || /,/.test(ln) || /London|Remote|Kingdom|shire|Scotland|Wales/.test(ln)) { loc = ln; break; } }
    out.push({ id, url: 'https://www.cv-library.co.uk/job/' + id, title,
      company: ((t.match(/\bby ([^\n]+)/) || [])[1] || '').trim() || null, location: loc,
      salary: ((t.match(/£[^\n]*/) || [])[0] || '').replace(/\s+/g, ' ').trim() || null,
      // The site shows 'Posted 2 days ago by <company>', 'Posted yesterday by ...' or, on older layouts, dd/mm/yyyy.
      posted: (t.match(/Posted\s+(\d{2}\/\d{2}\/\d{4})/) || t.match(/Posted\s+(.+?)\s+by\s/) || [])[1] || null,
      easyApply: /Easy Apply/.test(t) });
  });
  window.__jobs = out; return 'cv_library N=' + out.length;
})()
