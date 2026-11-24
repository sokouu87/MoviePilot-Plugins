<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps({
  api: Object,
  pluginId: { type: String, default: 'SubtitleManualUpload' },
  show_switch: { type: Boolean, default: true },
})
const emit = defineEmits(['close', 'switch'])
const states = {
  all: ['总数', 'primary'], queued: ['等待', 'info'], running: ['处理中', 'warning'],
  done: ['完成', 'success'], failed: ['失败', 'error'], cancelled: ['已取消', 'default'], skipped: ['已跳过', 'default'],
}
const actions = {
  cancel: { name: '取消', color: 'warning', icon: 'mdi-cancel', result: '已提交取消请求' },
  restart: { name: '重新生成', color: 'primary', icon: 'mdi-restart', result: '已提交重新生成' },
  delete: { name: '删除', color: 'error', icon: 'mdi-delete-outline', result: '已删除任务记录' },
}
const pageSize = 100
const stampFormat = new Intl.DateTimeFormat('sv-SE', { dateStyle: 'short', timeStyle: 'medium', hourCycle: 'h23' })
const data = ref({ jobs: [], counts: {}, total: 0 })
const filter = ref('all')
const order = ref('desc')
const offset = ref(0)
const selected = ref([])
const pending = ref(null)
const busy = ref(false)
const loading = ref(false)
const loadError = ref('')
const actionError = ref('')
const notice = ref('')
const picked = computed(() => data.value.jobs.filter(row => selected.value.includes(row.id)))
const allPicked = computed(() => picked.value.length > 0 && picked.value.length === data.value.jobs.length)
let requestId = 0
let timer

async function api(method, endpoint, body) {
  const result = await props.api[method](`plugin/${props.pluginId}/${endpoint}`, body)
  const payload = result?.data ?? result
  if (result?.success === false || payload?.success === false) {
    throw new Error(payload?.message || result?.message || '操作失败')
  }
  return payload?.data ?? payload
}

function errorText(error) {
  return error?.response?.data?.detail || error?.message || '无法访问字幕插件'
}

async function load() {
  const id = ++requestId
  loading.value = true
  try {
    const params = new URLSearchParams({ state: filter.value, order: order.value, offset: offset.value })
    const result = await api('get', 'task_page?' + params)
    if (id !== requestId) return
    if (!result.jobs.length && offset.value) {
      const size = filter.value === 'all' ? result.total : result.counts[filter.value] || 0
      offset.value = Math.floor(Math.max(0, size - 1) / pageSize) * pageSize
      return load()
    }
    data.value = result
    selected.value = selected.value.filter(key => result.jobs.some(row => row.id === key))
    loadError.value = result.history_error || ''
  } catch (error) {
    if (id === requestId) loadError.value = errorText(error)
  } finally {
    if (id === requestId) loading.value = false
  }
}

function selectView(state, sort, start = 0) {
  filter.value = state
  order.value = sort
  offset.value = start
  selected.value = []
  notice.value = ''
  actionError.value = ''
  data.value = { ...data.value, jobs: [] }
  load()
}

function can(action, row) {
  const active = row.state === 'queued' || row.state === 'running'
  return action === 'cancel' ? active && !row.cancelling && !row.publishing : !active
}

function request(action, rows) {
  const ids = rows.filter(row => can(action, row)).map(row => row.id)
  if (!ids.length || busy.value) return
  if (action === 'cancel') return perform({ action, ids })
  pending.value = { action, ids }
}

async function perform(operation) {
  if (!operation || busy.value) return
  pending.value = null
  busy.value = true
  actionError.value = ''
  notice.value = ''
  try {
    const result = await api('post', 'task_actions', operation)
    const skipped = result.skipped.map(item => '#' + item.id + ' ' + item.reason)
    notice.value = `${actions[operation.action].result} ${result.changed.length} 条`
    if (skipped.length) notice.value += `，跳过 ${skipped.length} 条（${skipped.slice(0, 3).join('、')}）`
    selected.value = []
    await load()
  } catch (error) {
    actionError.value = errorText(error)
  } finally {
    busy.value = false
  }
}

function utc(value) {
  return value.replace(' ', 'T') + 'Z'
}

function when(value) {
  const date = new Date(utc(value))
  return Number.isNaN(date.valueOf()) ? value : stampFormat.format(date)
}

function pathText(path) {
  return path.replace(/([\\/])((?:Season[ _.-]*\d+|S\d{1,2})(?:[\\/]|$))/i, '$1\n$2')
}

function hasReview(report) {
  return report.sources?.length || report.ambiguities?.length || Object.keys(report.warnings || {}).length
}

