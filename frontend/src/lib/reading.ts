import { normalizeSpeedReadContent } from "./reading-normalizer.js";
import { request, ApiError } from "./api";
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
export const normalizeReading = (value: SpeedRead) =>
  normalizeSpeedReadContent(value);
export async function loadReading(
  key: string,
): Promise<{ speed_read: SpeedRead }> {
  try {
    return await request<{ speed_read: SpeedRead }>(
      "/api/speedread-cache?file_key=" + encodeURIComponent(key),
    );
  } catch (error) {
    if (
      error instanceof ApiError &&
      error.status === 404 &&
      error.code === "speedread_not_generated"
    )
      return { speed_read: {} };
    throw error;
  }
}
export function hasReadingContent(value: unknown): boolean {
  if (value === null || value === undefined || value === "") return false;
  if (Array.isArray(value)) return value.some(hasReadingContent);
  if (typeof value === "object")
    return Object.values(value).some(hasReadingContent);
  return true;
}
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
