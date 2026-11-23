<script setup lang="ts">
import { confirmAction } from "@/lib/confirmation";
import ConfirmDialog from "./components/ConfirmDialog.vue";
import Feedback from "@/components/Feedback.vue";
import { viewState, viewStateError } from "@/lib/view-state";
import { computed, nextTick, onMounted, onUnmounted, ref } from "vue";
import {
  Search,
  LayoutGrid,
  List,
  RefreshCw,
  BookOpen,
  RotateCcw,
  X,
  FolderOpen,
} from "@lucide/vue";
import LibrarySidebar from "./components/LibrarySidebar.vue";
import PaperCard from "./components/PaperCard.vue";
import ReaderWorkspace from "./components/ReaderWorkspace.vue";
import LibraryTools from "./components/LibraryTools.vue";
import LibraryStats from "./components/LibraryStats.vue";
import GroupedLibrary from "./components/GroupedLibrary.vue";
import AdvancedFilters from "./components/AdvancedFilters.vue";
import PaperEditor from "./components/PaperEditor.vue";
import SettingsPanel from "./components/SettingsPanel.vue";
import ImportPdf from "./components/ImportPdf.vue";
import Button from "./components/ui/button/Button.vue";
import { useLibrary } from "./composables/useLibrary";
import { api } from "./lib/api";
import type { Paper } from "./lib/types";
const {
  papers,
  venue,
  selectedTags,
  tagMode,
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
} = useLibrary();
const searchShortcut = /Mac|iPhone|iPad/.test(navigator.platform)
  ? "⌘ K"
  : "Ctrl K";
const routeKey = new URLSearchParams(location.search).get("file_key") || "";
const exportSelection = ref<Paper[]>([]);
function navigateView(next: import("./lib/types").Collection, nextTag = "") {
  if (next === "tools") exportSelection.value = [...visible.value];
  navigate(next, nextTag);
}
async function purge(id?: string) {
  if (
    !(await confirmAction(
      id
        ? "永久删除此回收站项目？无法撤销。"
        : "清空整个回收站？所有项目将永久删除，无法撤销。",
      "永久删除",
    ))
  )
    return;
  await mutate(() => (id ? api.purge(id) : api.purgeAll()), "已永久删除。");
}
const settingsOpen = ref(false),
  importing = ref(false);
let settingsOpener: HTMLElement | null = null;
function openSettings() {
  settingsOpener = document.activeElement as HTMLElement;
  settingsOpen.value = true;
}
async function closeSettings() {
  settingsOpen.value = false;
  await nextTick();
  settingsOpener?.focus();
}
const grouped = ref(false);
try {
  grouped.value = viewState.getItem("openpaper-grouped") === "true";
} catch {}
function toggleGrouping() {
  grouped.value = !grouped.value;
  try {
    viewState.setItem("openpaper-grouped", String(grouped.value));
  } catch {}
}
const layout = ref<"grid" | "list">("grid");
try {
  if (viewState.getItem("openpaper-library-layout") === "list")
    layout.value = "list";
} catch {}
function setLayout(value: "grid" | "list") {
  layout.value = value;
  try {
    viewState.setItem("openpaper-library-layout", value);
  } catch {}
}
const selected = ref<Paper | null>(null),
  searchInput = ref<HTMLInputElement | null>(null);
