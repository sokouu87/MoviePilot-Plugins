<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import MediaDialog from './MediaDialog.vue'

const props = defineProps({
  api: Object,
  pluginId: { type: String, default: 'SubtitleManualUpload' },
  show_switch: { type: Boolean, default: true },
  show_close: { type: Boolean, default: true },
  compact: Boolean,
  allowRefresh: { type: Boolean, default: true },
})
const emit = defineEmits(['close', 'switch'])
const filters = {
  all: ['全部', 'primary'], recent: ['最近入库', 'primary'], present: ['已有中文', 'success'], missing: ['缺中文', 'warning'],
  unknown: ['待确认', 'default'], disc: ['原盘', 'secondary'],
  queued: ['等待', 'info'], running: ['处理中', 'warning'], done: ['已完成', 'success'],
  failed: ['失败', 'error'], cancelled: ['已取消', 'default'], skipped: ['已跳过', 'default'],
}
const actions = {
  cancel: { label: '取消', color: 'warning', result: '已提交取消请求' },
  restart: { label: '重新生成', color: 'primary', result: '已提交重新生成' },
  delete: { label: '删除', color: 'error', result: '已删除任务记录' },
}
const data = ref({ rows: [], counts: {}, matches: 0, page_size: 50 })
const query = ref(''), filter = ref(props.compact ? 'recent' : 'all')
const kind = ref(props.compact ? 'Movie' : 'all'), order = ref('desc'), offset = ref(0)
const selected = ref([]), pending = ref(null), upload = ref(null), history = ref(null)
const loading = ref(false), busy = ref(false), loadError = ref(''), actionError = ref(''), notice = ref('')
const selectable = computed(() => data.value.rows.filter(row => row.task).map(row => row.task.id))
const picked = computed(() => data.value.rows.filter(row => row.task && selected.value.includes(row.task.id)))
const allPicked = computed(() => selectable.value.length > 0 && selected.value.length === selectable.value.length)
const visibleRows = computed(() => props.compact ? data.value.rows.slice(0, 3) : data.value.rows)
const searchPage = computed(() => '#/plugin-app/' + encodeURIComponent(props.pluginId) + '/main')
let requestNumber = 0
let timer, debounce

async function call(method, endpoint, body) {
  const response = await props.api[method](`plugin/${props.pluginId}/${endpoint}`, body)
  const payload = response?.data ?? response
  if (response?.success === false || payload?.success === false)
    throw new Error(payload?.message || response?.message || '操作失败')
  return payload?.data ?? payload
}

function errorText(error) {
  return error?.response?.data?.detail || error?.message || '无法访问字幕插件'
}

async function load() {
  const number = ++requestNumber
  loading.value = true
  try {
    const params = new URLSearchParams({ q: query.value, state: filter.value, kind: kind.value, order: order.value, offset: offset.value })
    const result = await call('get', 'library_page?' + params)
    if (number !== requestNumber) return
    if (offset.value && !result.rows.length) {
      offset.value = 0
      return load()
    }
    data.value = result
    selected.value = selected.value.filter(id => selectable.value.includes(id))
    loadError.value = result.error || result.history_error || ''
  } catch (error) {
    if (number === requestNumber) loadError.value = errorText(error)
  } finally {
    if (number === requestNumber) loading.value = false
  }
}

function select(state, direction = order.value, from = 0) {
  clearTimeout(debounce)
  filter.value = state
  order.value = direction
  offset.value = from
  selected.value = []
  load()
}

function active(job) {
  return job?.state === 'queued' || job?.state === 'running'
}

function can(action, row) {
  const job = row.task
  if (!job) return false
  if (action === 'cancel') return active(job) && !job.cancelling && !job.publishing
  if (action === 'restart') return !row.original && row.available && !active(job)
  return !active(job)
}

async function act(fn) {
  if (busy.value) return
  busy.value = true
  actionError.value = notice.value = ''
  try {
    await fn()
  } catch (error) {
    actionError.value = errorText(error)
  } finally {
    busy.value = false
  }
}

function request(action, rows) {
  const ids = rows.filter(row => can(action, row)).map(row => row.task.id)
  if (!ids.length) return
  if (action === 'cancel') return perform({ action, ids })
  pending.value = { action, ids }
}

function perform(operation) {
  pending.value = null
  return act(async () => {
    const result = await call('post', 'task_actions', operation)
    const skipped = result.skipped.map(item => `#${item.id} ${item.reason}`)
    notice.value = actions[operation.action].result + ` ${result.changed.length} 条`
    if (skipped.length) notice.value += `，跳过 ${skipped.length} 条（${skipped.slice(0, 3).join('、')}）`
    selected.value = []
    await load()
  })
}

