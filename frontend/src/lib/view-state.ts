import { ref } from "vue";
export const viewStateError = ref("");
let values: Record<string, string> = {};
let loaded = false;
const client = crypto.randomUUID();
let sequence = 0;
async function send(body?: unknown) {
  const response = await fetch("/api/view-state", body === undefined ? { cache: "no-store", signal: AbortSignal.timeout(10000) } : {
    method: "POST", keepalive: true, signal: AbortSignal.timeout(10000),
    headers: { "Content-Type": "application/json", "X-OpenPaper-Request": "1" },
    body: JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok || !data.ok) throw new Error(data.error || "阅读状态保存失败");
  return data;
}
export async function loadViewState() {
  try {
    values = (await send()).values;
    // Import only this origin's old UI preferences; existing server values win.
    const legacy: [string, string][] = [];
    try {
      for (let i = 0; i < localStorage.length; i++) {
        const oldKey = localStorage.key(i)!;
        const key = oldKey === "papers-visualizer-group-order-v1" ? "openpaper-group-order" : oldKey;
        if (["openpaper-grouped", "openpaper-library-layout", "openpaper-group-order"].includes(key) || key.startsWith("openpaper-reader-")) {
          if (!(key in values)) legacy.push([key, localStorage.getItem(oldKey)!]);
        }
      }
    } catch { /* Storage can be disabled; backend state still works. */ }
    for (const [key, value] of legacy) {
      try { values[key] = (await send({ key, value, onlyMissing: true })).value; }
      catch { viewStateError.value = "部分旧阅读状态未能迁移，原记录已保留。"; }
    }
    loaded = true;
  } catch {
    viewStateError.value = "无法加载阅读状态，本次更改不会保存。请重新打开页面重试。";
  }
}
export const viewState = {
  getItem(key: string): string | null { return values[key] ?? null; },
  setItem(key: string, value: string) {
    if (!loaded || values[key] === value) return;
    values[key] = value;
    // Dispatch immediately so navigation cannot discard an unsent queued write.
    // The server rejects out-of-order writes from this page instance.
    void send({ key, value, client, sequence: ++sequence }).catch(() => {
      viewStateError.value = "阅读状态未能保存，请检查连接并重新打开页面。";
    });
  },
};
