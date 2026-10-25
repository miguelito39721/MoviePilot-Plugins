<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps({
  api: { type: Object, default: () => ({}) },
  pluginId: { type: String, default: 'MusicTagScraper' },
  compact: { type: Boolean, default: false },
})

const base = computed(() => `plugin/${props.pluginId || 'MusicTagScraper'}`)
const status = ref(null)
const loading = ref(false)
const busy = ref('')
const message = ref('')
const messageType = ref('info')
const showMessage = ref(false)
const previewDialog = ref(false)
const preview = ref(null)
const selected = ref([])
const dedupeDialog = ref(false)
const dedupe = ref(null)
const dedupeSelected = ref([])
const showFailures = ref(false)
let timer = null
let dedupeTimer = null

function unwrap(response) {
  if (response && Object.prototype.hasOwnProperty.call(response, 'data') && response.success !== undefined) {
    return response.data
  }
  return response?.data ?? response
}

function errorText(err) {
  if (!err) return '未知错误'
  return err.message || String(err)
}

function notify(text, type = 'info') {
  message.value = text
  messageType.value = type
  showMessage.value = true
}

async function refresh() {
  if (!props.api?.get) return
  try {
    status.value = unwrap(await props.api.get(`${base.value}/status`))
  } catch (err) {
    notify(`读取状态失败：${errorText(err)}`, 'error')
  }
}

async function doPreview() {
  if (!props.api?.post) return
  busy.value = 'preview'
  try {
    const data = unwrap(await props.api.post(`${base.value}/preview`, { body: { sample: 8 } }))
    preview.value = data
    selected.value = (data?.items || []).map(item => item.key)
    previewDialog.value = true
    if (!data?.items?.length) {
      notify(data?.stats ? `扫描 ${data.stats.scanned} 个音频，暂无待处理` : '暂无待处理音频', 'info')
    }
  } catch (err) {
    notify(`试跑失败：${errorText(err)}`, 'error')
  } finally {
    busy.value = ''
  }
}

async function doRun(paths = []) {
  if (!props.api?.post) return
  busy.value = 'run'
  try {
    const body = Array.isArray(paths) && paths.length ? { paths, limit: paths.length, force: true } : {}
    const data = unwrap(await props.api.post(`${base.value}/run`, { body }))
    notify(
      data?.started
        ? `已启动，待处理 ${data.total} 个音频`
        : data?.message || '未能启动',
      data?.started ? 'success' : 'warning',
    )
    await refresh()
    if (data?.started) startPolling()
  } catch (err) {
    notify(`启动失败：${errorText(err)}`, 'error')
  } finally {
    busy.value = ''
  }
}

async function doRunSelected() {
  if (!selected.value.length) {
    notify('请先勾选需要处理的音频', 'warning')
    return
  }
  previewDialog.value = false
  await doRun(selected.value)
}

async function retryOne(item) {
  if (!props.api?.post) return
  busy.value = `retry:${item.key}`
  try {
    const data = unwrap(await props.api.post(`${base.value}/retry`, { body: { keys: [item.key] } }))
    notify(data?.started ? '已重试该条' : data?.message || '无法重试', data?.started ? 'success' : 'warning')
    await refresh()
    if (data?.started) startPolling()
  } catch (err) {
    notify(`重试失败：${errorText(err)}`, 'error')
  } finally {
    busy.value = ''
  }
}

function toggleAll() {
  const items = preview.value?.items || []
  selected.value = selected.value.length === items.length ? [] : items.map(item => item.key)
}

const allSelected = computed(() => {
  const items = preview.value?.items || []
  return items.length > 0 && selected.value.length === items.length
})

function formatSize(bytes) {
  const value = Number(bytes || 0)
  if (!value) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let index = 0
  let size = value
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024
    index += 1
  }
  return `${size.toFixed(index === 0 ? 0 : 1)} ${units[index]}`
}

async function doDetect() {
  if (!props.api?.post) return
  busy.value = 'dedupe'
  try {
    const data = unwrap(await props.api.post(`${base.value}/duplicates`, { body: {} }))
    if (data?.groups) {
      applyDedupe(data)
      return
    }
    if (data?.started === false && !data?.running) {
      notify(data?.message || '无法开始查重', 'warning')
      return
    }
    notify(data?.running ? '查重已开始，扫描完成后自动打开结果' : '查重已开始', 'info')
    await refresh()
    stopDedupePolling()
    dedupeTimer = setInterval(pollDedupe, 2500)
  } catch (err) {
    notify(`查重失败：${errorText(err)}`, 'error')
  } finally {
    busy.value = ''
  }
}