function generate(row) {
  if (row.task && (row.task.state !== 'failed' || row.task.legacy)) return request('restart', [row])
  return act(async () => {
    if (row.task?.state === 'failed') {
      await call('post', 'retry', { id: row.task.id })
      notice.value = `任务 #${row.task.id} 已进入队列`
    } else {
      const ready = await call('post', 'library_target', { id: row.id })
      const result = await call('post', 'translate', { target: ready.target })
      notice.value = `任务 #${result.id} 已进入队列`
    }
    await load()
  })
}

function refresh() {
  return act(async () => {
    await call('post', 'refresh', {})
    await call('post', 'inventory_scan', {})
    await load()
  })
}

function loadHistory(row, at = 0) {
  return act(async () => {
    const result = await call('get', `task_page?target=${encodeURIComponent(row.target)}&offset=${at}`)
    history.value = { row, at, ...result }
  })
}

function aiLabel(row) {
  if (active(row.task)) return row.task.state === 'queued' ? '已排队' : '生成中'
  if (row.task?.state === 'failed' && !row.task.legacy) return '从断点重试'
  return row.task ? '重新生成' : 'AI 生成'
}

function badges(row) {
  const result = []
  const job = row.task
  const source = job?.report?.source || ''
  const files = job?.report?.files || []
  if (row.original) result.push(['原盘', 'secondary'])
  const scripts = row.chinese_scripts ?? []
  if (scripts.includes('hans')) result.push(['内嵌简中', 'var(--embedded-chinese-color)'])
  if (scripts.includes('hant')) result.push(['内嵌繁中', 'var(--embedded-chinese-color)'])
  if (!scripts.length && (row.chinese.includes('embedded') || /内封|内嵌/.test(source)))
    result.push(['视频内嵌字幕', 'info'])
  if (row.chinese.includes('external')) result.push(['外挂中文', 'success'])
  if (job?.state === 'done' && (files.some(f => f.endsWith('.zh-en.ai.ass')) && files.some(f => f.endsWith('.zh-en.ai.srt'))
      || /生成双语 ASS 和 SRT/.test(job.detail))) result.push(['已生成双语 ASS 和 SRT', 'success'])
  if (job?.state === 'failed' && /缺少英文字幕|无英文字幕|没有英文字幕|未提取到可用外挂/.test(job.detail))
    result.push(['缺少英文字幕', 'warning'])
  if (row.status === 'missing') result.push(['缺中文字幕', 'warning'])
  if (row.status === 'unknown' && row.emby) result.push(['字幕待确认', 'default'])
  return result
}

function when(value, utc = false) {
  const date = new Date(utc ? value.replace(' ', 'T') + 'Z' : value)
  return Number.isNaN(date.valueOf()) ? value : date.toLocaleString('zh-CN', { hour12: false })
}

watch(query, () => {
  clearTimeout(debounce)
  debounce = setTimeout(() => select(filter.value), 230)
})
onMounted(() => {
  load()
  timer = setInterval(() => {
    if (props.allowRefresh && !document.hidden && !busy.value && !loading.value && !pending.value && !upload.value && !history.value) load()
  }, props.compact ? 30000 : 7000)
})
onBeforeUnmount(() => { ++requestNumber; clearInterval(timer); clearTimeout(debounce) })
</script>