onMounted(() => {
  load()
  timer = setInterval(() => {
    if (!document.hidden && !busy.value && !loading.value && !pending.value) load()
  }, 8000)
})
onBeforeUnmount(() => { ++requestId; clearInterval(timer) })
</script>

<template>
  <div class="records">
    <header class="toolbar">
      <div class="heading">
        <h2>海拉鲁 AI 字幕</h2>
        <p>{{ data.auto === undefined ? '字幕任务' : data.auto ? '已接管入库自动翻译' : '手动翻译' }}<template v-if="data.model"> · {{ data.model }} · {{ data.effort }}</template></p>
      </div>
      <div class="tools" role="group" aria-label="任务操作">
        <VBtn color="primary" variant="tonal" :prepend-icon="order === 'desc' ? 'mdi-sort-clock-descending' : 'mdi-sort-clock-ascending'"
              @click="selectView(filter, order === 'desc' ? 'asc' : 'desc')">{{ order === 'desc' ? '最新在前' : '最早在前' }}</VBtn>
        <VBtn color="primary" variant="tonal" prepend-icon="mdi-checkbox-multiple-marked-outline" :disabled="!data.jobs.length || busy"
              @click="selected = allPicked ? [] : data.jobs.map(row => row.id)">
          {{ allPicked ? '取消全选' : (offset || data.more ? '全选本页' : '全选') }}
        </VBtn>
        <VBtn v-for="(spec, action) in actions" :key="action" :color="spec.color" variant="tonal" :prepend-icon="spec.icon"
              :disabled="busy || !picked.some(row => can(action, row))" @click="request(action, picked)">批量{{ spec.name }}</VBtn>
        <VBtn icon="mdi-refresh" color="primary" variant="text" aria-label="刷新任务" title="刷新任务" :loading="loading" :disabled="busy" @click="load" />
        <VBtn v-if="show_switch" icon="mdi-cog-outline" color="primary" variant="text" aria-label="插件设置" title="插件设置" @click="emit('switch')" />
        <VBtn icon="mdi-close" color="primary" variant="text" aria-label="关闭" title="关闭" @click="emit('close')" />
      </div>
    </header>
    <main class="content">
      <nav class="filters" aria-label="按任务状态筛选">
        <VChip v-for="([label, color], state) in states" :key="state" tag="button" type="button" size="small" :color="color"
               :variant="filter === state ? 'flat' : 'tonal'" :aria-pressed="filter === state" @click="selectView(state, order)">
          {{ label }} {{ state === 'all' ? data.total : data.counts[state] || 0 }}
        </VChip>
      </nav>
      <p v-if="loadError || actionError" class="feedback error-text" role="alert">{{ actionError || loadError }}</p>
      <p v-if="notice" class="feedback" role="status">{{ notice }}</p>
      <p v-if="!data.jobs.length && !loadError" class="empty">{{ loading ? '正在读取任务…' : filter === 'all' ? '暂无字幕任务' : '当前筛选暂无任务' }}</p>
      <div class="cards">
        <article v-for="row in data.jobs" :key="row.id" class="task" :class="{ marked: selected.includes(row.id) }">
          <label class="pick"><input v-model="selected" type="checkbox" :value="row.id" :aria-label="'选择 ' + row.file"></label>
          <div class="body">
            <div class="title">
              <strong>{{ row.file }}</strong>
              <VChip size="x-small" variant="tonal" :color="states[row.state]?.[1]">
                {{ row.cancelling ? '取消中' : row.state === 'done' ? '已完成' : states[row.state]?.[0] || row.state }}
              </VChip>
            </div>
            <div class="path">{{ pathText(row.path) }}</div>
            <div class="meta">
              <span>{{ row.origin }}<template v-if="row.legacy"> · 联动版历史</template></span>
              <span v-if="row.report.source">{{ row.report.source }}</span>
              <span v-if="row.report.files?.length">输出：{{ row.report.files.join('、') }}</span>
              <time v-if="row.created" :datetime="utc(row.created)" title="创建时间">{{ when(row.created) }}</time>
              <time v-if="row.finished" :datetime="utc(row.finished)" title="结束时间">{{ when(row.finished) }}</time>
              <time v-else-if="row.report.rendered" :datetime="utc(row.report.rendered)">译稿生成时间 {{ when(row.report.rendered) }}</time>
            </div>
            <p class="detail" :class="{ 'error-text': row.state === 'failed' }">{{ row.cancelling ? '正在取消，等待当前步骤结束' : row.detail }}</p>
            <details v-if="hasReview(row.report)">
              <summary>审校记录</summary>
              <p v-for="(words, id) in row.report.warnings" :key="id">第 {{ id }} 轴 · {{ words.join('、') }}</p>
              <p v-for="a in row.report.ambiguities" :key="a.id">第 {{ a.id }} 轴 · {{ a.options.join(' / ') }} · {{ a.reason }}</p>
              <div v-for="url in row.report.sources" :key="url"><a :href="url" target="_blank" rel="noopener noreferrer">{{ url }}</a></div>
            </details>
          </div>
          <div class="actions">
            <VBtn v-for="(spec, action) in actions" :key="action" size="small" :color="spec.color" variant="tonal"
                  :disabled="busy || !can(action, row)" @click="request(action, [row])">{{ spec.name }}</VBtn>
          </div>
        </article>
      </div>
      <nav v-if="offset || data.more" class="pages" aria-label="任务分页">
        <VBtn size="small" variant="tonal" :disabled="!offset || loading" @click="selectView(filter, order, offset - pageSize)">上一页</VBtn>
        <span>第 {{ offset / pageSize + 1 }} 页</span>
        <VBtn size="small" variant="tonal" :disabled="!data.more || loading" @click="selectView(filter, order, offset + pageSize)">下一页</VBtn>
      </nav>
    </main>
    <VDialog :model-value="Boolean(pending)" max-width="420" aria-labelledby="hyrule-confirm" @update:model-value="open => { if (!open) pending = null }">
      <VCard v-if="pending">
        <VCardTitle id="hyrule-confirm">{{ actions[pending.action].name }} {{ pending.ids.length }} 条任务？</VCardTitle>
        <VCardText>{{ pending.action === 'delete' ? '移除所选任务记录。视频和字幕文件会保留。' : '用当前订阅模型重新翻译。新字幕将使用独立文件名。' }}</VCardText>
        <VCardActions>
          <VSpacer />
          <VBtn variant="text" @click="pending = null">返回</VBtn>
          <VBtn variant="tonal" :color="actions[pending.action].color" @click="perform(pending)">{{ actions[pending.action].name }}</VBtn>
        </VCardActions>
      </VCard>
    </VDialog>
  </div>
