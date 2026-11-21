<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import {
  DialogRoot,
  DialogPortal,
  DialogOverlay,
  DialogContent,
  DialogTitle,
  DialogDescription,
} from "reka-ui";
import { X, ShieldCheck, Download, Settings2 } from "@lucide/vue";
import Button from "./ui/button/Button.vue";
import AppearanceSettings from "./AppearanceSettings.vue";
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
function apply(data: Settings) {
  saved.value = data;
  provider.value = { ...data.provider };
  apiKey.value = "";
  legacy.value = hasLegacy();
}
async function run(action: () => Promise<void>) {
  if (busy.value) return;
  busy.value = true;
  error.value = "";
  message.value = "";
  try {
    await action();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "操作失败，请重试";
  } finally {
    busy.value = false;
  }
}
function load() {
  if (dirty.value && !confirm("放弃未保存的修改，重新加载配置？")) return;
  run(async () => {
    apply(await settingsApi.load());
    models.value = [];
  });
}
function close() {
  if (
    !busy.value &&
    !appearanceBusy.value &&
    (!(dirty.value || appearanceDirty.value) ||
      confirm("放弃未保存的配置修改？"))
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
    message.value =
      result.warning ||
      (result.hasCredential
        ? "配置已保存。密钥存入系统凭据库，重启后继续使用。"
        : "普通配置已保存，尚未保存密钥。");
  });
}
function reset() {
  if (!saved.value || !confirm("清空速读配置并删除已保存的系统凭据？")) return;
  run(async () => {
    const result = await settingsApi.reset(saved.value!.revision);
    apply(result);
    models.value = [];
    message.value = result.warning || "配置及凭据已清空。";
  });
}
function importOld() {
  if (
    !saved.value ||
    !confirm("用旧浏览器配置替换当前配置？成功保存后将删除浏览器中的旧密钥。")
  )
    return;
  run(async () => {
    const result = await importLegacy(saved.value!.revision);
    apply(result);
    models.value = [];
    message.value = result.warning || "旧配置已导入，浏览器中的旧密钥已删除。";
  });
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
    message.value = `已读取 ${models.value.length} 个模型。${(result.warnings || []).join("；")}`;
  });
}
function testConnection() {
  run(async () => {
    assertSaved();
    const result = await settingsApi.test();
    message.value = result.preview || "接口连接成功。";
  });
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
          ><Settings2 :size="20" />速读设置</DialogTitle
        >
        <DialogDescription class="dialog-description"
          >连接你自己的模型服务。普通配置保存在本机，密钥交由系统凭据库保管。</DialogDescription
        >
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
            模型服务</button
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
          <div class="settings-security">
            <ShieldCheck :size="17" /><span>{{
              saved?.hasCredential
                ? "已保存密钥 · 留空即可继续使用"
                : "尚未保存密钥"
            }}</span
            ><span v-if="dirty" class="unsaved-label">未保存</span>
          </div>
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
                >API Key<input
                  v-model="apiKey"
                  type="password"
                  :placeholder="
                    saved?.hasCredential
                      ? '已保存；留空不更换'
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
                  >读取模型</Button
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
            <p v-if="error" role="alert" class="inline-error">{{ error }}</p>
            <p v-if="message" role="status" class="settings-message">
              {{ message }}
            </p>
            <p v-if="busy" role="status" class="field-help">处理中，请稍候…</p>
            <div class="settings-secondary">
              <button type="button" :disabled="busy" @click="load">
                重新加载</button
              ><button
                type="button"
                class="danger-link"
                :disabled="busy || !saved"
                @click="reset"
              >
                清空配置
              </button>
            </div>
            <div class="dialog-footer">
              <Button
                type="button"
                variant="outline"
                :disabled="busy || dirty || !saved?.hasCredential"
                @click="testConnection"
                >测试接口（会调用模型）</Button
              ><Button type="submit" :disabled="busy || !saved"
                >保存配置</Button
              >
            </div>
          </form>
        </div>
      </DialogContent></DialogPortal
    >
  </DialogRoot>
</template>