<template>
  <div class="records" :class="{ compact }">
    <header v-if="compact" class="dashboard-head">
      <h2>海拉鲁 AI 字幕</h2>
      <VBtn size="small" variant="text" color="primary" :href="searchPage" prepend-icon="mdi-magnify">搜索片库</VBtn>
    </header>
    <header v-else class="toolbar">
      <div class="heading">
        <h2>海拉鲁 AI 字幕</h2>
        <p v-if="data.model">{{ data.model }} · {{ data.effort }}</p>
      </div>
      <div class="search">
        <input v-model="query" type="search" autocomplete="off" aria-label="搜索最近入库和 Emby 片库" placeholder="搜索片库">
        <select v-model="kind" aria-label="筛选媒体类型" @change="select(filter)">
          <option value="all">全部类型</option><option value="Movie">电影</option><option value="Episode">剧集</option>
        </select>
      </div>
      <div class="tools">
        <VBtn class="toolbar-action" size="small" color="primary" variant="tonal" :disabled="busy"
              :aria-label="order === 'desc' ? '最新在前' : '最早在前'" :title="order === 'desc' ? '最新在前' : '最早在前'"
              @click="select(filter, order === 'desc' ? 'asc' : 'desc')">
          <VIcon :icon="order === 'desc' ? 'mdi-sort-calendar-descending' : 'mdi-sort-calendar-ascending'" />
          <span class="tool-label">{{ order === 'desc' ? '最新在前' : '最早在前' }}</span>
        </VBtn>
        <VBtn class="toolbar-action" size="small" color="primary" variant="tonal" :disabled="busy || data.scanning"
              aria-label="刷新片库" title="刷新片库" @click="refresh">
          <VIcon icon="mdi-refresh" /><span class="tool-label">刷新片库</span>
        </VBtn>
        <VBtn v-if="show_switch" icon="mdi-cog-outline" size="small" variant="text" aria-label="插件设置" @click="emit('switch')" />
        <VBtn v-if="show_close" icon="mdi-close" size="small" variant="text" aria-label="关闭" @click="emit('close')" />
      </div>
    </header>

    <component :is="compact ? 'div' : 'main'" class="content">
      <nav v-if="!compact" class="filters" aria-label="筛选片源和任务">
        <VChip v-for="([label, color], state) in filters" :key="state" tag="button" type="button" size="small" :color="color"
               :variant="filter === state ? 'flat' : 'tonal'" :aria-pressed="filter === state" @click="select(state)">
          {{ label }} {{ data.counts[state] || 0 }}
        </VChip>
      </nav>
      <div v-if="!compact && selectable.length" class="batch" role="group" aria-label="批量管理任务">
        <VBtn size="small" variant="text" :disabled="busy" @click="selected = allPicked ? [] : [...selectable]">
          {{ allPicked ? '取消全选' : '全选本页任务' }}
        </VBtn>
        <template v-if="picked.length">
          <VBtn v-for="(spec, action) in actions" :key="action" size="small" variant="tonal" :color="spec.color"
                :disabled="busy || !picked.some(row => can(action, row))" @click="request(action, picked)">批量{{ spec.label }}</VBtn>
        </template>
      </div>
      <p v-if="!compact && data.scanning" class="feedback" role="status">{{ data.progress || '正在读取 Emby 片库…' }}</p>
      <p v-if="loadError || actionError" class="feedback error-text" role="alert">{{ actionError || loadError }}</p>
      <p v-if="notice" class="feedback" role="status">{{ notice }}</p>
      <p v-if="!visibleRows.length && !loadError" class="empty">{{ loading ? '正在读取…' : compact ? '暂无最近入库电影' : '当前筛选没有片源' }}</p>

      <div class="cards">
        <article v-for="row in visibleRows" :key="row.id" class="task" :class="{ marked: selected.includes(row.task?.id) }">
          <label v-if="!compact" class="pick"><input v-if="row.task" v-model="selected" type="checkbox" :value="row.task.id" :aria-label="'选择任务 ' + row.title"></label>
          <div class="body">
            <div class="title">
              <strong :title="compact ? row.title || row.file : undefined">{{ row.title || row.file }}</strong>
              <VChip v-if="row.task" class="row-state" size="x-small" variant="tonal" :color="filters[row.task.state]?.[1]">
                {{ row.task.cancelling ? '取消中' : filters[row.task.state]?.[0] }}
              </VChip>
            </div>
            <template v-if="!compact">
            <div v-if="badges(row).length" class="badges">
              <VChip v-for="([label,color]) in badges(row)" :key="label" size="small" variant="tonal" :color="color">{{ label }}</VChip>
            </div>
            <div class="path" v-if="row.original && row.directory">影片目录 {{ row.directory }}</div>
            <div class="path" v-else-if="row.file">{{ row.file }}</div>
            <div class="meta">
              <span>{{ row.recent ? 'MoviePilot 入库' : '' }}{{ row.recent && row.emby ? ' · ' : '' }}{{ row.emby ? 'Emby' : '' }}</span>
              <time v-if="row.added">{{ when(row.added) }}</time>
              <span v-if="row.task?.origin">{{ row.task.origin }}</span>
            </div>
            <p v-if="row.reason || row.task?.detail" class="detail" :class="{ 'error-text': row.task?.state === 'failed' }">
              {{ row.task?.detail || row.reason }}
            </p>
            <details v-if="row.task">
              <summary>任务 #{{ row.task.id }} · 字幕与审校记录</summary>
              <p v-if="row.task.report.source">{{ row.task.report.source }}</p>
              <p v-if="row.task.report.translation_mode === 'embedded_chinese'">
                英文复用 {{ row.task.report.existing_english || 0 }} 条 · AI 补齐 {{ row.task.report.generated_english || 0 }} 条
              </p>
              <p v-if="row.task.created">{{ when(row.task.created, true) }}<template v-if="row.task.finished"> · 完成 {{ when(row.task.finished, true) }}</template></p>
              <p v-for="file in row.task.report.files" :key="file">{{ file }}</p>
              <p v-for="(issues,id) in row.task.report.warnings" :key="id">第 {{ id }} 轴 · {{ issues.join('、') }}</p>
              <p v-for="item in row.task.report.ambiguities" :key="item.id">第 {{ item.id }} 轴 · {{ item.options.join(' / ') }} · {{ item.reason }}</p>
              <div v-for="url in row.task.report.sources" :key="url">
                <a v-if="/^https?:\/\//i.test(url)" :href="url" target="_blank" rel="noopener noreferrer">{{ url }}</a>
              </div>
              <VBtn v-if="row.task_count > 1" size="small" variant="text" @click="loadHistory(row)">历史任务 {{ row.task_count }}</VBtn>
            </details>
            </template>
          </div>
          <div class="actions">
            <VBtn class="quick-action" size="small" variant="tonal" :href="row.search_url" target="_blank" rel="noopener noreferrer">SubHD{{ compact ? '' : ' ↗' }}</VBtn>
            <VBtn class="quick-action" size="small" variant="tonal" color="primary" :disabled="busy" @click="upload = row">上传</VBtn>
            <VBtn v-if="!row.original" class="quick-action" size="small" variant="tonal" color="primary"
                  :aria-label="aiLabel(row)" :title="compact ? aiLabel(row) : undefined"
                  :disabled="busy || !data.configured || !row.available || active(row.task)" @click="generate(row)">{{ compact ? 'AI' : aiLabel(row) }}</VBtn>
            <VBtn v-if="!compact && can('cancel', row)" size="small" variant="text" color="warning" :disabled="busy" @click="request('cancel', [row])">取消</VBtn>
          </div>
        </article>
      </div>
      <nav v-if="!compact && (offset || data.more)" class="pages" aria-label="片源分页">
        <VBtn size="small" variant="tonal" :disabled="!offset || loading" @click="select(filter, order, offset - data.page_size)">上一页</VBtn>
        <span>第 {{ offset / data.page_size + 1 }} 页</span>
        <VBtn size="small" variant="tonal" :disabled="!data.more || loading" @click="select(filter, order, offset + data.page_size)">下一页</VBtn>
      </nav>
    </component>

    <MediaDialog v-if="upload" :row="upload" :call="call" @close="upload = null" @changed="load" />
    <VDialog :model-value="Boolean(pending)" max-width="420" aria-labelledby="hyrule-confirm" @update:model-value="open => { if (!open) pending = null }">
      <VCard v-if="pending">
        <VCardTitle id="hyrule-confirm">{{ actions[pending.action].label }} {{ pending.ids.length }} 条任务？</VCardTitle>
        <VCardText>{{ pending.action === 'delete' ? '移除任务记录，保留视频和字幕文件。' : '使用当前订阅模型翻译，字幕另存为独立版本。' }}</VCardText>
        <VCardActions><VSpacer /><VBtn @click="pending = null">返回</VBtn>
          <VBtn :color="actions[pending.action].color" @click="perform(pending)">{{ actions[pending.action].label }}</VBtn>
        </VCardActions>
      </VCard>
    </VDialog>
    <VDialog :model-value="Boolean(history)" max-width="640" aria-labelledby="hyrule-history" @update:model-value="open => { if (!open) history = null }">
      <VCard v-if="history">
        <VCardTitle id="hyrule-history">{{ history.row.title }} · 历史任务</VCardTitle>
        <VCardText>
          <p v-for="job in history.jobs" :key="job.id">#{{ job.id }} · {{ filters[job.state]?.[0] }} · {{ job.detail }}</p>
        </VCardText>
        <VCardActions><VSpacer />
          <VBtn v-if="history.at" @click="loadHistory(history.row, history.at - 100)">上一页</VBtn>
          <VBtn v-if="history.more" @click="loadHistory(history.row, history.at + 100)">下一页</VBtn>
          <VBtn @click="history = null">关闭</VBtn>
        </VCardActions>
      </VCard>
    </VDialog>
  </div>
