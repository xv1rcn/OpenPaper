/* Shared by the legacy library and reader; never persists secrets in the browser. */
window.OpenPaperSettings = (() => {
    const legacyKey = 'papers-visualizer-speedread-config-v1';
    const headers = { 'Content-Type': 'application/json', 'X-OpenPaper-Request': '1' };
    async function request(payload) {
        const response = await fetch('/api/settings', payload === undefined
            ? { cache: 'no-store' }
            : { method: 'POST', headers, body: JSON.stringify(payload) });
        const data = await response.json();
        if (!response.ok || !data.ok) throw new Error(data.error || `HTTP ${response.status}`);
        return data;
    }
    async function savedRequest(requireModel = true) {
        const data = await request();
        if (!data.hasCredential || !data.provider.apiBaseUrl || (requireModel && !data.provider.model))
            throw new Error('请先在首页“设置 → 速读”保存配置，或导入旧浏览器配置。');
        return { useSaved: true };
    }
    async function importLegacy(revision) {
        const raw = localStorage.getItem(legacyKey);
        if (!raw) throw new Error('没有可导入的旧浏览器配置。');
        const old = JSON.parse(raw);
        const provider = {};
        for (const name of ['apiBaseUrl', 'model', 'timeoutSec', 'contextWindow', 'maxOutputTokens'])
            if (old[name] !== undefined) provider[name] = old[name];
        const data = await request({ revision, provider, apiKey: old.apiKey });
        // A concurrent legacy tab may have edited the original while saving.
        try {
            if (localStorage.getItem(legacyKey) === raw) localStorage.removeItem(legacyKey);
            else data.warning = '配置已导入，但浏览器配置已被其他页面修改，未删除该副本。';
        } catch (_) {
            data.warning = '配置已导入，但浏览器旧副本未能删除，请手动清理。';
        }
        return data;
    }
    return { headers, load: () => request(), save: request, savedRequest, importLegacy };
})();
