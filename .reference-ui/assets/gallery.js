(() => {
  const { items } = JSON.parse(document.getElementById('catalog').textContent);
  const grid = document.getElementById('grid');
  const search = document.getElementById('search');
  const filters = document.getElementById('filters');
  let platform = 'all';
  const element = (tag, text, className) => {
    const node = document.createElement(tag);
    if (text) node.textContent = text;
    if (className) node.className = className;
    return node;
  };
  const link = (label, href) => {
    const node = element('a', label);
    node.href = href;
    return node;
  };
  const render = () => {
    const query = search.value.trim().toLocaleLowerCase();
    const visible = items.filter(item => (platform === 'all' || item.platforms.includes(platform)) && [item.title, ...item.platforms, ...item.tags].join(' ').toLocaleLowerCase().includes(query));
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
      } else {
        preview.textContent = '프로토타입 열기';
        preview.classList.add('empty');
      }
      const meta = element('div', '', 'item-meta');
      const description = element('div');
      description.append(element('h2', item.title));
      const tags = element('div', '', 'tags');
      item.tags.forEach(tag => tags.append(element('span', tag, 'tag')));
      description.append(tags);
      meta.append(description, element('span', item.platforms.join(' / '), 'platform'));
      const links = element('nav', '', 'links');
      links.setAttribute('aria-label', item.title + ' 자료');
      for (const [label, href] of [['프로토타입', item.preview], ['디자인 규칙', item.design], ['토큰 JSON', item.tokens], ['출처와 검증', item.metadata]]) links.append(link(label, href));
      article.append(preview, meta, links);
      grid.append(article);
    }
    document.getElementById('count').textContent = visible.length + ' / ' + items.length + ' references';
    document.getElementById('empty').hidden = visible.length > 0;
  };
  for (const name of ['all', ...new Set(items.flatMap(item => item.platforms))]) {
    const button = element('button', name === 'all' ? '전체' : name);
    button.type = 'button';
    button.setAttribute('aria-pressed', String(name === platform));
    button.addEventListener('click', () => {
      platform = name;
      [...filters.children].forEach(child => child.setAttribute('aria-pressed', String(child === button)));
      render();
    });
    filters.append(button);
  }
  document.body.classList.toggle('dark', window.matchMedia('(prefers-color-scheme: dark)').matches);
  document.getElementById('theme').addEventListener('click', () => document.body.classList.toggle('dark'));
  search.addEventListener('input', render);
  render();
})();
