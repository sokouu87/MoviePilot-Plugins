<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'

const props = defineProps({ api: Object, pluginId: { type: String, default: 'SubtitleManualUpload' } })
const storeKey = 'hyrule-ai.selection.' + props.pluginId
const query = ref(''), rows = ref([]), selected = ref(null), jobs = ref([]), more = ref(false)
const file = ref(null), member = ref(''), members = ref([]), role = ref('zh-Hans'), input = ref(null)
const busy = ref(false), message = ref(''), error = ref(''), index = ref(false), account = ref(''), configured = ref(true)
const glossary = ref(null), meta = ref(null)
let timer, debounce, searchSeq = 0, disposed = false
const statuses = { done: '已完成', skipped: '已跳过', queued: '排队中', running: '处理中', failed: '失败', cancelled: '已取消' }

async function api(method, endpoint, body) {
  const value = await props.api[method]('plugin/' + props.pluginId + '/' + endpoint, body)
  if (value?.success === false) throw new Error(value.message || 'MoviePilot 请求失败')
  return value?.data ?? value
}
function fail(e) {
  error.value = e?.response?.data?.detail || e?.detail || e?.message || '请求失败'
}
async function list(append = false) {
  const seq = ++searchSeq
  try {
    const res = await api('get', 'targets?q=' + encodeURIComponent(query.value) + '&offset=' + (append ? rows.value.length : 0))
    if (disposed || seq !== searchSeq) return
    rows.value = append ? rows.value.concat(res.targets) : res.targets
    more.value = res.more
    index.value = res.indexing
    if (res.error) error.value = res.error
  } catch (e) { if (seq === searchSeq) fail(e) }
}
async function loadJobs() {
  const data = await api('get', 'jobs')
  if (disposed) return
  jobs.value = data.jobs
  configured.value = data.configured
  account.value = data.model + ' · ' + data.effort
}
function clearFile() {
  file.value = null
  member.value = ''
  members.value = []
  if (input.value) input.value.value = ''
}
function pick(item) {
  selected.value = item
  try { sessionStorage.setItem(storeKey, JSON.stringify(item)) } catch {}
  clearFile()
  glossary.value = null
  meta.value = null
  message.value = error.value = ''
}
async function act(fn) {
  if (busy.value) return
  busy.value = true
  message.value = error.value = ''
  try { await fn() } catch (e) { fail(e) } finally { busy.value = false }
}
function translate() {
  return act(async () => {
    const result = await api('post', 'translate', { target: selected.value.id })
    message.value = '翻译任务 #' + result.id + ' 已进入队列'
    await loadJobs()
  })
}
function upload() {
  return act(async () => {
    if (!file.value) throw new Error('请先选择字幕')
    const data = new FormData()
    data.append('target', selected.value.id)
    data.append('role', role.value)
    data.append('member', member.value)
    data.append('file', file.value)
    const res = await api('post', 'upload', data)
    if (res.members) {
      members.value = res.members
      message.value = '请选择与当前影片或集数对应的字幕文件'
    } else {
      message.value = '已上传 ' + res.file + '（' + res.cues + ' 轴）'
      clearFile()
    }
  })
}
function editGlossary() {
  return act(async () => {
    const res = await api('get', 'glossary?target=' + encodeURIComponent(selected.value.id))
    glossary.value = JSON.stringify(res.glossary, null, 2)
  })
}
function saveGlossary() {
  return act(async () => {
    await api('post', 'glossary', { target: selected.value.id, glossary: JSON.parse(glossary.value) })
    glossary.value = null
    message.value = '已保存本剧译名表'
  })
}
function saveMeta() {
  return act(async () => {
    await api('post', 'metadata', { ...meta.value, target: selected.value.id })
    const updated = await api('get', 'target?id=' + encodeURIComponent(selected.value.id))
    pick(updated)
    await list()
    message.value = '作品资料已保存'
  })
}
watch(query, () => { clearTimeout(debounce); debounce = setTimeout(() => list(), 200) })
onMounted(async () => {
  try {
    const saved = JSON.parse(sessionStorage.getItem(storeKey) || 'null')
    if (saved?.id) {
      try { selected.value = await api('get', 'target?id=' + encodeURIComponent(saved.id)) }
      catch { sessionStorage.removeItem(storeKey) }
    }
    await Promise.all([list(), loadJobs()])
  } catch (e) { fail(e) }
  if (disposed) return
  timer = setInterval(async () => {
    try { await loadJobs(); if (index.value) await list() } catch (e) { fail(e) }
  }, 5000)
})
onBeforeUnmount(() => { disposed = true; clearInterval(timer); clearTimeout(debounce) })
</script>

