<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref } from "vue";
import {
  Search,
  LayoutGrid,
  List,
  RefreshCw,
  ArrowUpRight,
  BookOpen,
  RotateCcw,
  X,
  FolderOpen,
} from "@lucide/vue";
import LibrarySidebar from "./components/LibrarySidebar.vue";
import PaperCard from "./components/PaperCard.vue";
import PaperEditor from "./components/PaperEditor.vue";
import SettingsPanel from "./components/SettingsPanel.vue";
import ImportPdf from "./components/ImportPdf.vue";
import Button from "./components/ui/button/Button.vue";
import { useLibrary } from "./composables/useLibrary";
import { api } from "./lib/api";
import type { Paper } from "./lib/types";
const {
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
} = useLibrary();
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
const layout = ref<"grid" | "list">("grid");
try {
  if (localStorage.getItem("openpaper-library-layout") === "list")
    layout.value = "list";
} catch {}
function setLayout(value: "grid" | "list") {
  layout.value = value;
  try {
    localStorage.setItem("openpaper-library-layout", value);
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
    }[collection.value],
);
async function save(paper: Paper, fields: Partial<Paper>) {
  if (
    await mutate(() => api.update(paper.file_key, fields), "论文信息已保存。")
  )
    closeEditor();
}
async function remove(paper: Paper) {
  if (!window.confirm(`将《${paper.title}》移入回收站？可以随时恢复。`)) return;
  if (
    await mutate(
      () => api.remove(paper.file_key),
      "论文已移入回收站，可在左侧回收站恢复。",
    )
  )
    closeEditor();
}
function keyboard(event: KeyboardEvent) {
  if (
    (event.metaKey || event.ctrlKey) &&
    event.key.toLowerCase() === "k" &&
    !selected.value &&
    !settingsOpen.value
  ) {
    event.preventDefault();
    searchInput.value?.focus();
  }
}
onMounted(() => {
  refresh();
  window.addEventListener("keydown", keyboard);
});
onUnmounted(() => window.removeEventListener("keydown", keyboard));
</script>
<template>
  <div class="app-shell">
    <LibrarySidebar
      :collection="collection"
      :tag="tag"
      :tags="tags"
      :total="papers.length"
      :unread="unread"
      :recycled="recycle.length"
      @navigate="navigate"
      @settings="openSettings"
    />
    <main class="main-content">
      <header class="topbar">
        <span
          >论文库 <span class="breadcrumb">/ {{ title }}</span></span
        >
        <div class="topbar-right">
          <span class="quiet-label">让阅读，成为积累。</span
          ><button
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
            <div class="eyebrow">YOUR RESEARCH, COLLECTED</div>
            <h1>
              {{ title
              }}<span>{{
                collection === "recycle" ? recycle.length : visible.length
              }}</span>
            </h1>
            <p>
              {{
                collection === "recycle"
                  ? "暂时放下的论文，随时可以找回来。"
                  : "从一篇论文开始，把想法连接起来。"
              }}
            </p>
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
        <div v-if="error" class="error-banner" role="alert">
          {{ error
          }}<Button
            variant="outline"
            :disabled="loading || busy || importing"
            @click="refresh"
            >重试</Button
          >
        </div>
        <template v-if="collection !== 'recycle'">
          <section class="library-toolbar" aria-label="筛选与排序">
            <div class="search-box">
              <Search :size="17" /><input
                ref="searchInput"
                v-model="query"
                aria-label="搜索论文"
                placeholder="搜索标题、作者或标签…"
              /><button v-if="query" aria-label="清空搜索" @click="query = ''">
                <X :size="15" /></button
              ><kbd v-else>⌘ K</kbd>
            </div>
            <div class="toolbar-options">
              <select v-model="sort" aria-label="排序方式">
                <option value="recent">最近添加</option>
                <option value="title">标题顺序</option>
                <option value="year">发表年份</option>
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
          <div class="shelf-label">
            <span>{{
              tag
                ? "# " + tag
                : collection === "unread"
                  ? "留给下一次专注"
                  : "你的研究收藏"
            }}</span><span>{{ visible.length }} 篇论文</span>
          </div>
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
              {{ papers.length ? "没有匹配的论文" : "第一篇论文，从这里开始" }}
            </h2>
            <p>
              {{
                papers.length
                  ? "试试其他关键词，或返回全部论文。"
                  : "点击“导入 PDF”添加论文，原文件会保留。"
              }}
            </p>
            <Button
              v-if="papers.length"
              variant="outline"
              @click="navigate('all')"
              >查看全部论文</Button
            >
          </div>
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
          <footer class="library-footer">
            <span>阅读留下痕迹，思考慢慢生长。</span
            ><span>OPENPAPER <ArrowUpRight :size="12" /></span>
          </footer>
        </template>
        <section v-else aria-label="已删除的项目">
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
          </article>
        </section>
      </div>
    </main>
    <SettingsPanel v-if="settingsOpen" @close="closeSettings" />
    <PaperEditor
      :paper="selected"
      :busy="busy || importing"
      :error="error"
      @close="closeEditor"
      @save="save"
      @remove="remove"
    />
  </div>
</template>
