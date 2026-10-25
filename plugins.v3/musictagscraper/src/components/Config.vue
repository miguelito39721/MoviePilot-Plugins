<script setup>
import { computed, onMounted, ref } from 'vue'

const props = defineProps({
  initialConfig: { type: Object, default: () => ({}) },
  api: { type: Object, default: () => ({}) },
  pluginId: { type: String, default: 'MusicTagScraper' },
})

const emit = defineEmits(['save', 'close'])

const DEFAULTS = {
  enabled: false,
  music_dirs: ['/vol2/1000/music'],
  exclude_dirs: [],
  sources: ['douban', 'musicbrainz', 'theaudiodb'],
  fill_tags: true,
  write_cover: true,
  write_folder_cover: true,
  folder_cover_names: ['cover.jpg'],
  write_lyrics: true,
  lrc_metadata: true,
  overwrite: false,
  overwrite_lyrics: false,
  min_score: 0.62,
  concurrency: 2,
  max_files_per_run: 200,
  schedule_hours: 0,
  notify: true,
  show_sidebar_nav: true,
  dashboard: true,
}

const base = computed(() => `plugin/${props.pluginId || 'MusicTagScraper'}`)
const saving = ref(false)
const config = ref({ ...DEFAULTS })
const dirsText = ref('/vol2/1000/music')
const excludeText = ref('')

const sourceItems = [
  { title: '豆瓣音乐（中文优先）', value: 'douban' },
  { title: 'MusicBrainz', value: 'musicbrainz' },
  { title: 'TheAudioDB', value: 'theaudiodb' },
]

const coverNameItems = [
  { title: 'cover.jpg（Navidrome / 群晖）', value: 'cover.jpg' },
  { title: 'folder.jpg（Windows / 飞牛）', value: 'folder.jpg' },
]

function unwrap(response) {
  if (response && Object.prototype.hasOwnProperty.call(response, 'data') && response.success !== undefined) {
    return response.data
  }
  return response?.data ?? response
}

function toList(value) {
  if (Array.isArray(value)) return value.map(item => String(item || '').trim()).filter(Boolean)
  if (!value) return []
  return String(value)
    .split(/\n|;|；/)
    .map(item => item.trim())
    .filter(Boolean)
}

function applyConfig(data) {
  const merged = { ...DEFAULTS, ...(data || {}) }
  config.value = merged
  dirsText.value = toList(merged.music_dirs).join('\n')
  excludeText.value = toList(merged.exclude_dirs).join('\n')
}

async function loadConfig() {
  if (props.initialConfig && Object.keys(props.initialConfig).length) {
    applyConfig(props.initialConfig)
    return
  }
  if (!props.api?.get) {
    applyConfig({})
    return
  }
  try {
    applyConfig(unwrap(await props.api.get(`${base.value}/config`)))
  } catch (err) {
    applyConfig({})
  }
}

async function save() {
  saving.value = true
  try {
    const payload = {
      ...config.value,
      music_dirs: toList(dirsText.value),
      exclude_dirs: toList(excludeText.value),
      sources: (config.value.sources || []).filter(Boolean),
      folder_cover_names: (config.value.folder_cover_names || []).filter(Boolean),
      concurrency: Number(config.value.concurrency || 2),
      max_files_per_run: Number(config.value.max_files_per_run || 200),
      schedule_hours: Number(config.value.schedule_hours || 0),
      min_score: Number(config.value.min_score || 0.62),
    }
    emit('save', payload)
  } finally {
    saving.value = false
  }
}

onMounted(loadConfig)
</script>