function applyDedupe(data) {
  dedupe.value = data
  dedupeSelected.value = (data?.groups || []).flatMap(group => group.duplicates || [])
  dedupeDialog.value = true
  if (!data?.groups?.length) {
    notify(`扫描 ${data?.stats?.scanned ?? 0} 个音频，未发现重复`, 'success')
  } else {
    notify(`发现 ${data.groups.length} 组重复，可省 ${formatSize(data?.stats?.wasted_bytes)}`, 'info')
  }
}

async function pollDedupe() {
  if (!props.api?.post) return
  try {
    const snapshot = unwrap(await props.api.post(`${base.value}/duplicates/result`, { body: {} }))
    if (snapshot?.running) return
    stopDedupePolling()
    await refresh()
    const result = snapshot?.result
    if (result?.stats) {
      applyDedupe(result)
    } else {
      notify(snapshot?.run?.message || '查重结束但没有结果', 'warning')
    }
  } catch (err) {
    stopDedupePolling()
    notify(`读取查重结果失败：${errorText(err)}`, 'error')
  }
}

function stopDedupePolling() {
  if (dedupeTimer) {
    clearInterval(dedupeTimer)
    dedupeTimer = null
  }
}

function toggleDedupeAll() {
  const all = (dedupe.value?.groups || []).flatMap(group => group.duplicates || [])
  dedupeSelected.value = dedupeSelected.value.length === all.length ? [] : all
}

async function doQuarantine() {
  if (!props.api?.post) return
  if (!dedupeSelected.value.length) {
    notify('请先勾选需要隔离的重复文件', 'warning')
    return
  }
  busy.value = 'quarantine'
  try {
    const data = unwrap(await props.api.post(`${base.value}/duplicates/quarantine`, {
      body: { paths: dedupeSelected.value },
    }))
    const failed = data?.failed?.length || 0
    notify(
      `已隔离 ${data?.moved ?? 0} 个文件（${formatSize(data?.moved_bytes)}）${failed ? `，失败 ${failed} 个` : ''}`,
      failed ? 'warning' : 'success',
    )
    dedupeDialog.value = false
    await refresh()
  } catch (err) {
    notify(`隔离失败：${errorText(err)}`, 'error')
  } finally {
    busy.value = ''
  }
}

async function doRestore() {
  if (!props.api?.post) return
  busy.value = 'restore'
  try {
    const data = unwrap(await props.api.post(`${base.value}/duplicates/restore`, { body: {} }))
    notify(`已还原 ${data?.restored ?? 0} 个文件`, 'success')
    await refresh()
  } catch (err) {
    notify(`还原失败：${errorText(err)}`, 'error')
  } finally {
    busy.value = ''
  }
}

const dedupeStats = computed(() => status.value?.dedupe?.stats || status.value?.dedupe || {})
const quarantinedCount = computed(() => status.value?.quarantined_count ?? 0)

async function doStop() {
  if (!props.api?.post) return
  busy.value = 'stop'
  try {
    await props.api.post(`${base.value}/stop`)
    notify('已请求停止', 'warning')
    await refresh()
  } catch (err) {
    notify(`停止失败：${errorText(err)}`, 'error')
  } finally {
    busy.value = ''
  }
}

async function doRetry() {
  if (!props.api?.post) return
  busy.value = 'retry'
  try {
    const data = unwrap(await props.api.post(`${base.value}/retry`))
    notify(data?.started ? '已开始重试失败条目' : data?.message || '没有可重试的条目', 'info')
    await refresh()
    if (data?.started) startPolling()
  } catch (err) {
    notify(`重试失败：${errorText(err)}`, 'error')
  } finally {
    busy.value = ''
  }
}

async function doClear() {
  if (!props.api?.post) return
  busy.value = 'clear'
  try {
    const data = unwrap(await props.api.post(`${base.value}/clear`))
    notify(`已清空 ${data?.cleared ?? 0} 条记录`, 'success')
    await refresh()
  } catch (err) {
    notify(`清空失败：${errorText(err)}`, 'error')
  } finally {
    busy.value = ''
  }
}