let editorOpener: HTMLElement | null = null;
function edit(paper: Paper) {
  editorOpener = document.activeElement as HTMLElement;
  selected.value = paper;
  error.value = "";
}
async function closeEditor() {
  selected.value = null;
  await nextTick();
  if (editorOpener?.isConnected) editorOpener.focus();
}
const unread = computed(() => papers.value.filter((p) => !p.read).length);
const title = computed(
  () =>
    tag.value ||
    {
      all: "全部论文",
      unread: "待读论文",
      read: "已读论文",
      recycle: "回收站",
      stats: "统计面板",
      tools: "导出与管理",
    }[collection.value],
);
async function save(paper: Paper, fields: Partial<Paper>) {
  if (await mutate(() => api.update(paper.file_key, fields), "已保存"))
    closeEditor();
}
async function remove(paper: Paper) {
  if (
    !(await confirmAction(
      `将《${paper.title}》移入回收站？可以随时恢复。`,
      "移入回收站",
    ))
  )
    return;
  if (await mutate(() => api.remove(paper.file_key), "已移入回收站"))
    closeEditor();
}
function keyboard(event: KeyboardEvent) {
  if (
    (((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") ||
      (event.key === "/" &&
        !(event.target as HTMLElement)?.closest(
          "input, textarea, select, [contenteditable=true]",
        ))) &&
    !selected.value &&
    !settingsOpen.value
  ) {
    event.preventDefault();
    searchInput.value?.focus();
  }
}
onMounted(() => {
  if (new URLSearchParams(location.search).get("view") === "stats")
    navigate("stats");
  refresh();
  window.addEventListener("keydown", keyboard);
});
onUnmounted(() => window.removeEventListener("keydown", keyboard));
</script>
<template>
  <ConfirmDialog />
  <div v-if="viewStateError" role="alert" class="state-save-error">
    {{ viewStateError }}
  </div>
  <ReaderWorkspace v-if="routeKey" :file-key="routeKey" />
  <div v-else class="app-shell">
    <LibrarySidebar
      :collection="collection"
      :tag="tag"
      :tags="tags"
      :total="papers.length"
      :unread="unread"
      :recycled="recycle.length"
      @navigate="navigateView"
      @settings="openSettings"
    />
    <main class="main-content">
      <header class="topbar">
        <span>书库</span>
        <div class="topbar-right">
          <button
            class="icon-button"
            :disabled="loading || busy || importing"
            aria-label="刷新论文库"
            @click="refresh"
          >
            <RefreshCw :size="16" :class="{ spinning: loading }" />
          </button>
        </div>
      </header>
      <div class="library-content">
        <section class="page-heading">
          <div>
            <h1>
              {{ title
              }}<span>{{
                collection === "recycle" ? recycle.length : visible.length
              }}</span>
            </h1>
          </div>
          <ImportPdf
            :disabled="busy || loading"
            @busy="importing = $event"
            @complete="refresh"
          />
        </section>
        <div v-if="notice" class="notice" role="status">
          {{ notice
          }}<button aria-label="关闭提示" @click="notice = ''">
            <X :size="15" />
          </button>
        </div>
        <Feedback :message="error">
          <Button
            variant="outline"
            :disabled="loading || busy || importing"
            @click="refresh"
            >重试</Button
          >
        </Feedback>
        <LibraryStats v-if="collection === 'stats'" :papers="papers" />
        <LibraryTools
          v-else-if="collection === 'tools'"
          :papers="papers"
          :filtered="exportSelection"
          :tags="tags"
          @changed="refresh"
        />
        <template v-else-if="collection !== 'recycle'">
          <section class="library-toolbar" aria-label="筛选与排序">
            <div class="search-box">
              <Search :size="17" /><input
                ref="searchInput"
                v-model="query"
                aria-label="搜索论文"
                placeholder="搜索标题、作者或标签…"
              /><button v-if="query" aria-label="清空搜索" @click="query = ''">
                <X :size="15" /></button
              ><kbd v-else>{{ searchShortcut }}</kbd>
            </div>
            <div class="toolbar-options">
              <button :aria-pressed="grouped" @click="toggleGrouping">
                按标签分组
              </button>
              <select v-model="sort" aria-label="排序方式">
                <option value="recent">最近添加</option>
                <option value="title">标题顺序</option>
                <option value="year">年份：新到旧</option>
                <option value="year-asc">年份：旧到新</option>
                <option value="oldest">最早添加</option>
                <option value="title-desc">标题倒序</option>
                <option value="venue">会议名称正序</option>
                <option value="venue-desc">会议名称倒序</option>
              </select>
              <div class="layout-switch" aria-label="显示方式">
                <button
                  :aria-pressed="layout === 'grid'"
                  aria-label="卡片视图"
                  @click="setLayout('grid')"
                >
                  <LayoutGrid :size="17" /></button
                ><button
                  :aria-pressed="layout === 'list'"
                  aria-label="列表视图"
                  @click="setLayout('list')"
                >
                  <List :size="18" />
                </button>
              </div>
            </div>
          </section>
          <AdvancedFilters
            :papers="papers"
            :all-tags="tags"
            v-model:venue="venue"
            v-model:tags="selectedTags"
            v-model:mode="tagMode"
          />

          <div
            v-if="loading && !papers.length"
            class="empty-state"
            role="status"
          >
            正在打开本地论文库…
          </div>
          <div v-else-if="!visible.length" class="empty-state">
            <FolderOpen :size="40" :stroke-width="1" />
            <h2>
              {{ papers.length ? "没有匹配的论文" : "还没有论文" }}
            </h2>
            <p>
              {{
                papers.length ? "调整关键词或清除筛选。" : "导入 PDF 开始阅读。"
              }}
            </p>
            <Button
              v-if="papers.length"
              variant="outline"
              @click="navigate('all')"
              >清除筛选</Button
            >
          </div>
          <GroupedLibrary
            v-else-if="grouped"
            :papers="visible"
            :layout="layout"
            :busy="busy || importing"
            @edit="edit"
            @toggle-read="
              (paper) =>
                mutate(
                  () => api.update(paper.file_key, { read: !paper.read }),
                  '阅读状态已保存。',
                )
            "
          />
          <div
            v-else
            class="paper-grid"
            :class="{ 'paper-list': layout === 'list' }"
            :aria-busy="loading || busy"
          >
            <PaperCard
              v-for="paper in visible"
              :key="paper.file_key"
              :paper="paper"
              :layout="layout"
              :busy="busy || importing"
              @edit="edit"
              @toggle-read="
                (paper) =>
                  mutate(
                    () => api.update(paper.file_key, { read: !paper.read }),
                    paper.read ? '已标记为待读。' : '已标记为已读。',
                  )
              "
            />
          </div>
        </template>
        <section v-else aria-label="已删除的项目">
          <Button
            v-if="recycle.length"
            variant="outline"
            :disabled="busy"
            @click="purge()"
            >清空回收站</Button
          >
          <div v-if="!recycle.length" class="empty-state">
            <RotateCcw :size="36" :stroke-width="1" />
            <h2>回收站是空的</h2>
            <p>移除的论文和标签会暂存在这里。</p>
          </div>
          <article v-for="item in recycle" :key="item.id" class="recycle-row">
            <div>
              <span class="item-type">{{
                item.item_type === "tag"
                  ? "标签"
                  : item.item_type === "speedread"
                    ? "速读结果"
                    : "论文"
              }}</span>
              <h3>{{ item.title || item.tag || "未命名项目" }}</h3>
              <p>{{ item.deleted_at }}</p>
            </div>
            <Button
              variant="outline"
              :disabled="busy"
              @click="mutate(() => api.restore(item.id), '项目已恢复。')"
              ><RotateCcw :size="14" />恢复</Button
            >
            <Button variant="ghost" :disabled="busy" @click="purge(item.id)"
              >永久删除</Button
            >
          </article>
        </section>
      </div>
    </main>
    <SettingsPanel v-if="settingsOpen" @close="closeSettings" />
    <PaperEditor
      :available-tags="tags"
      :paper="selected"
      :busy="busy || importing"
      :error="error"
      @close="closeEditor"
      @save="save"
      @remove="remove"
    />
  </div>
</template>