<template>
  <VForm @submit.prevent="save">
    <VContainer class="pa-4">
      <VRow>
        <VCol cols="12" md="6">
          <VSwitch v-model="config.enabled" label="启用插件" color="primary" hide-details class="mb-2" />
        </VCol>
        <VCol cols="12" md="6">
          <VSwitch v-model="config.show_sidebar_nav" label="显示侧栏入口" color="primary" hide-details class="mb-2" />
        </VCol>
      </VRow>

      <VTextarea
        v-model="dirsText"
        label="音乐目录（每行一个）"
        rows="3"
        variant="outlined"
        density="comfortable"
        hint="支持多个目录；子目录会自动递归扫描"
        persistent-hint
        class="mb-3"
      />
      <VTextarea
        v-model="excludeText"
        label="排除目录（每行一个，可留空）"
        rows="2"
        variant="outlined"
        density="comfortable"
        hint="例如 MV 目录、试听目录"
        persistent-hint
        class="mb-3"
      />

      <div class="text-subtitle-2 mb-2">元数据来源（按顺序回退）</div>
      <VCheckboxBtn
        v-for="item in sourceItems"
        :key="item.value"
        v-model="config.sources"
        :label="item.title"
        :value="item.value"
        color="primary"
        inline
      />

      <VDivider class="my-3" />

      <VRow>
        <VCol cols="12" md="3">
          <VSwitch v-model="config.fill_tags" label="补全音频标签" color="primary" hide-details />
        </VCol>
        <VCol cols="12" md="3">
          <VSwitch v-model="config.write_cover" label="补齐内嵌封面" color="primary" hide-details />
        </VCol>
        <VCol cols="12" md="3">
          <VSwitch v-model="config.write_folder_cover" label="写专辑目录封面" color="primary" hide-details />
        </VCol>
        <VCol cols="12" md="3">
          <VSwitch v-model="config.write_lyrics" label="写入歌词（.lrc）" color="primary" hide-details />
        </VCol>
      </VRow>

      <div class="text-caption text-medium-emphasis mt-3 mb-1">目录封面文件名（可多选）</div>
      <VCheckboxBtn
        v-for="item in coverNameItems"
        :key="item.value"
        v-model="config.folder_cover_names"
        :label="item.title"
        :value="item.value"
        color="primary"
        inline
      />
      <VAlert type="info" variant="tonal" density="compact" class="mt-2 mb-1">
        目录封面只在专辑目录没有 cover/folder 图片时补写：优先在线封面，缺失时从音频内嵌封面提取，
        不覆盖已有图片（除非勾选「覆盖已有标签」）。
      </VAlert>

      <VRow class="mt-2">
        <VCol cols="12" md="4">
          <VSwitch v-model="config.overwrite" label="覆盖已有标签" color="warning" hide-details />
        </VCol>
        <VCol cols="12" md="4">
          <VSwitch v-model="config.overwrite_lyrics" label="覆盖已有歌词" color="warning" hide-details />
        </VCol>
        <VCol cols="12" md="4">
          <VSwitch v-model="config.lrc_metadata" label="歌词写入 LRC 头部信息" color="primary" hide-details />
        </VCol>
      </VRow>

      <VRow class="mt-2">
        <VCol cols="12" md="4">
          <VSwitch v-model="config.notify" label="完成后通知" color="primary" hide-details />
        </VCol>
        <VCol cols="12" md="4">
          <VSwitch v-model="config.dashboard" label="首页显示仪表板" color="primary" hide-details />
        </VCol>
      </VRow>

      <VRow class="mt-2">
        <VCol cols="12" md="4">
          <div class="text-caption mb-1">匹配阈值：{{ Number(config.min_score).toFixed(2) }}</div>
          <VSlider v-model="config.min_score" :min="0.3" :max="1" :step="0.01" thumb-label hide-details />
        </VCol>
        <VCol cols="12" md="4">
          <div class="text-caption mb-1">并发：{{ config.concurrency }}</div>
          <VSlider v-model="config.concurrency" :min="1" :max="8" :step="1" thumb-label hide-details />
        </VCol>
        <VCol cols="12" md="4">
          <VTextField
            v-model.number="config.max_files_per_run"
            label="单次最多处理音频数"
            type="number"
            density="comfortable"
            variant="outlined"
            hide-details
          />
        </VCol>
      </VRow>

      <VRow class="mt-3">
        <VCol cols="12" md="4">
          <VTextField
            v-model.number="config.schedule_hours"
            label="定时补全间隔（小时，0=关闭）"
            type="number"
            density="comfortable"
            variant="outlined"
            hint="例如 24 表示每天补一次"
            persistent-hint
          />
        </VCol>
      </VRow>

      <VAlert type="info" variant="tonal" density="compact" class="mt-4">
        插件只写音频文件的标签与同名 .lrc 歌词，不重命名、不移动、不删除；默认「只补空缺」，
        勾选覆盖才会改写已有内容。试跑只扫描不写入。
      </VAlert>

      <VRow class="mt-4">
        <VSpacer />
        <VBtn variant="text" @click="emit('close')">关闭</VBtn>
        <VBtn color="primary" variant="tonal" :loading="saving" @click="save">保存配置</VBtn>
      </VRow>
    </VContainer>
  </VForm>
</template>
