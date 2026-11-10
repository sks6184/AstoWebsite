// Offline runtime protocol checks for the actual template script. No browser/network calls.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync('templates/chat/ask.html', 'utf8').split('<script>')[1].split('</script>')[0];

async function scenario(failure) {
  let submit, poll, resolvePost;
  const requests = [], redirects = [];
  const fields = [
    {name: 'csrfmiddlewaretoken', value: 'synthetic-csrf', tagName: 'INPUT'},
    {name: 'request_id', value: 'synthetic-uuid', tagName: 'INPUT'},
    {name: 'chart_id', value: '42', tagName: 'SELECT'},
    {name: 'answer_language', value: 'English', tagName: 'SELECT'},
    {name: 'question', value: 'Synthetic question', tagName: 'TEXTAREA'},
    {tagName: 'BUTTON'}
  ];
  const label = {textContent: ''};
  const overlay = {hidden: true, querySelector: () => label};
  const form = {action: '/chat/ask/', querySelector: () => null, querySelectorAll: () => fields,
    addEventListener: (name, callback) => { submit = callback; }};
  const context = {
    document: {querySelector: selector => selector === '[data-ask-form]' ? form : overlay,
      body: {classList: {add() {}, remove() {}}}},
    FormData: class {
      constructor() { this.values = new Map(fields.filter(f => f.name && !f.disabled).map(f => [f.name, f.value])); }
      get(name) { return this.values.get(name); }
    },
    window: {setInterval: callback => { poll = callback; return 1; }, clearInterval() {},
      setTimeout: callback => callback(), location: {assign: url => redirects.push(url)}},
    fetch: async (url, options) => {
      requests.push({url, options});
      if (options.method === 'POST') {
        if (failure) throw new Error('Synthetic network failure');
        return new Promise(resolve => { resolvePost = resolve; });
      }
      return {ok: true, json: async () => ({label: 'Checking requested periods'})};
    },
    DOMParser: class {}, encodeURIComponent
  };
  vm.runInNewContext(source, context);
  const finished = submit({preventDefault() {}});
  if (!failure) {
    await poll();
    assert.equal(label.textContent, 'Checking requested periods');
    resolvePost({redirected: true, url: '/chat/ask/history/7/'});
  }
  await finished;
  const posts = requests.filter(r => r.options.method === 'POST');
  assert.equal(posts.length, 1, 'Polling/errors must never start an automatic second paid submission');
  for (const field of fields.filter(f => f.name)) assert.equal(posts[0].options.body.get(field.name), field.value);
  assert.equal(fields.at(-1).disabled, false);
  if (failure) {
    assert.match(label.textContent, /Check History/);
    assert.equal(redirects.length, 0);
  } else assert.equal(redirects[0], '/chat/ask/history/7/');
}

(async () => { await scenario(false); await scenario(true); process.stdout.write('Pilot UI protocol checks: 2 passed\n'); })()
  .catch(error => { console.error(error); process.exitCode = 1; });
