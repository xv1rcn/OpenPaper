<script setup lang="ts">
import DesktopRecovery from "./DesktopRecovery.vue";
import { confirmAction } from "@/lib/confirmation";
import Feedback from "@/components/Feedback.vue";
import { computed, onMounted, ref, watch } from "vue";
import {
  DialogRoot,
  DialogPortal,
  DialogOverlay,
  DialogContent,
  DialogTitle,
  DialogDescription,
} from "reka-ui";
import { X, Download, Settings2 } from "@lucide/vue";
import Button from "./ui/button/Button.vue";
import { useUnsavedChanges } from "@/composables/useUnsavedChanges";
import AppearanceSettings from "./AppearanceSettings.vue";
import { useTransientMessage } from "@/composables/useTransientMessage";
const action = ref("");
const warning = ref("");
const tab = ref("model"),
  appearanceBusy = ref(false),
  appearanceDirty = ref(false);
import {
  defaults,
  hasLegacy,
  importLegacy,
  settingsApi,
  type Settings,
} from "@/lib/settings";
const emit = defineEmits<{ close: [] }>();
const provider = ref({ ...defaults }),
  apiKey = ref(""),
  saved = ref<Settings | null>(null);
const busy = ref(false),
  error = ref(""),
  message = ref(""),
  models = ref<{ id: string }[]>([]),
  legacy = ref(hasLegacy());