</template>

<style scoped>
.records {
  --embedded-chinese-color: #5e35b1;
  --paper: rgb(var(--v-theme-surface, 255, 255, 255));
  --muted: rgba(var(--v-theme-on-surface, 38, 38, 47), .72);
  --line: rgba(var(--v-border-color, 92, 92, 110), .18);
  min-height: 100%;
  color: rgb(var(--v-theme-on-surface, 38, 38, 47));
  background: rgb(var(--v-theme-background, 244, 244, 248));
}
@supports (color: light-dark(black, white)) {
  .records { --embedded-chinese-color: light-dark(#5e35b1, #d1b8ff); }
}
.toolbar {
  position: sticky;
  top: 0;
  z-index: 2;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border-bottom: 1px solid var(--line);
  background: var(--paper);
}
.heading { display: flex; align-items: baseline; gap: 8px; white-space: nowrap; }
.heading h2 { margin: 0; font-size: 17px; }
.heading p { margin: 0; color: var(--muted); font-size: 12px; }
.filters, .batch, .badges, .title, .actions, .meta, .pages {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 7px;
}
.content { padding: 16px; }
.tools, .search { display: flex; align-items: center; gap: 6px; }
.search { flex: 1; min-width: 0; }
.search input { flex: 1; }
.search input, .search select {
  min-width: 0;
  min-height: 38px;
  padding: .35rem .6rem;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--paper);
  color: inherit;
  font: inherit;
}
.search select { appearance: auto; }
.tool-label { margin-inline-start: 4px; }
.pages span { color: var(--muted); font-size: 13px; }
.filters { margin-bottom: 12px; }
.batch { margin: 0 0 8px; }
.cards { display: grid; gap: 10px; }
.task {
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 12px;
  background: var(--paper);
}
.task.marked { border-color: rgba(var(--v-theme-primary, 128, 78, 238), .55); }
.pick { display: grid; place-items: center; min-height: 34px; }
.pick input { width: 17px; height: 17px; accent-color: rgb(var(--v-theme-primary, 128, 78, 238)); }
.body { min-width: 0; overflow-wrap: anywhere; }
.title strong { font-size: 16px; }
.badges, .path, .meta, .detail, .body details { margin-top: 5px; }
.path, .meta, .detail, .body details { color: var(--muted); font-size: 12px; line-height: 1.5; }
.body summary { cursor: pointer; }
.body a { color: rgb(var(--v-theme-primary, 128, 78, 238)); }
.error-text { color: rgb(var(--v-theme-error, 209, 47, 58)); }
.actions { justify-content: flex-end; }
.feedback { margin: 8px 0; }
.pages { justify-content: center; margin-top: 14px; }
.empty { text-align: center; padding: 24px; }
@media (max-width: 800px) {
  .toolbar { position: static; padding: 7px 8px; gap: 4px; }
  .toolbar .heading { display: none; }
  .tools, .search { gap: 4px; }
  .search select { max-width: 6em; padding-inline: .25rem; }
  .toolbar-action { min-width: 38px; padding-inline: 0; }
  .tool-label { display: none; }
  .content { padding: 10px; }
  .task { grid-template-columns: 22px minmax(0, 1fr); gap: 6px; padding: 10px; }
  .task .actions { grid-column: 2; justify-content: flex-start; }
}
.compact { min-height: auto; background: var(--paper); border: 1px solid var(--line); border-radius: 10px; }
.dashboard-head {
  min-height: 36px;
  padding: 0 8px 0 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  border-bottom: 1px solid var(--line);
}
.dashboard-head h2 { font-size: 14px; margin: 0; white-space: nowrap; }
.compact .content { padding: 0 8px 4px; }
.compact .cards { gap: 0; }
.compact .task {
  grid-template-columns: minmax(0, 1fr) auto;
  padding: 4px;
  border: 0;
  border-radius: 0;
  min-height: 36px;
  gap: 4px;
}
.compact .task + .task { border-top: 1px solid var(--line); }
.compact .title, .compact .actions { flex-wrap: nowrap; gap: 4px; }
.compact .title strong { font-size: 13px; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.compact .row-state { flex: none; }
.compact .task .actions { grid-column: auto; justify-content: flex-end; }
.compact .quick-action { min-width: 29px; min-height: 30px; padding-inline: 5px; font-size: 11px; }
.compact .empty { padding: 10px; margin: 0; font-size: 13px; }
</style>
