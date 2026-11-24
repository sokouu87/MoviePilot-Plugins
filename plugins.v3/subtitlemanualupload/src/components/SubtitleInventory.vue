<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({ api: Object, pluginId: String })
const labels = { all: '全部', present: '已有中文', missing: '缺中文字幕', unknown: '待确认', disc: '原盘分段' }
const kind = ref('all'), state = ref('missing'), q = ref(''), offset = ref(0)
const data = ref({ rows: [], matches: 0, page_size: 100 })
const loading = ref(false), starting = ref(false), error = ref('')
const counts = computed(() => data.value.summary?.[kind.value])
let generation = 0
let poll, debounce

async function request(method, endpoint) {
  const result = await props.api[method](`plugin/${props.pluginId}/${endpoint}`)
  const payload = result?.data ?? result
  if (result?.success === false || payload?.success === false)
    throw new Error(payload?.message || result?.message || '无法读取字幕清单')
  return payload?.data ?? payload
}

function failed(reason) {
  error.value = reason?.response?.data?.detail || reason?.message || '无法读取字幕清单'
}

async function load() {
  const pending = ++generation
  loading.value = true
  try {
    const params = new URLSearchParams({ state: state.value, kind: kind.value, q: q.value, offset: offset.value })
    const snapshot = await request('get', 'subtitle_inventory?' + params)
    if (pending !== generation) return
    if (offset.value && !snapshot.rows.length) {
      offset.value = 0
      return load()
    }
    data.value = snapshot
    error.value = snapshot.error || ''
  } catch (reason) {
    if (pending === generation) failed(reason)
  } finally {
    if (pending === generation) loading.value = false
  }
}

async function scan() {
  starting.value = true
  error.value = ''
  try {
    await request('post', 'inventory_scan')
    await load()
  } catch (reason) { failed(reason) }
  finally { starting.value = false }
}

function select(nextState, nextKind = kind.value, nextOffset = 0) {
  clearTimeout(debounce)
  state.value = nextState
  kind.value = nextKind
  offset.value = nextOffset
  load()
}

function title(row) {
  if (row.type === 'Movie') return row.year ? `${row.title} (${row.year})` : row.title
  const season = row.season == null ? '' : 'S' + String(row.season).padStart(2, '0')
  const episode = row.episode == null ? '' : 'E' + String(row.episode).padStart(2, '0')
  const end = row.episode_end > row.episode ? '–E' + String(row.episode_end).padStart(2, '0') : ''
  return [row.series, season + episode + end, row.title].filter(Boolean).join(' · ')
}

function notes(row) {
  return [row.bilingual && '中英双语', row.chinese.includes('embedded') && '内封中文',
    row.chinese.includes('external') && '外挂中文', row.english && '有英文文本', row.reason].filter(Boolean).join(' · ')
}

watch(q, () => {
  clearTimeout(debounce)
  debounce = setTimeout(() => select(state.value), 200)
})
onMounted(() => {
  load()
  poll = setInterval(() => { if (data.value.scanning && !loading.value && !document.hidden) load() }, 3000)
})
onBeforeUnmount(() => { ++generation; clearInterval(poll); clearTimeout(debounce) })
</script>

<template>
  <section class="inventory">
    <header>
      <h3>片库字幕清单</h3>
      <VBtn color="primary" variant="tonal" :disabled="starting || data.scanning" @click="scan">
        {{ data.created ? '重新清点片库' : '清点整个 Emby 片库' }}
      </VBtn>
    </header>
    <p v-if="data.scanning" role="status">{{ data.progress || '正在清点 Emby 片库…' }}</p>
    <p v-if="error" role="alert" class="inventory-error">{{ error }}</p>
    <p v-if="!data.created && !data.scanning && !loading">清点会读取电影和单集的字幕轨，生成一份可筛选的清单。</p>
    <template v-if="data.created">
      <p class="inventory-meta">
        {{ new Date(data.created).toLocaleString('zh-CN', { hour12: false }) }} ·
        {{ data.summary.Movie.items }} 条电影记录 · {{ data.summary.Episode.items }} 条单集记录 ·
        {{ data.summary.all.total }} 个片源
      </p>
      <div class="inventory-filters" role="group" aria-label="字幕覆盖状态">
        <VBtn v-for="(label, key) in labels" :key="key" size="small" color="primary"
              :variant="state === key ? 'flat' : 'tonal'" :aria-pressed="state === key" @click="select(key)">
          {{ label }} {{ key === 'all' ? counts.total : counts[key] }}
        </VBtn>
      </div>
      <div class="inventory-filters">
        <label>类型
          <select :value="kind" @change="select(state, $event.target.value)">
            <option value="all">全部影视</option>
            <option value="Movie">电影</option>
            <option value="Episode">剧集</option>
          </select>
        </label>
        <input v-model="q" type="search" aria-label="搜索字幕清单" placeholder="片名、剧名、S01E01 或文件名">
      </div>
      <div v-if="data.rows.length" class="inventory-table">
        <table aria-label="字幕清点结果">
          <thead><tr><th>作品</th><th>片源</th><th>字幕</th></tr></thead>
          <tbody>
            <tr v-for="(row, i) in data.rows" :key="i">
              <td>{{ title(row) }}</td>
              <td>{{ row.file || 'Emby 条目 ' + row.item }}</td>
              <td><strong>{{ labels[row.state] }}</strong><small v-if="notes(row)">{{ notes(row) }}</small></td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-else>{{ loading ? '正在读取清单…' : '当前筛选没有结果' }}</p>
      <nav class="inventory-filters" aria-label="字幕清单分页">
        <VBtn size="small" variant="tonal" :disabled="!offset || loading"
              @click="select(state, kind, offset - data.page_size)">上一页</VBtn>
        <span>{{ data.matches }} 个结果 · 第 {{ offset / data.page_size + 1 }} 页</span>
        <VBtn size="small" variant="tonal" :disabled="offset + data.page_size >= data.matches || loading"
              @click="select(state, kind, offset + data.page_size)">下一页</VBtn>
      </nav>
    </template>
  </section>
</template>

<style scoped>
.inventory header,.inventory-filters{display:flex;align-items:center;flex-wrap:wrap;gap:8px}
.inventory header{justify-content:space-between}
.inventory-meta,.inventory small{color:rgba(var(--v-theme-on-surface,38,38,47),.72)}
.inventory-filters{margin:10px 0}
.inventory-filters input{flex:1;min-width:12rem;max-width:100%}
.inventory-filters select,.inventory-filters input{border:1px solid #8888;border-radius:6px;padding:.42rem .65rem;font:inherit;color:inherit}
.inventory-table{overflow-x:auto}
.inventory table{width:100%;border-collapse:collapse;min-width:420px}
.inventory th,.inventory td{text-align:left;vertical-align:top;padding:9px 8px;border-bottom:1px solid #8884;overflow-wrap:anywhere}
.inventory th:nth-child(2){width:38%}
.inventory small{display:block}
.inventory-error{color:rgb(var(--v-theme-error,184,51,40))}
</style>