function startPolling() {
  stopPolling()
  timer = setInterval(async () => {
    await refresh()
    if (!status.value?.running) stopPolling()
  }, 3000)
}

function stopPolling() {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

const running = computed(() => Boolean(status.value?.running))
const run = computed(() => status.value?.run || {})
const lastRun = computed(() => status.value?.last_run || {})
const failures = computed(() => status.value?.failures || [])
const logs = computed(() => status.value?.logs || [])
const progress = computed(() => {
  const total = Number(run.value?.total || 0)
  const finished = Number(run.value?.finished || 0)
  if (!total) return 0
  return Math.min(100, Math.round((finished / total) * 100))
})
const cards = computed(() => [
  { title: '已处理音频', value: status.value?.processed_total ?? 0, icon: 'mdi-music-note', color: 'primary' },
  { title: '今日更新', value: status.value?.today?.updated ?? 0, icon: 'mdi-check-circle-outline', color: 'success' },
  { title: '失败条目', value: status.value?.failure_count ?? 0, icon: 'mdi-alert-circle-outline', color: 'error' },
  { title: '目录封面', value: status.value?.cover_dir_count ?? 0, icon: 'mdi-image-multiple-outline', color: 'info' },
])

const sourceLabels = { douban: '豆瓣音乐', musicbrainz: 'MusicBrainz', theaudiodb: 'TheAudioDB' }

function missingLabel(items) {
  const mapping = {
    title: '标题', artist: '艺人', album: '专辑', year: '年份', track: '曲序', lyrics: '歌词',
    folder_cover: '目录封面',
  }
  return (items || []).map(item => mapping[item] || item).join('、')
}

onMounted(async () => {
  await refresh()
  if (status.value?.running) startPolling()
})

onBeforeUnmount(() => {
  stopPolling()
  stopDedupePolling()
})
</script>

<template>
  <VContainer :class="props.compact ? 'pa-2' : 'pa-4'">
    <VRow class="mb-2" align="center">
      <VCol cols="12" md="auto">
        <div class="d-flex align-center ga-2">
          <VIcon icon="mdi-music-note-plus" size="28" color="primary" />
          <div>
            <div class="text-h6">音乐标签刮削</div>
            <div class="text-caption text-medium-emphasis">
              多源补全标签 / 歌词 / 封面，只补空缺，不移动文件
            </div>
          </div>
        </div>
      </VCol>
      <VSpacer />
      <VCol cols="12" md="auto" class="d-flex ga-2 flex-wrap justify-end">
        <VBtn
          variant="tonal"
          prepend-icon="mdi-magnify-scan"
          :loading="busy === 'preview'"
          @click="doPreview"
        >
          试跑预览
        </VBtn>
        <VBtn
          color="primary"
          prepend-icon="mdi-play"
          :loading="busy === 'run'"
          :disabled="running"
          @click="doRun"
        >
          开始补全
        </VBtn>
        <VBtn
          variant="outlined"
          color="warning"
          prepend-icon="mdi-stop"
          :disabled="!running"
          :loading="busy === 'stop'"
          @click="doStop"
        >
          停止
        </VBtn>
      </VCol>
    </VRow>

    <VRow>
      <VCol v-for="card in cards" :key="card.title" cols="6" md="3">
        <VCard variant="tonal" :color="card.color">
          <VCardText class="d-flex align-center ga-3">
            <VIcon :icon="card.icon" size="30" />
            <div>
              <div class="text-caption">{{ card.title }}</div>
              <div class="text-h5">{{ card.value }}</div>
            </div>
          </VCardText>
        </VCard>
      </VCol>
    </VRow>

    <VCard v-if="running" variant="outlined" class="mt-4">
      <VCardText>
        <div class="d-flex align-center justify-space-between mb-2">
          <span class="text-body-2">{{ run.message || '正在处理…' }}</span>
          <VChip size="small" color="primary" variant="tonal">{{ progress }}%</VChip>
        </div>
        <VProgressLinear :model-value="progress" color="primary" height="10" rounded />
      </VCardText>
    </VCard>

    <VCard v-else-if="lastRun && lastRun.state" variant="outlined" class="mt-4">
      <VCardText class="d-flex flex-wrap ga-3 align-center">
        <VChip size="small" :color="lastRun.state === 'finished' ? 'success' : 'warning'" variant="tonal">
          {{ lastRun.state === 'finished' ? '上次完成' : lastRun.state === 'cancelled' ? '上次已停止' : '上次失败' }}
        </VChip>
        <span class="text-body-2">共 {{ lastRun.total || 0 }} 条</span>
        <span class="text-body-2 text-success">更新 {{ lastRun.updated || 0 }}</span>
        <span class="text-body-2 text-info">目录封面 {{ lastRun.folder_cover || 0 }}</span>
        <span class="text-body-2 text-medium-emphasis">跳过 {{ lastRun.skipped || 0 }}</span>
        <span class="text-body-2 text-error">失败 {{ lastRun.failed || 0 }}</span>
        <VSpacer />
        <span class="text-caption text-medium-emphasis">{{ lastRun.finished_at }}</span>
      </VCardText>
    </VCard>

    <VRow class="mt-4">
      <VCol cols="12" md="6">
        <VCard variant="tonal">
          <VCardTitle class="d-flex align-center">
            <VIcon icon="mdi-tools" class="me-2" />失败与重试
            <VSpacer />
            <VBtn size="small" variant="text" :loading="busy === 'retry'" @click="doRetry">重试失败</VBtn>
            <VBtn size="small" variant="text" color="warning" :loading="busy === 'clear'" @click="doClear">清空记录</VBtn>
          </VCardTitle>
          <VCardText>
            <VAlert v-if="!failures.length" type="success" variant="tonal" density="compact">
              暂无失败条目
            </VAlert>
            <VTable v-else density="compact">
              <thead>
                <tr><th>文件</th><th>原因</th><th>次数</th><th></th></tr>
              </thead>
              <tbody>
                <tr v-for="item in failures.slice(0, 8)" :key="item.key">
                  <td class="text-caption">{{ item.name }}</td>
                  <td class="text-caption text-error">{{ item.message }}</td>
                  <td class="text-caption">{{ item.count }}</td>
                  <td>
                    <VBtn
                      size="x-small"
                      variant="text"
                      :loading="busy === `retry:${item.key}`"
                      @click="retryOne(item)"
                    >
                      重试
                    </VBtn>
                  </td>
                </tr>
              </tbody>
            </VTable>
          </VCardText>
        </VCard>
      </VCol>
      <VCol cols="12" md="6">
        <VCard variant="tonal">
          <VCardTitle class="d-flex align-center">
            <VIcon icon="mdi-text-box-outline" class="me-2" />运行日志
          </VCardTitle>
          <VCardText style="max-height: 260px; overflow-y: auto">
            <div v-if="!logs.length" class="text-caption text-medium-emphasis">暂无日志</div>
            <div v-for="(log, index) in logs.slice().reverse()" :key="index" class="text-caption mb-1">
              <span class="text-medium-emphasis">{{ log.time }}</span>
              <span :class="log.level === 'error' ? 'text-error' : ''"> {{ log.message }}</span>
            </div>
          </VCardText>
        </VCard>
      </VCol>
    </VRow>

    <VRow class="mt-4">
      <VCol cols="12">
        <VCard variant="tonal">
          <VCardTitle class="d-flex align-center flex-wrap ga-2">
            <VIcon icon="mdi-content-duplicate" class="me-2" />重复检测
            <VChip v-if="quarantinedCount" size="small" color="warning" variant="tonal">
              已隔离 {{ quarantinedCount }}
            </VChip>
            <VChip v-if="status?.dedupe_running" size="small" color="info" variant="tonal">
              查重中…
            </VChip>
            <VSpacer />
            <VBtn
              size="small"
              variant="text"
              :loading="busy === 'restore'"
              :disabled="!quarantinedCount"
              @click="doRestore"
            >
              还原隔离
            </VBtn>
            <VBtn
              size="small"
              variant="tonal"
              color="primary"
              :loading="busy === 'dedupe' || status?.dedupe_running"
              @click="doDetect"
            >
              扫描重复
            </VBtn>
          </VCardTitle>
          <VCardText>
            <div class="text-caption text-medium-emphasis">
              按文件内容识别完全重复，按「曲名 + 艺人 + 时长」识别同曲多版本；只盘点、不自动删除，
              勾选后可移入隔离目录（保留相对路径，随时一键还原）。
            </div>
            <div v-if="dedupeStats.groups" class="d-flex flex-wrap ga-3 mt-2">
              <VChip size="small" variant="tonal">重复组 {{ dedupeStats.groups }}</VChip>
              <VChip size="small" variant="tonal" color="primary">可清理 {{ dedupeStats.duplicate_files }} 个</VChip>
              <VChip size="small" variant="tonal" color="warning">可省 {{ formatSize(dedupeStats.wasted_bytes) }}</VChip>
              <span class="text-caption text-medium-emphasis">{{ status?.dedupe?.time }}</span>
            </div>
          </VCardText>
        </VCard>
      </VCol>
    </VRow>

    <VDialog v-model="dedupeDialog" max-width="1000">
      <VCard>
        <VCardTitle class="d-flex align-center flex-wrap ga-2">
          <VIcon icon="mdi-content-duplicate" class="me-2" />重复扫描结果
          <VSpacer />
          <VBtn size="small" variant="text" @click="toggleDedupeAll">全选 / 取消</VBtn>
          <VBtn icon="mdi-close" variant="text" @click="dedupeDialog = false" />
        </VCardTitle>
        <VCardText style="max-height: 60vh; overflow-y: auto">
          <div v-if="dedupe?.stats" class="d-flex flex-wrap ga-3 mb-3">
            <VChip size="small" variant="tonal">扫描 {{ dedupe.stats.scanned }}</VChip>
            <VChip size="small" variant="tonal">完全重复 {{ dedupe.stats.exact_groups }} 组</VChip>
            <VChip size="small" variant="tonal">同曲多版本 {{ dedupe.stats.track_groups }} 组</VChip>
            <VChip size="small" variant="tonal" color="warning">可省 {{ formatSize(dedupe.stats.wasted_bytes) }}</VChip>
          </div>
          <div v-for="group in dedupe?.groups || []" :key="group.id" class="mb-4">
            <div class="d-flex align-center flex-wrap ga-2 mb-1">
              <VChip
                size="small"
                :color="group.kind === 'exact' ? 'error' : 'warning'"
                variant="tonal"
              >
                {{ group.kind === 'exact' ? '完全重复' : '同曲多版本' }}
              </VChip>
              <span class="text-body-2">
                {{ group.title }}
                <span v-if="group.album" class="text-medium-emphasis"> · {{ group.album }}</span>
              </span>
              <span class="text-caption text-medium-emphasis">可省 {{ formatSize(group.wasted) }}</span>
            </div>
            <VTable density="compact">
              <thead>
                <tr>
                  <th style="width: 44px"></th>
                  <th>文件</th>
                  <th>格式</th>
                  <th>码率</th>
                  <th>大小</th>
                  <th>状态</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="file in group.files" :key="file.path">
                  <td>
                    <VCheckboxBtn
                      v-model="dedupeSelected"
                      :value="file.path"
                      :disabled="file.path === group.keep"
                      density="compact"
                      hide-details
                      color="error"
                    />
                  </td>
                  <td class="text-caption" style="word-break: break-all">{{ file.path }}</td>
                  <td class="text-caption">
                    {{ (file.ext || '').replace('.', '').toUpperCase() }}{{ file.lossless ? ' · 无损' : '' }}
                  </td>
                  <td class="text-caption">{{ file.bitrate ? `${file.bitrate} kbps` : '—' }}</td>
                  <td class="text-caption">{{ formatSize(file.size) }}</td>
                  <td>
                    <VChip v-if="file.path === group.keep" size="x-small" color="success" variant="tonal">
                      保留
                    </VChip>
                    <VChip v-else size="x-small" color="error" variant="tonal">重复</VChip>
                  </td>
                </tr>
              </tbody>
            </VTable>
          </div>
          <VAlert v-if="!dedupe?.groups?.length" type="success" variant="tonal" density="compact">
            未发现重复文件
          </VAlert>
          <div class="text-caption text-medium-emphasis mt-2">
            隔离只会移动文件到隔离目录，不会删除；位置：{{ dedupe?.stats?.quarantine_dir || '默认音乐目录同级' }}
          </div>
        </VCardText>
        <VCardActions>
          <span class="text-caption text-medium-emphasis ms-4">已选 {{ dedupeSelected.length }} 个</span>
          <VSpacer />
          <VBtn variant="text" @click="dedupeDialog = false">关闭</VBtn>
          <VBtn
            color="error"
            variant="tonal"
            :disabled="!dedupeSelected.length"
            :loading="busy === 'quarantine'"
            @click="doQuarantine"
          >
            隔离选中（{{ dedupeSelected.length }}）
          </VBtn>
        </VCardActions>
      </VCard>
    </VDialog>

    <VDialog v-model="previewDialog" max-width="900">
      <VCard>
        <VCardTitle class="d-flex align-center">
          <VIcon icon="mdi-magnify-scan" class="me-2" />试跑结果
          <VSpacer />
          <VBtn icon="mdi-close" variant="text" @click="previewDialog = false" />
        </VCardTitle>
        <VCardText>
          <div v-if="preview?.stats" class="d-flex flex-wrap ga-3 mb-3">
            <VChip size="small" variant="tonal">扫描 {{ preview.stats.scanned }}</VChip>
            <VChip size="small" variant="tonal" color="primary">待处理 {{ preview.stats.candidates }}</VChip>
            <VChip size="small" variant="tonal">跳过 {{ preview.stats.skipped }}</VChip>
            <VChip size="small" variant="tonal" color="warning">
              缺目录封面 {{ preview.stats.missing_folder_cover ?? 0 }}
            </VChip>
          </div>
          <VTable v-if="preview?.items?.length" density="compact">
            <thead>
              <tr>
                <th style="width: 44px">
                  <VCheckboxBtn
                    :model-value="allSelected"
                    density="compact"
                    hide-details
                    color="primary"
                    @update:model-value="toggleAll"
                  />
                </th>
                <th>文件</th><th>缺失</th><th>目录封面</th><th>匹配专辑</th><th>来源</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in preview.items" :key="item.key">
                <td>
                  <VCheckboxBtn v-model="selected" :value="item.key" density="compact" hide-details color="primary" />
                </td>
                <td class="text-caption">{{ item.name }}</td>
                <td class="text-caption">{{ missingLabel(item.missing) }}</td>
                <td class="text-caption">
                  <VChip v-if="item.folder_cover_ok" size="x-small" color="success" variant="tonal">已有</VChip>
                  <VChip v-else size="x-small" color="warning" variant="tonal">待补</VChip>
                </td>
                <td class="text-caption">
                  {{ item.album || '—' }}
                  <span v-if="item.album_artist" class="text-medium-emphasis"> / {{ item.album_artist }}</span>
                  <span v-if="item.year" class="text-medium-emphasis"> ({{ item.year }})</span>
                </td>
                <td class="text-caption">
                  <VChip v-if="item.source" size="x-small" variant="tonal">
                    {{ sourceLabels[item.source] || item.source }}
                  </VChip>
                  <span v-else class="text-medium-emphasis">未命中</span>
                </td>
              </tr>
            </tbody>
          </VTable>
          <VAlert v-else type="info" variant="tonal" density="compact">
            没有待处理音频（已补全或未达到上限）
          </VAlert>
          <div class="text-caption text-medium-emphasis mt-3">
            试跑只做扫描与匹配，不会写入任何标签或歌词。
          </div>
        </VCardText>
        <VCardActions>
          <span class="text-caption text-medium-emphasis ms-4">已选 {{ selected.length }} / {{ preview?.items?.length || 0 }}</span>
          <VSpacer />
          <VBtn variant="text" @click="previewDialog = false">关闭</VBtn>
          <VBtn variant="tonal" :disabled="!preview?.items?.length" @click="doRunSelected">
            仅处理选中（{{ selected.length }}）
          </VBtn>
          <VBtn color="primary" variant="tonal" @click="previewDialog = false; doRun()">全部处理</VBtn>
        </VCardActions>
      </VCard>
    </VDialog>

    <VSnackbar v-model="showMessage" :color="messageType" :timeout="4000" location="bottom">
      {{ message }}
    </VSnackbar>
  </VContainer>
</template>

<style scoped>
.text-h6 {
  letter-spacing: 0.01em;
}
</style>
