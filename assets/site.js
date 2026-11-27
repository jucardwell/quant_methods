// Fills in the parts of the site that depend on today's date or on the course
// data in course.js: This week, the tutorial and reading sidebars, and quizzes.
(function () {
  var C = window.COURSE;
  if (!C) return;

  function el(tag, attrs, html) {
    var e = document.createElement(tag);
    for (var k in attrs || {}) e.setAttribute(k, attrs[k]);
    if (html != null) e.innerHTML = html;
    return e;
  }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }
  function iso(d) {
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
  }
  function parse(s) { var p = s.split('-'); return new Date(+p[0], +p[1] - 1, +p[2]); }
  function addDays(d, n) { var x = new Date(d); x.setDate(x.getDate() + n); return x; }
  var MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  var DAY = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  function label(d) { return DAY[d.getDay()] + ' ' + MON[d.getMonth()] + ' ' + d.getDate(); }

  // Today in Chapel Hill, so the week flips at the same moment for everyone.
  var today = (function () {
    var q = new URLSearchParams(location.search).get('today');
    if (q) return parse(q);
    try {
      return parse(new Intl.DateTimeFormat('en-CA', { timeZone: 'America/New_York' }).format(new Date()));
    } catch (e) { var n = new Date(); return new Date(n.getFullYear(), n.getMonth(), n.getDate()); }
  })();
  var todayIso = iso(today);

  var rows = C.rows;
  function rowFor(dIso) {
    for (var i = 0; i < rows.length; i++) {
      var r = rows[i];
      if (r.date === dIso) return r;
      if (r.end && r.date <= dIso && dIso <= r.end) return r;
    }
    return null;
  }
  var caseNo = {};
  C.cases.forEach(function (c) { caseNo[c.date] = c.n; });

  // Slides are linked once their class day has arrived.
  document.querySelectorAll('a.slides-link[data-date]').forEach(function (a) {
    if (a.getAttribute('data-date') > todayIso) {
      var prev = a.previousSibling;
      if (prev && prev.nodeType === 3) prev.textContent = prev.textContent.replace(/ · $/, '');
      a.remove();
    }
  });
  document.querySelectorAll('table.schedule tr[data-date="' + todayIso + '"]').forEach(function (tr) { tr.classList.add('today'); });

  // ---- This week ---------------------------------------------------------
  var wk = document.getElementById('this-week');
  if (wk) {
    var dated = rows.filter(function (r) { return r.date; });
    var first = parse(dated[0].date), last = parse(dated[dated.length - 1].date);
    var d = today;
    if (d.getDay() === 6) d = addDays(d, 2);
    if (d.getDay() === 0) d = addDays(d, 1);
    if (d < first) d = first;
    var monday = addDays(d, 1 - d.getDay());
    var days = wk.querySelector('.week-days');
    var head = wk.querySelector('.week-label');
    var unitP = wk.querySelector('.week-unit');
    if (d > last) {
      var fin = rows.filter(function (r) { return r.kind === 'final'; })[0];
      head.textContent = 'After the last class';
      days.style.gridTemplateColumns = '1fr';
      days.appendChild(el('div', { 'class': 'day' },
        '<span class="day-date">Exam period</span><span class="day-topic">' + esc(fin ? fin.topic : 'Final project') + '</span>' +
        (fin && fin.in_class ? '<span class="day-sub">' + esc(fin.in_class) + '</span>' : '')));
    } else {
      var fri = addDays(monday, 4);
      var anyRow = null;
      [0, 2, 4].forEach(function (off) {
        var day = addDays(monday, off);
        var r = rowFor(iso(day));
        if (r && r.kind !== 'off') anyRow = anyRow || r;
        var cls = 'day', html = '';
        var dateTxt = label(day);
        if (!r) {
          cls += ' off';
          html = '<span class="day-date">' + dateTxt + '</span><span class="day-topic">No class</span>';
        } else if (r.kind === 'off') {
          cls += ' off';
          html = '<span class="day-date">' + dateTxt + '</span><span class="day-topic">No class</span>' +
            '<span class="day-sub">' + esc(r.topic.replace(/^No class:\s*/, '')) + '</span>';
        } else {
          if (r.kind === 'case') { cls += ' case'; dateTxt += ' ★'; }
          html = '<span class="day-date">' + dateTxt + '</span><span class="day-topic">' + esc(r.topic) + '</span>';
          if (r.in_class) html += '<span class="day-sub">' + esc(r.in_class) + '</span>';
          var links = [];
          (r.readings || []).forEach(function (it) {
            if (it.href) links.push('<a href="' + esc(it.href) + '">' + (it.external ? '' : 'Read: ') + esc(it.title) + '</a>');
            else if (it.soon) links.push('<span>Read: ' + esc(it.title) + '</span>');
          });
          if (r.tutorial && r.tutorial.href) links.push('<a href="' + r.tutorial.href + '">Tutorial</a>');
          if (r.kind === 'case') links.push('<a href="case_studies.html#case-study-' + caseNo[r.date] + '">Study guide</a>');
          if (r.slides && r.date <= todayIso) links.push('<a href="' + esc(r.slides) + '">Slides</a>');
          if (links.length) html += '<div class="day-links">' + links.join('') + '</div>';
        }
        if (r && r.due) html += '<span class="day-due' + (html.indexOf('day-links') < 0 ? '" style="margin-top:auto' : '') + '">Due: ' + esc(r.due) + '</span>';
        days.appendChild(el('div', { 'class': cls }, html));
      });
      var wkNo = anyRow ? anyRow.week : (rowFor(iso(monday)) || {}).week;
      var range = MON[monday.getMonth()] + ' ' + monday.getDate() + '–' +
        (fri.getMonth() !== monday.getMonth() ? MON[fri.getMonth()] + ' ' : '') + fri.getDate();
      head.textContent = (wkNo ? 'Week ' + wkNo + ' · ' : '') + range;
      if (anyRow && C.units[anyRow.unit]) unitP.textContent = 'Unit ' + anyRow.unit + ', ' + C.units[anyRow.unit].name;
    }
  }

  // ---- Which page is this? -----------------------------------------------
  var page = (location.pathname.split('/').pop() || 'index.html').replace(/\.html$/, '');
  var tutorials = C.tutorials.filter(function (t) { return t.ready; });
  var tIdx = -1;
  tutorials.forEach(function (t, i) { if (t.file === page) tIdx = i; });
  var sidebar = document.getElementById('quarto-sidebar-toc-left') || document.querySelector('nav#TOC') && document.querySelector('nav#TOC').parentNode;

  function sideBlock(title, inner) {
    return el('div', { 'class': 'side-block' }, '<span class="side-title">' + title + '</span>' + inner);
  }
  function classDays(test) {
    return rows.filter(test).map(function (r) {
      return '<a href="index.html#schedule">' + esc(r.label) + ', ' + esc(r.topic) + '</a>';
    }).join('');
  }

  // ---- Tutorial pages ------------------------------------------------------
  if (tIdx >= 0) {
    var t = tutorials[tIdx];
    var useRow = rows.filter(function (r) { return r.tutorial && r.tutorial.file === t.file; })[0];
    var h1 = document.querySelector('#title-block-header h1, main h1');
    if (h1 && /Concept \d+/.test(t.concept)) {
      var u = useRow && C.units[useRow.unit];
      h1.parentNode.insertBefore(el('span', { 'class': 'concept-line' }, esc(t.concept) + (u ? ' · Unit ' + useRow.unit + ', ' + esc(u.name) : '')), h1);
    }
    if (sidebar) {
      var grid = '';
      for (var k = tIdx - 4; k <= tIdx + 4; k++) {
        var s = tutorials[(k + tutorials.length * 2) % tutorials.length];
        grid += k === tIdx ? '<span class="here">' + esc(s.title) + '</span>' : '<a href="' + s.file + '.html">' + esc(s.title) + '</a>';
      }
      sidebar.insertBefore(sideBlock('Adjoining tutorials', '<div class="adjoining">' + grid + '</div>'), sidebar.firstChild);
      var used = classDays(function (r) { return r.tutorial && r.tutorial.file === t.file; });
      if (used) sidebar.appendChild(sideBlock('Used in class', used));
    }
    var main = document.querySelector('main');
    if (main) {
      var prev = tutorials[tIdx - 1], next = tutorials[tIdx + 1];
      var pager = el('div', { 'class': 'sheet-pager' });
      pager.innerHTML = (prev ? '<a href="' + prev.file + '.html"><small>← Previous</small><b>' + esc(prev.title) + '</b></a>' : '<span></span>') +
        (next ? '<a href="' + next.file + '.html"><small>Next →</small><b>' + esc(next.title) + '</b></a>' : '');
      main.appendChild(pager);
    }
  }

  // ---- Reading pages -------------------------------------------------------
  var rm = page.match(/^reading-(.+)$/);
  if (rm && sidebar) {
    var slug = rm[1];
    var hasIt = function (r) { return (r.readings || []).some(function (it) { return it.slug === slug; }); };
    var before = classDays(hasIt);
    if (before) sidebar.insertBefore(sideBlock('Read before', before), sidebar.firstChild);
    var seen = {}, goes = '';
    rows.filter(hasIt).forEach(function (r) {
      if (r.tutorial && r.tutorial.href && !seen[r.tutorial.file]) {
        seen[r.tutorial.file] = 1;
        goes += '<a href="' + r.tutorial.href + '">' + esc(r.tutorial.title) + '</a>';
      }
    });
    if (goes) sidebar.appendChild(sideBlock('Tutorials', goes));
  }

  // ---- Reading quizzes -----------------------------------------------------
  document.querySelectorAll('.reading-quiz[data-quiz]').forEach(function (box) {
    var quiz = C.quizzes[box.getAttribute('data-quiz')];
    if (!quiz) { box.remove(); return; }
    box.innerHTML = '';
    quiz.questions.forEach(function (q, qi) {
      var wrap = el('div', { 'class': 'quiz-q' });
      wrap.appendChild(el('p', {}, (qi + 1) + '. ' + esc(q.q)));
      var why = el('p', { 'class': 'quiz-why', hidden: '' });
      q.options.forEach(function (opt, oi) {
        var lab = el('label', { 'class': 'quiz-opt' });
        var input = el('input', { type: 'radio', name: 'q' + qi + '-' + box.getAttribute('data-quiz') });
        input.addEventListener('change', function () {
          wrap.querySelectorAll('.quiz-opt').forEach(function (o) { o.classList.remove('right', 'wrong'); });
          var right = oi === q.answer;
          lab.classList.add(right ? 'right' : 'wrong');
          why.className = 'quiz-why ' + (right ? 'right' : 'wrong');
          why.textContent = (right ? 'Right. ' : 'Not quite. ') + q.why;
          why.hidden = false;
        });
        lab.appendChild(input);
        lab.appendChild(el('span', {}, esc(opt)));
        wrap.appendChild(lab);
      });
      wrap.appendChild(why);
      box.appendChild(wrap);
    });
  });
})();
