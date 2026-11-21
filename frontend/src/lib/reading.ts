import "../../../assets/quick-reading-common.js";
import { request } from "./api";
export interface SpeedRead {
  status?: string;
  model?: string;
  error?: string;
  updated_at?: string;
  content?: Record<string, unknown>;
  options?: Record<string, unknown>;
  progress?: { message?: string; percent?: number };
  token_status?: Record<string, unknown>;
}
declare global {
  interface Window {
    QuickReadingCommon: {
      normalizeSpeedReadContent(value: unknown): Record<string, unknown>;
    };
  }
}
export const normalizeReading = (value: SpeedRead) =>
  window.QuickReadingCommon.normalizeSpeedReadContent(value);
export const loadReading = (key: string) =>
  request<{ speed_read: SpeedRead }>(
    "/api/speedread-cache?file_key=" + encodeURIComponent(key),
  );
export function download(data: Blob, name: string) {
  const url = URL.createObjectURL(data),
    link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 10000);
}
export async function exportReading(key: string, format: "pdf" | "pptx") {
  const response = await fetch(
    "/api/quick-reading/export?file_key=" +
      encodeURIComponent(key) +
      "&format=" +
      format,
  );
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.error || "导出失败");
  }
  const disposition = response.headers.get("Content-Disposition") || "";
  const encoded = disposition.match(/filename\*=UTF-8''([^;]+)/i)?.[1];
  let name = `OpenPaper-speedread.${format}`;
  if (encoded) {
    try {
      name = decodeURIComponent(encoded).replace(/[\\/\x00-\x1f]/g, "_");
    } catch {}
  }
  download(await response.blob(), name);
}
export function safeFigure(value: unknown) {
  if (typeof value !== "string") return undefined;
  const path = value.replace(/^\//, "");
  return path.startsWith("papers/.quick_reading_cache/") &&
    !path.includes("..") &&
    !path.includes("\\")
    ? "/" + path
    : undefined;
}
