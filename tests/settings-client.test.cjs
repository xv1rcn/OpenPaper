const { readFileSync } = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const test = require('node:test');
const source = readFileSync('assets/settings-client.js', 'utf8');
function setup(fail = false) {
    const data = new Map();
    const calls = [];
    const context = { window: {}, localStorage: {
        getItem: key => data.get(key) ?? null,
        removeItem: key => data.delete(key),
    }, fetch: async (url, options) => {
        calls.push(options);
        return { ok: !fail, status: fail ? 500 : 200,
            json: async () => ({ ok: !fail, hasCredential: true, provider: {apiBaseUrl: 'https://example.com', model: 'test'} }) };
    }};
    vm.runInNewContext(source, context);
    return {client: context.window.OpenPaperSettings, data, calls};
}
const key = 'papers-visualizer-speedread-config-v1';
test('failed import preserves original browser credential', async () => {
    const {client, data} = setup(true);
    data.set(key, JSON.stringify({apiKey: 'synthetic-secret'}));
    await assert.rejects(client.importLegacy('0'));
    assert.ok(data.has(key));
});
test('successful import removes old credential, normal requests carry no secret', async () => {
    const {client, data, calls} = setup();
    data.set(key, JSON.stringify({apiKey: 'synthetic-secret', model: 'test'}));
    await client.importLegacy('0');
    assert.equal(data.has(key), false);
    assert.equal(JSON.stringify(await client.savedRequest()), '{"useSaved":true}');
    assert.equal(calls[0].headers['X-OpenPaper-Request'], '1');
});
test('both legacy pages parse and load settings client before application code', () => {
    for (const name of ['template.html', 'index.html', 'quick-reading.html']) {
        const html = readFileSync(name, 'utf8');
        assert.ok(html.includes('assets/settings-client.js'));
        for (const match of html.matchAll(/<script>([\s\S]*?)<\/script>/g)) new vm.Script(match[1]);
        assert.ok(!html.includes('localStorage.setItem(SPEEDREAD_CONFIG_KEY'));
    }
});