</template>

<style scoped>
.records {
  --paper: rgb(var(--v-theme-surface, 255, 255, 255));
  --muted: rgba(var(--v-theme-on-surface, 38, 38, 47), .72);
  --line: rgba(var(--v-border-color, 92, 92, 110), .16);
  min-height: 100%;
  color: rgb(var(--v-theme-on-surface, 38, 38, 47));
  background: rgb(var(--v-theme-background, 244, 244, 248));
}
.toolbar {
  position: sticky;
  top: 0;
  z-index: 2;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 6px 10px;
  padding: 6px 8px 6px 12px;
  border-bottom: 1px solid var(--line);
  background: var(--paper);
}
.heading h2 { margin: 0; font-size: 20px; font-weight: 600; line-height: 1.35; }
.heading p { margin: 0; color: var(--muted); font-size: 12px; line-height: 1.4; }
.tools, .actions, .filters, .title, .meta, .pages { display: flex; align-items: center; flex-wrap: wrap; }
.tools { gap: 2px; }
.content { padding: 18px; }
.filters { gap: 8px; margin-bottom: 14px; }
.feedback { margin: 0 0 12px; }
.cards { display: grid; gap: 10px; }
.task {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--paper);
}
.task.marked { border-color: rgba(var(--v-theme-primary, 128, 78, 238), .5); }
.pick { display: flex; align-items: center; min-height: 36px; cursor: pointer; }
.pick input { width: 18px; height: 18px; accent-color: rgb(var(--v-theme-primary, 128, 78, 238)); }
.body { min-width: 0; overflow-wrap: anywhere; }
.title { gap: 8px; }
.title strong { font-size: 16px; line-height: 1.45; }
.path { max-width: 78ch; margin-top: 6px; color: var(--muted); font-size: 13px; line-height: 1.5; white-space: pre-wrap; }
.meta { gap: 2px 10px; margin-top: 6px; color: var(--muted); font-size: 12px; }
.detail, .body details { margin: 7px 0 0; color: var(--muted); font-size: 12px; line-height: 1.5; }
.body summary { cursor: pointer; }
.body a { color: rgb(var(--v-theme-primary, 128, 78, 238)); }
.records .error-text { color: rgb(var(--v-theme-error, 209, 47, 58)); }
.actions { gap: 8px; justify-content: flex-end; }
.pages { justify-content: center; gap: 10px; margin-top: 14px; }
.empty { padding: 24px; text-align: center; color: var(--muted); }
@media (max-width: 800px) {
  .toolbar { position: static; padding: 10px 12px; }
  .content { padding: 12px; }
  .tools { gap: 4px; }
  .task { grid-template-columns: 26px minmax(0, 1fr); gap: 6px; padding: 11px; }
  .task .actions { grid-column: 2; justify-content: flex-start; }
}
</style>
