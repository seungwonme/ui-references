(() => {
  const { items } = JSON.parse(document.getElementById('catalog').textContent);
  const grid = document.getElementById('grid');
  const search = document.getElementById('search');
  const filters = document.getElementById('filters');
  const tags = document.getElementById('tags');
  const root = document.documentElement;
  const labels = { all: '전체 레퍼런스', web: '웹', desktop: '데스크톱', mobile: '모바일' };
  let platform = 'all';
  let selectedTag = '';
  const element = (tag, text, className) => {
    const node = document.createElement(tag);
    if (text) node.textContent = text;
    if (className) node.className = className;
    return node;
  };
  const icon = name => {
    const shapes = {
      all: 'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z',
      web: 'M3 5h18v15H3z M3 10h18 M7 7.5h.01 M10 7.5h.01',
      desktop: 'M3 4h18v13H3z M12 17v4 M8 21h8',
      mobile: 'M7 2h10v20H7z M11 18h2',
      arrow: 'M6 18 18 6 M6 6h12v12',
      sun: 'M12 2v2 M12 20v2 M2 12h2 M20 12h2 M5 5l1.5 1.5 M17.5 17.5 19 19 M5 19l1.5-1.5 M17.5 6.5 19 5 M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0',
      moon: 'M20.5 13.5A9 9 0 0 1 10.5 3.5a9 9 0 1 0 10 10'
    };
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('aria-hidden', 'true');
    const path = document.createElementNS(svg.namespaceURI, 'path');
    path.setAttribute('d', shapes[name] || shapes.all);
    svg.append(path);
    return svg;
  };
  const link = (label, href) => {
    const node = element('a', label);
    node.href = href;
    return node;
  };
  const render = () => {
    const query = search.value.trim().toLocaleLowerCase();
    const visible = items.filter(item => (platform === 'all' || item.platforms.includes(platform)) && (!selectedTag || item.tags.includes(selectedTag)) && [item.title, ...item.platforms, ...item.platforms.map(name => labels[name] || name), ...item.tags].join(' ').toLocaleLowerCase().includes(query));
    grid.replaceChildren();
    grid.classList.toggle('single', visible.length === 1);
    for (const item of visible) {
      const article = element('article', '', 'reference');
      const preview = link('', item.preview);
      preview.className = 'preview';
      preview.setAttribute('aria-label', item.title + ' 프로토타입 열기');
      if (item.thumbnail) {
        const img = element('img');
        img.src = item.thumbnail;
        img.alt = item.title + ' 미리보기';
        img.loading = 'lazy';
        preview.append(img);
        const badge = element('span', '미리보기 열기', 'preview-label');
        badge.append(icon('arrow'));
        preview.append(badge);
      } else {
        preview.textContent = '프로토타입 열기';
        preview.classList.add('empty');
      }
      const content = element('div', '', 'item-content');
      content.append(element('div', item.platforms.join(' / '), 'platform'), element('h3', item.title));
      const itemTags = element('div', '', 'tags');
      item.tags.forEach(tag => itemTags.append(element('span', tag, 'tag')));
      content.append(itemTags);
      const links = element('nav', '', 'links');
      links.setAttribute('aria-label', item.title + ' 자료');
      for (const [label, href] of [['프로토타입 열기', item.preview], ['디자인 규칙', item.design], ['디자인 토큰', item.tokens], ['출처와 검증', item.metadata]]) {
        const node = link(label, href);
        node.append(icon('arrow'));
        links.append(node);
      }
      content.append(links);
      article.append(preview, content);
      grid.append(article);
    }
    document.getElementById('count').textContent = visible.length === items.length ? String(items.length).padStart(2, '0') : visible.length + ' / ' + items.length;
    document.getElementById('empty').hidden = visible.length > 0;
    document.getElementById('clear').hidden = !query && platform === 'all' && !selectedTag;
    document.getElementById('view-label').textContent = labels[platform] || platform;
    for (const button of filters.children) button.setAttribute('aria-pressed', String(button.dataset.platform === platform));
    for (const button of tags.children) button.setAttribute('aria-pressed', String(button.dataset.tag === selectedTag));
  };
  for (const name of ['all', ...new Set(items.flatMap(item => item.platforms))]) {
    const button = element('button');
    button.type = 'button';
    button.dataset.platform = name;
    button.append(icon(name), element('span', labels[name] || name), element('span', String(name === 'all' ? items.length : items.filter(item => item.platforms.includes(name)).length), 'filter-count'));
    button.addEventListener('click', () => { platform = name; render(); });
    filters.append(button);
  }
  for (const name of [...new Set(items.flatMap(item => item.tags))].sort()) {
    const button = element('button', name);
    button.type = 'button';
    button.dataset.tag = name;
    button.addEventListener('click', () => { selectedTag = selectedTag === name ? '' : name; render(); });
    tags.append(button);
  }
  const preference = (name, value) => {
    try { if (value === undefined) return localStorage.getItem('reference-ui-' + name); localStorage.setItem('reference-ui-' + name, value); } catch { /* The UI also works when storage is unavailable. */ }
    return null;
  };
  const theme = document.getElementById('theme');
  const setTheme = dark => {
    root.classList.toggle('dark', dark);
    theme.replaceChildren(icon(dark ? 'sun' : 'moon'));
    const label = dark ? '밝은 테마로 전환' : '어두운 테마로 전환';
    theme.setAttribute('aria-label', label);
    theme.title = label;
  };
  const savedTheme = preference('theme');
  setTheme(savedTheme ? savedTheme === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches);
  theme.addEventListener('click', () => { const dark = !root.classList.contains('dark'); setTheme(dark); preference('theme', dark ? 'dark' : 'light'); });
  const material = document.getElementById('material');
  const setMaterial = flat => { root.classList.toggle('flat', flat); material.setAttribute('aria-pressed', String(!flat)); material.textContent = flat ? '단색' : '글래스'; };
  setMaterial(preference('material') === 'flat');
  material.addEventListener('click', () => { const flat = !root.classList.contains('flat'); setMaterial(flat); preference('material', flat ? 'flat' : 'glass'); });
  const reset = () => { search.value = ''; platform = 'all'; selectedTag = ''; render(); search.focus(); };
  document.getElementById('reset').addEventListener('click', reset);
  document.getElementById('clear').addEventListener('click', reset);
  document.addEventListener('keydown', event => {
    if (event.key === '/' && !event.isComposing && !event.metaKey && !event.ctrlKey && !event.altKey && !event.target.closest('input,textarea,[contenteditable="true"]')) { event.preventDefault(); search.focus(); }
  });
  search.addEventListener('input', render);
  render();
})();
