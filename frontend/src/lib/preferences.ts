import { request } from "./api";
export const appearanceDefaults = {
  theme: "light",
  accent: "#43684e",
  background: "#fafbf8",
  readBackground: "#eef3e8",
};
export type Appearance = typeof appearanceDefaults;
export interface Preferences {
  revision: string;
  values: Appearance;
}
export const preferencesApi = {
  load: () => request<Preferences>("/api/preferences"),
  save: (values: Appearance, revision: string) =>
    request<Preferences>("/api/preferences", { values, revision }),
};
export function applyAppearance(values: Appearance) {
  const root = document.documentElement;
  root.dataset.theme = values.theme;
  root.style.setProperty("--accent", values.accent);
  root.style.setProperty("--primary", values.accent);
  root.style.setProperty("--background", values.background);
  root.style.setProperty("--read-background", values.readBackground);
}
export async function loadAppearance() {
  try {
    applyAppearance((await preferencesApi.load()).values);
  } catch {
    /* Settings panel exposes persistence errors without preventing library access. */
  }
}
