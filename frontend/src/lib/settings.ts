import { request } from "./api";
export interface Provider {
  apiBaseUrl: string;
  model: string;
  timeoutSec: number;
  contextWindow: number;
  maxOutputTokens: number;
}
export interface Settings {
  revision: string;
  provider: Provider;
  hasCredential: boolean;
  warning?: string;
}
export const defaults: Provider = {
  apiBaseUrl: "",
  model: "",
  timeoutSec: 180,
  contextWindow: 0,
  maxOutputTokens: 0,
};
export const settingsApi = {
  load: () => request<Settings>("/api/settings"),
  save: (provider: Provider, revision: string, apiKey?: string) =>
    request<Settings>("/api/settings", {
      provider,
      revision,
      ...(apiKey ? { apiKey } : {}),
    }),
  reset: (revision: string) =>
    request<Settings>("/api/settings", { revision, reset: true }),
  models: () =>
    request<{ models: { id: string }[]; warnings?: string[] }>(
      "/api/list-models",
      { apiConfig: { useSaved: true }, force: true },
    ),
  test: () =>
    request<{ preview: string }>("/api/test-speedread-config", {
      apiConfig: { useSaved: true },
    }),
};
const legacyKey = "papers-visualizer-speedread-config-v1";
export function hasLegacy() {
  try {
    return localStorage.getItem(legacyKey) !== null;
  } catch {
    return false;
  }
}
export async function importLegacy(revision: string) {
  const raw = localStorage.getItem(legacyKey);
  if (!raw)
    throw new Error("当前浏览器没有旧配置。请在原来使用的浏览器和地址中导入。");
  const legacy = JSON.parse(raw);
  if (!legacy || typeof legacy.apiKey !== "string" || !legacy.apiKey.trim())
    throw new Error("旧配置中没有有效密钥，请手动填写。");
  const provider = { ...defaults };
  for (const field of Object.keys(defaults) as (keyof Provider)[]) {
    if (legacy[field] !== undefined)
      Object.assign(provider, { [field]: legacy[field] });
  }
  const data = await settingsApi.save(provider, revision, legacy.apiKey);
  try {
    if (localStorage.getItem(legacyKey) === raw)
      localStorage.removeItem(legacyKey);
    else data.warning = "配置已导入；旧副本被其他页面修改，因此没有删除。";
  } catch {
    data.warning = "配置已导入，但旧浏览器副本未能删除，请手动清理。";
  }
  return data;
}
