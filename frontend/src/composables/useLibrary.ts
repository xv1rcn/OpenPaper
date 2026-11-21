import { ref, computed } from "vue";
import { api, normalizePaper } from "@/lib/api";
import { filterPapers } from "@/lib/library";
import type { Paper, RecycleItem, Collection, Sort } from "@/lib/types";
export function useLibrary() {
  const papers = ref<Paper[]>([]),
    recycle = ref<RecycleItem[]>([]);
  const loading = ref(false),
    busy = ref(false),
    error = ref(""),
    notice = ref("");
  const venue = ref(""),
    selectedTags = ref<string[]>([]),
    tagMode = ref<"any" | "all">("any");
  const query = ref(""),
    collection = ref<Collection>("all"),
    tag = ref(""),
    sort = ref<Sort>("recent");
  const tags = computed(() =>
    [...new Set(papers.value.flatMap((p) => p.tags))].sort((a, b) =>
      a.localeCompare(b, "zh-CN"),
    ),
  );
  const visible = computed(() =>
    filterPapers(
      papers.value.filter(
        (p) =>
          (!venue.value || p.venue === venue.value) &&
          (!selectedTags.value.length ||
            (tagMode.value === "all"
              ? selectedTags.value.every((t) => p.tags.includes(t))
              : selectedTags.value.some((t) => p.tags.includes(t)))),
      ),
      query.value,
      collection.value,
      tag.value,
      sort.value,
    ),
  );
  async function refresh() {
    loading.value = true;
    error.value = "";
    try {
      const [library, bin] = await Promise.all([api.library(), api.recycle()]);
      papers.value = library.papers.map(normalizePaper);
      recycle.value = bin.items;
    } catch (e) {
      error.value = e instanceof Error ? e.message : "无法连接本地服务";
    } finally {
      loading.value = false;
    }
  }
  async function mutate(action: () => Promise<unknown>, success: string) {
    if (busy.value) return false;
    busy.value = true;
    error.value = "";
    notice.value = "";
    try {
      await action();
      notice.value = success;
      await refresh();
      return true;
    } catch (e) {
      error.value = e instanceof Error ? e.message : "操作失败，请重试";
      return false;
    } finally {
      busy.value = false;
    }
  }
  function navigate(next: Collection, nextTag = "") {
    collection.value = next;
    tag.value = nextTag;
    query.value = "";
    venue.value = "";
    selectedTags.value = [];
  }
  return {
    venue,
    selectedTags,
    tagMode,
    papers,
    recycle,
    loading,
    busy,
    error,
    notice,
    query,
    collection,
    tag,
    sort,
    tags,
    visible,
    refresh,
    mutate,
    navigate,
  };
}
