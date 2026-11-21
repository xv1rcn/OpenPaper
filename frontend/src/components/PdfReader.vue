<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from "vue";
import {
  getDocument,
  GlobalWorkerOptions,
  type PDFDocumentLoadingTask,
} from "pdfjs-dist";
import {
  EventBus,
  PDFViewer,
  PDFLinkService,
  PDFFindController,
} from "pdfjs-dist/web/pdf_viewer.mjs";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import "pdfjs-dist/web/pdf_viewer.css";
GlobalWorkerOptions.workerSrc = workerUrl;
const props = defineProps<{ src: string; page: number; storageKey: string }>();
const emit = defineEmits<{ page: [page: number] }>();
const container = ref<HTMLDivElement>(),
  pages = ref<HTMLDivElement>();
const total = ref(0),
  loading = ref(true),
  error = ref(""),
  zoom = ref("page-width"),
  query = ref(""),
  matches = ref("");
let viewer: PDFViewer | undefined,
  task: PDFDocumentLoadingTask | undefined,
  observer: ResizeObserver | undefined;
let disposed = false,
  ready = false;
const bus = new EventBus();
function go(value: number) {
  if (!viewer || !ready) return;
  const page = Math.max(1, Math.min(total.value, Math.round(value) || 1));
  viewer.currentPageNumber = page;
  emit("page", page);
}
function scale() {
  if (!viewer || !ready) return;
  const page = viewer.currentPageNumber;
  ready = false;
  viewer.currentScaleValue = zoom.value;
  viewer.currentPageNumber = page;
  ready = true;
  emit("page", page);
  try {
    localStorage.setItem(props.storageKey + "-zoom", zoom.value);
  } catch {}
}
function search(previous = false, again = false) {
  bus.dispatch("find", {
    source: null,
    type: again ? "again" : "",
    query: query.value,
    phraseSearch: true,
    caseSensitive: false,
    entireWord: false,
    highlightAll: true,
    findPrevious: previous,
    matchDiacritics: false,
  });
}
watch(query, () => search());
watch(
  () => props.page,
  (value) => {
    if (viewer && viewer.currentPageNumber !== value) go(value);
  },
);
onMounted(async () => {
  try {
    const saved = localStorage.getItem(props.storageKey + "-zoom");
    if (
      saved &&
      [
        "page-width",
        "page-fit",
        "0.5",
        "0.75",
        "1",
        "1.25",
        "1.5",
        "2",
      ].includes(saved)
    )
      zoom.value = saved;
  } catch {}
  try {
    const links = new PDFLinkService({
      eventBus: bus,
      externalLinkTarget: 2,
      externalLinkRel: "noopener noreferrer",
      ignoreDestinationZoom: true,
    });
    const find = new PDFFindController({ eventBus: bus, linkService: links });
    viewer = new PDFViewer({
      container: container.value!,
      viewer: pages.value!,
      eventBus: bus,
      linkService: links,
      findController: find,
    });
    links.setViewer(viewer);
    bus.on("pagesinit", () => {
      if (disposed) return;
      const initialPage = Math.max(1, Math.min(total.value, props.page));
      viewer!.currentScaleValue = zoom.value;
      viewer!.currentPageNumber = initialPage;
      ready = true;
      emit("page", initialPage);
      loading.value = false;
    });
    bus.on("pagechanging", ({ pageNumber }: { pageNumber: number }) => {
      if (ready) emit("page", pageNumber);
    });
    bus.on(
      "updatefindmatchescount",
      ({
        matchesCount,
      }: {
        matchesCount: { current: number; total: number };
      }) => {
        matches.value = `${matchesCount.current} / ${matchesCount.total}`;
      },
    );
    bus.on(
      "updatefindcontrolstate",
      ({
        state,
        matchesCount,
      }: {
        state: number;
        matchesCount?: { current: number; total: number };
      }) => {
        if (state === 1) matches.value = "未找到";
        else if (state !== 3 && matchesCount)
          matches.value = `${matchesCount.current} / ${matchesCount.total}`;
      },
    );
    const base = import.meta.env.BASE_URL + "pdfjs/";
    task = getDocument({
      url: props.src,
      cMapUrl: base + "cmaps/",
      cMapPacked: true,
      standardFontDataUrl: base + "standard_fonts/",
      wasmUrl: base + "wasm/",
    });
    task.onPassword = () => {
      error.value = "此 PDF 需要密码，请先使用解锁后的副本。";
      loading.value = false;
      void task?.destroy();
    };
    const doc = await task.promise;
    if (disposed) return;
    total.value = doc.numPages;
    links.setDocument(doc);
    viewer.setDocument(doc);
    observer = new ResizeObserver(() => {
      if (ready && zoom.value.startsWith("page-"))
        viewer!.currentScaleValue = zoom.value;
    });
    observer.observe(container.value!);
  } catch (e) {
    if (!disposed) {
      if (!error.value) error.value = "无法读取 PDF，请检查文件或重新加载。";
      loading.value = false;
    }
  }
});
onUnmounted(() => {
  disposed = true;
  ready = false;
  observer?.disconnect();
  viewer?.setDocument(null);
  void task?.destroy();
});
</script>
<template>
  <div class="pdf-reader">
    <div class="pdf-controls">
      <button
        :disabled="!total || page <= 1"
        @click="go(page - 1)"
        aria-label="上一页"
      >
        上一页
      </button>
      <span aria-live="polite">{{ page }} / {{ total || "—" }}</span>
      <button
        :disabled="!total || page >= total"
        @click="go(page + 1)"
        aria-label="下一页"
      >
        下一页
      </button>
      <select v-model="zoom" aria-label="PDF 缩放" @change="scale">
        <option value="page-width">适合宽度</option>
        <option value="page-fit">适合整页</option>
        <option
          v-for="s in [0.5, 0.75, 1, 1.25, 1.5, 2]"
          :key="s"
          :value="String(s)"
        >
          {{ s * 100 }}%
        </option>
      </select>
    </div>
    <form class="pdf-find" @submit.prevent="search(false, true)">
      <input
        v-model="query"
        aria-label="搜索 PDF 原文"
        placeholder="搜索原文"
      /><button type="button" :disabled="!query" @click="search(true, true)">
        上一处</button
      ><button :disabled="!query">下一处</button
      ><span role="status">{{ query ? matches : "" }}</span>
    </form>
    <p v-if="loading" role="status">正在加载原文…</p>
    <p v-if="error" role="alert">
      {{ error }} <a :href="src" target="_blank" rel="noopener">打开原始 PDF</a>
    </p>
    <div class="pdf-viewport">
      <div
        ref="container"
        class="pdf-scroll"
        tabindex="0"
        aria-label="PDF 原文"
      >
        <div ref="pages" class="pdfViewer" />
      </div>
    </div>
  </div>
</template>