<template>
  <main class="studio">
    <header><h2>海拉鲁 AI 字幕</h2><span>{{ account }}</span></header>
    <p v-if="!configured" role="status">请在插件设置中填入本机订阅线路密钥，或启用已配置的 AutoSubv3 订阅线路。</p>
    <p v-if="error" class="err" role="alert">{{ error }}</p>
    <p v-if="message" role="status">{{ message }}</p>
    <section>
      <h3>选择影片或剧集</h3>
      <div class="row"><input v-model="query" type="search" aria-label="搜索媒体" placeholder="输入片名、集数或文件名">
        <button :disabled="busy || index" @click="act(async () => { await api('post','refresh',{}); await list() })">{{ index ? '正在索引…' : '刷新媒体' }}</button></div>
      <ul class="choices"><li v-for="t in rows" :key="t.id"><button :disabled="busy" :aria-pressed="selected?.id===t.id" @click="pick(t)">
        <strong>{{ t.label }}</strong><small>{{ t.file }}</small></button></li></ul>
      <p v-if="!rows.length">{{ index ? '正在读取媒体库…' : '没有匹配的媒体' }}</p>
      <button v-if="more" @click="list(true)">更多结果</button>
    </section>
    <section v-if="selected">
      <h3>{{ selected.label }}</h3><p class="filename">{{ selected.file }}</p>
      <div class="row"><button class="primary" :disabled="busy || !configured" @click="translate">AI 翻译</button>
        <button :disabled="busy" @click="editGlossary">本剧译名表</button>
        <button :disabled="busy" @click="meta = {...selected.meta}">作品资料</button></div>
      <form v-if="meta" @submit.prevent="saveMeta"><label v-for="(label,k) in {title:'片名',year:'年份',season:'季',episode:'集'}" :key="k">{{ label }}<input v-model="meta[k]"></label>
        <button :disabled="busy">保存资料</button><button type="button" @click="meta=null">取消</button></form>
      <form v-if="glossary !== null" @submit.prevent="saveGlossary">
        <label>译名表 JSON<textarea v-model="glossary" rows="10"></textarea></label>
        <label>从文件导入<input type="file" accept=".json" @change="e => act(async () => { const f = e.target.files[0]; if (f) glossary = await f.text() })"></label>
        <button :disabled="busy">保存译名表</button><button type="button" @click="glossary=null">取消</button></form>
      <h4>SubHD 手动字幕</h4>
      <a :href="selected.search_url" target="_blank" rel="noopener noreferrer">在 SubHD 搜索 ↗</a>
      <p>到官网完成验证和下载，回到此处上传到上方影片。RAR 或 7z 请先解压。</p>
      <label>字幕文件<input ref="input" type="file" accept=".srt,.ass,.ssa,.zip" @change="e => { file=e.target.files[0]; members=[]; member='' }"></label>
      <label v-if="members.length">压缩包成员<select v-model="member"><option disabled value="">请选择对应集数</option><option v-for="name in members" :key="name">{{ name }}</option></select></label>
      <div class="row"><label>用途<select v-model="role"><option value="zh-Hans">简中成品</option><option value="zh-Hant">繁中成品</option><option value="zh-en">中英成品</option><option value="eng">英文原稿，供 AI 翻译</option></select></label>
        <button :disabled="busy || !file || (members.length && !member)" @click="upload">上传到当前影片</button></div>
    </section>
    <section><h3>翻译任务</h3><p v-if="!jobs.length">尚无翻译任务</p>
      <article v-for="job in jobs" :key="job.id"><strong>{{ job.file }}</strong>
        <p>#{{ job.id }} · {{ statuses[job.state] }} · {{ job.detail }}</p>
        <button v-if="job.state==='failed'" :disabled="busy" @click="act(async () => { await api('post','retry',{id:job.id}); await loadJobs() })">从断点重试</button>
        <details v-if="job.report.files"><summary>字幕与审校记录</summary>
          <p>{{ job.report.source }} · {{ job.report.model }} · {{ job.report.cues }} 轴</p>
          <p v-for="f in job.report.files" :key="f">{{ f }}</p>
          <p v-for="(problems,id) in job.report.warnings" :key="id">第 {{ id }} 轴 · {{ problems.join('、') }}</p>
          <p v-for="a in job.report.ambiguities" :key="a.id">第 {{ a.id }} 轴 · {{ a.options.join(' / ') }} · {{ a.reason }}</p>
          <div v-for="url in job.report.sources" :key="url"><a :href="url" target="_blank" rel="noopener noreferrer">{{ url }}</a></div>
        </details></article>
    </section>
  </main>
</template>

<style scoped>
.studio{max-width:960px;margin:auto;padding:1rem;color:inherit;font:inherit;overflow-wrap:anywhere}
.studio header,.row{display:flex;align-items:center;flex-wrap:wrap;gap:.7rem}
.studio header{justify-content:space-between}
.studio section{padding:1.1rem 0;border-top:1px solid rgba(128,128,128,.32)}
.studio h2,.studio h3,.studio h4,.studio p{margin:.45rem 0 .7rem}
.studio h4{margin-top:1.35rem}
.studio label{display:block;margin:.35rem 0}
.studio input,.studio select,.studio textarea,.studio button{border:1px solid #8888;border-radius:6px;padding:.42rem .65rem;font:inherit;color:inherit}
.studio input,.studio textarea,.studio select{max-width:100%;background:rgb(var(--v-theme-surface,255,255,255))}
.studio textarea{display:block;width:100%}
.studio button{cursor:pointer}
.studio button:disabled{opacity:.55;cursor:default}
.studio button:focus-visible,.studio a:focus-visible{outline:2px solid currentColor}
.studio .primary,.studio button[aria-pressed=true]{background:#225d52;color:white}
.studio .choices{list-style:none;display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,240px),1fr));padding:0;gap:.4rem;margin:.6rem 0;max-height:18rem;overflow:auto}
.choices button{display:block;width:100%;text-align:left;overflow-wrap:anywhere}.choices small{display:block}
.studio article{border-bottom:1px solid #8884;padding:.6rem 0}.studio a{text-decoration:underline}
.studio .err{color:rgb(var(--v-theme-error,184,51,40))}.studio input[type=search]{flex:1}
</style>