const dirty = computed(
  () =>
    !!apiKey.value ||
    (!!saved.value &&
      JSON.stringify(provider.value) !== JSON.stringify(saved.value.provider)),
);
useTransientMessage(message);
watch(
  [provider, apiKey],
  () => {
    message.value = "";
  },
  { deep: true, flush: "sync" },
);
useUnsavedChanges(computed(() => dirty.value || appearanceDirty.value));
function apply(data: Settings) {
  saved.value = data;
  provider.value = { ...data.provider };
  apiKey.value = "";
  legacy.value = hasLegacy();
}
async function run(task: () => Promise<void>, label = "加载中…") {
  if (busy.value) return;
  busy.value = true;
  action.value = label;
  warning.value = "";
  error.value = "";
  message.value = "";
  try {
    await task();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "操作失败，请重试";
  } finally {
    busy.value = false;
    action.value = "";
  }
}
async function load() {
  if (dirty.value && !(await confirmAction("放弃未保存的修改，重新加载配置？")))
    return;
  run(async () => {
    apply(await settingsApi.load());
    models.value = [];
  });
}
async function close() {
  if (
    !busy.value &&
    !appearanceBusy.value &&
    (!(dirty.value || appearanceDirty.value) ||
      (await confirmAction("放弃未保存的配置修改？")))
  )
    emit("close");
}
function save() {
  run(async () => {
    if (!saved.value) throw new Error("请先重新加载配置");
    const result = await settingsApi.save(
      provider.value,
      saved.value.revision,
      apiKey.value.trim() || undefined,
    );
    apply(result);
    models.value = [];
    warning.value =
      result.warning ||
      (!result.hasCredential ? "配置已保存，请填写 API Key 后使用速读。" : "");
    if (!warning.value) message.value = "已保存";
  }, "保存中…");
}
async function reset() {
  if (
    !saved.value ||
    !(await confirmAction("清空速读配置并删除已保存的系统凭据？", "清空配置"))
  )
    return;
  run(async () => {
    const result = await settingsApi.reset(saved.value!.revision);
    apply(result);
    models.value = [];
    warning.value = result.warning || "";
    if (!warning.value) message.value = "配置已清空";
  }, "清空中…");
}
async function importOld() {
  if (
    !saved.value ||
    !(await confirmAction(
      "用旧浏览器配置替换当前配置？成功保存后将删除浏览器中的旧密钥。",
      "导入旧配置",
    ))
  )
    return;
  run(async () => {
    const result = await importLegacy(saved.value!.revision);
    apply(result);
    models.value = [];
    warning.value = result.warning || "";
    if (!warning.value) message.value = "旧配置已导入";
  }, "导入中…");
}
function assertSaved(requireModel = true) {
  if (dirty.value) throw new Error("请先保存修改，再使用已保存的配置。");
  if (
    !saved.value?.hasCredential ||
    !provider.value.apiBaseUrl ||
    (requireModel && !provider.value.model)
  )
    throw new Error("请先保存 API 地址、密钥和所需模型。");
}
function loadModels() {
  run(async () => {
    assertSaved(false);
    const result = await settingsApi.models();
    models.value = result.models;
    warning.value = (result.warnings || []).join("；");
    message.value = models.value.length
      ? `已读取 ${models.value.length} 个模型`
      : "未找到模型，可手动填写模型名称";
  }, "读取中…");
}
function testConnection() {
  run(async () => {
    assertSaved();
    await settingsApi.test();
    message.value = "连接成功";
  }, "测试中…");
}
onMounted(load);
</script>
<template>
  <DialogRoot
    :open="true"
    @update:open="
      (value) => {
        if (!value) close();
      }
    "
  >
    <DialogPortal
      ><DialogOverlay class="dialog-overlay" /><DialogContent
        class="dialog-content settings-panel"
        @escape-key-down="
          (event) => {
            event.preventDefault();
            close();
          }
        "
        @pointer-down-outside="(event) => event.preventDefault()"
      >
        <DialogTitle class="dialog-title"
          ><Settings2 :size="20" />设置</DialogTitle
        >
        <DialogDescription class="sr-only"
          >应用外观与速读配置。</DialogDescription
        ><DesktopRecovery inline />
        <button
          class="dialog-close"
          aria-label="关闭设置"
          :disabled="busy || appearanceBusy"
          @click="close"
        >
          <X :size="19" />
        </button>
        <div class="settings-tabs">
          <button :aria-pressed="tab === 'model'" @click="tab = 'model'">
            速读</button
          ><button
            :aria-pressed="tab === 'appearance'"
            @click="tab = 'appearance'"
          >
            外观
          </button>
        </div>
        <AppearanceSettings
          v-show="tab === 'appearance'"
          @busy="appearanceBusy = $event"
          @dirty="appearanceDirty = $event"
        />
        <div v-show="tab === 'model'">
          <form @submit.prevent="save">
            <fieldset :disabled="busy || !saved">
              <label
                >API 地址<input
                  v-model="provider.apiBaseUrl"
                  @input="models = []"
                  type="url"
                  placeholder="https://api.example.com/v1"
                  autocomplete="off"
              /></label>
              <label
                >API Key
                <span
                  aria-hidden="true"
                  v-if="saved?.hasCredential"
                  class="credential-status"
                  >已设置</span
                ><input
                  aria-label="API Key"
                  v-model="apiKey"
                  type="password"
                  :placeholder="
                    saved?.hasCredential
                      ? '输入新密钥以替换'
                      : '输入服务商提供的密钥'
                  "
                  autocomplete="new-password"
                  spellcheck="false"
              /></label>
              <div class="model-field">
                <label
                  >模型名称<input
                    v-model="provider.model"
                    list="provider-models"
                    placeholder="填写模型 ID，或读取模型列表"
                    autocomplete="off" /></label
                ><Button
                  type="button"
                  variant="outline"
                  :disabled="busy || dirty || !saved?.hasCredential"
                  @click="loadModels"
                  >{{ action === "读取中…" ? action : "读取模型" }}</Button
                >
              </div>
              <datalist id="provider-models">
                <option
                  v-for="model in models"
                  :key="model.id"
                  :value="model.id"
                />
              </datalist>
              <details class="advanced-settings">
                <summary>高级参数</summary>
                <div class="settings-numbers">
                  <label
                    >超时（秒）<input
                      v-model.number="provider.timeoutSec"
                      type="number"
                      min="1"
                      max="3600"
                      required /></label
                  ><label
                    >上下文窗口<input
                      v-model.number="provider.contextWindow"
                      type="number"
                      min="0"
                      max="10000000"
                      required /></label
                  ><label
                    >最大输出<input
                      v-model.number="provider.maxOutputTokens"
                      type="number"
                      min="0"
                      max="1000000"
                      required
                  /></label>
                </div>
                <p class="field-help">
                  上下文窗口与最大输出设为 0 时自动配置。
                </p>
              </details>
              <div v-if="legacy" class="legacy-import">
                <Download :size="17" />
                <div>
                  <strong>检测到旧浏览器配置</strong>
                  <p>导入成功后才会删除浏览器中的旧密钥。</p>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  :disabled="busy"
                  @click="importOld"
                  >导入旧配置</Button
                >
              </div>
            </fieldset>
            <Feedback :message="error" />
            <Feedback :message="warning" kind="warning" />
            <div class="settings-secondary">
              <button
                v-if="dirty || !saved"
                type="button"
                :disabled="busy"
                @click="load"
              >
                {{ dirty ? "放弃修改" : "重试" }}</button><button
                type="button"
                class="danger-link"
                :disabled="busy || !saved"
                @click="reset"
              >
                清空配置
              </button>
            </div>
            <p id="model-test-cost" class="field-help">
              测试会发送一次模型请求，可能产生费用。
            </p>
            <div class="dialog-footer">
              <span v-if="dirty" class="field-help">未保存</span>
              <Feedback v-else :message="message" kind="success" />
              <Button
                type="button"
                variant="outline"
                :disabled="busy || dirty || !saved?.hasCredential"
                aria-describedby="model-test-cost"
                @click="testConnection"
                >{{
                  action === "测试中…" ? action : "测试连接"
                }}</Button><Button type="submit" :disabled="busy || !saved">{{
                action === "保存中…" ? action : "保存"
              }}</Button>
            </div>
          </form>
        </div>
      </DialogContent></DialogPortal
    >
  </DialogRoot>
</template>
