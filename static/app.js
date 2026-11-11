'use strict';
const $ = id => document.getElementById(id);
const data = window.RESULTS;
let study = '', kind = '';
const kindNames = {rnaseq:'RNA-SEQ', scrnaseq:'SINGLE-CELL RNA-SEQ'};
const reports = data?.reports || [];
const reportUrl = report => report.url.split('/').map(encodeURIComponent).join('/');
function el(tag, text, cls) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (cls) element.className = cls;
  return element;
}
function createStudyButtons() {
  $('studies').replaceChildren();
  for (const s of [{id: '', name: '전체 연구'}, ...data.studies]) {
    const button = el('button', s.name, s.id === study ? 'active' : '');
    button.type = 'button';
    button.dataset.study = s.id;
    const count = reports.filter(r => !s.id || r.study === s.id).length;
    button.append(el('small', `${count}개 보고서`));
    button.setAttribute('aria-pressed', String(s.id === study));
    button.onclick = () => { study = s.id; render(); };
    $('studies').append(button);
  }
}
function render() {
  const studyKinds = new Map(data.studies.map(s => [s.id,s.kind]));
  const selected = data.studies.find(s => s.id === study);
  $('title').textContent = selected ? selected.name : '전체 보고서';
  $('kind').textContent = selected ? (kindNames[selected.kind] || selected.kind) : 'ALL REPORTS';
  // Keep the actual buttons mounted so keyboard focus survives filtering.
  for (const button of $('studies').querySelectorAll('button')) {
    button.hidden = !!kind && !!button.dataset.study && studyKinds.get(button.dataset.study) !== kind;
    const active = button.dataset.study === study;
    button.classList.toggle('active', active);
    button.setAttribute('aria-pressed', String(active));
  }
  const query = $('search').value.trim().toLowerCase();
  const visible = reports.filter(r => (!study || r.study === study) && (!kind || studyKinds.get(r.study) === kind) && `${r.name} ${r.path}`.toLowerCase().includes(query));
  $('count').textContent = `${visible.length}개 보고서`;
  $('reports').replaceChildren();
  for (const report of visible) {
    const card = el('article', undefined, 'file');
    const info = el('div', undefined, 'details');
    info.append(el('strong', report.name), el('p', report.path));
    const link = el('a', '보고서 열기 ↗', 'report-link');
    link.href = reportUrl(report);
    link.target = '_blank';
    link.rel = 'noopener';
    card.append(info, link);
    $('reports').append(card);
  }
  if (!visible.length) $('reports').append(el('p', '선택한 연구 또는 검색 조건에 해당하는 HTML 보고서가 없습니다.'));
}
if (!data) {
  $('reports').textContent = '보고서 목록을 불러오지 못했습니다. 서버 연결을 확인하고 새로고침해주세요.';
} else {
  for (const [value, label] of [[new Set(reports.map(r => r.study)).size, 'STUDIES WITH REPORTS'], [reports.length, 'HTML REPORTS']]) {
    const item = el('div');
    item.append(el('strong', value), el('span', label));
    $('stats').append(item);
  }
  document.querySelectorAll('[data-kind]').forEach(button => {
    button.onclick = () => {
      kind = button.dataset.kind; study = '';
      document.querySelectorAll('[data-kind]').forEach(b => { b.classList.toggle('active', b === button); b.setAttribute('aria-pressed', String(b === button)); });
      render();
    };
  });
  $('updated').textContent = `목록 갱신: ${data.generated.slice(0, 10)}`;
  $('search').oninput = render;
  createStudyButtons();
  render();
}
