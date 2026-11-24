<script setup>
import { onMounted, ref } from 'vue'

const props = defineProps({ row: Object, call: Function })
const emit = defineEmits(['close', 'changed'])
const target = ref(null), busy = ref(false), message = ref(''), error = ref('')
const file = ref(null), member = ref(''), members = ref([]), role = ref('zh-Hans')
const fileInput = ref(null), glossary = ref(null), metadata = ref(null)
const roles = { 'zh-Hans': '简中成品', 'zh-Hant': '繁中成品', 'zh-en': '中英成品', eng: '英文原稿，供 AI 翻译' }

async function act(fn) {
  if (busy.value) return
  busy.value = true
  error.value = message.value = ''
  try {
    await fn()
  } catch (reason) {
    error.value = reason?.response?.data?.detail || reason?.message || '操作失败'
  } finally {
    busy.value = false
  }
}

onMounted(() => act(async () => {
  target.value = await props.call('post', 'library_target', { id: props.row.id })
}))

function selectFile(event) {
  file.value = event.target.files[0] || null
  members.value = []
  member.value = ''
}

function upload() {
  return act(async () => {
    const form = new FormData()
    form.append('target', target.value.target)
    form.append('role', role.value)
    form.append('member', member.value)
    form.append('file', file.value)
    const res = await props.call('post', 'upload', form)
    if (res.members) {
      members.value = res.members
      message.value = '请选择和当前片源对应的字幕'
    } else {
      message.value = `已上传 ${res.file}（${res.cues} 轴）`
      file.value = null
      members.value = []
      member.value = ''
      if (fileInput.value) fileInput.value.value = ''
      emit('changed')
    }
  })
}

function editMeta() {
  return act(async () => {
    const res = await props.call('get', 'target?id=' + encodeURIComponent(target.value.target))
    metadata.value = { ...res.meta }
  })
}

function saveMeta() {
  return act(async () => {
    await props.call('post', 'metadata', { ...metadata.value, target: target.value.target })
    metadata.value = null
    message.value = '作品资料已保存'
    emit('changed')
  })
}

function editGlossary() {
  return act(async () => {
    const res = await props.call('get', 'glossary?target=' + encodeURIComponent(target.value.target))
    glossary.value = JSON.stringify(res.glossary, null, 2)
  })
}

function saveGlossary() {
  return act(async () => {
    await props.call('post', 'glossary', { glossary: JSON.parse(glossary.value), target: target.value.target })
    glossary.value = null
    message.value = '译名表已保存'
  })
}
</script>

<template>
  <VDialog :model-value="true" max-width="650" :persistent="busy" aria-labelledby="hyrule-upload"
           @update:model-value="open => { if (!open) emit('close') }">
    <VCard>
      <VCardTitle id="hyrule-upload">上传字幕</VCardTitle>
      <VCardText class="upload-body">
        <strong>{{ row.title }}</strong>
        <p v-if="busy && !target" role="status">正在核对影片目录…</p>
        <p v-if="error" class="error-text" role="alert">{{ error }}</p>
        <p v-if="message" role="status">{{ message }}</p>
        <p v-if="row.directory"><span>影片目录</span><code>{{ target?.directory || row.directory }}</code></p>
        <a :href="row.search_url" target="_blank" rel="noopener noreferrer">前往 SubHD ↗</a>
        <template v-if="target">
          <p v-if="row.original">
            <span>{{ target.folder ? '原盘目录内的外挂，可在播放器手动加载' : '字幕保存到主片旁' }}</span>
            <code>{{ target.destination }}<template v-if="!target.folder"> · {{ target.file }}</template></code>
          </p>
          <form class="upload-form" @submit.prevent="upload">
            <label>字幕文件<input ref="fileInput" type="file" accept=".srt,.ass,.ssa,.zip" @change="selectFile"></label>
            <label v-if="members.length">压缩包成员
              <select v-model="member"><option disabled value="">选择当前片源的字幕</option>
                <option v-for="name in members" :key="name">{{ name }}</option>
              </select>
            </label>
            <label>用途<select v-model="role">
              <option v-for="(label, value) in roles" :key="value" :value="value" :disabled="row.original && value === 'eng'">{{ label }}</option>
            </select></label>
            <VBtn type="submit" color="primary" :disabled="busy || !file || (members.length && !member)">上传字幕</VBtn>
          </form>
          <div v-if="!row.original" class="upload-tools">
            <VBtn size="small" variant="text" :disabled="busy" @click="editMeta">作品资料</VBtn>
            <VBtn size="small" variant="text" :disabled="busy" @click="editGlossary">本剧译名表</VBtn>
          </div>
          <form v-if="metadata" class="upload-form" @submit.prevent="saveMeta">
            <label v-for="(label,key) in {title:'片名',year:'年份',season:'季',episode:'集'}" :key="key">{{ label }}<input v-model="metadata[key]"></label>
            <VBtn type="submit" size="small" :disabled="busy">保存资料</VBtn>
          </form>
          <form v-if="glossary !== null" class="upload-form" @submit.prevent="saveGlossary">
            <label>译名表 JSON<textarea v-model="glossary" rows="8"></textarea></label>
            <label>从文件导入<input type="file" accept=".json" @change="e => act(async () => {
              if (e.target.files[0]) glossary = await e.target.files[0].text()
            })"></label>
            <VBtn type="submit" size="small" :disabled="busy">保存译名表</VBtn>
          </form>
        </template>
      </VCardText>
      <VCardActions><VSpacer /><VBtn variant="text" :disabled="busy" @click="emit('close')">关闭</VBtn></VCardActions>
    </VCard>
  </VDialog>
</template>

<style scoped>
.upload-body{overflow-wrap:anywhere}
.upload-body p{margin:.6rem 0}
.upload-body code,.upload-form label,.upload-form input,.upload-form textarea,.upload-form select{display:block}
.upload-body code{white-space:normal;user-select:text}
.upload-body a,.error-text{color:rgb(var(--v-theme-primary,128,78,238))}
.upload-body .error-text{color:rgb(var(--v-theme-error,209,47,58))}
.upload-form,.upload-tools{display:flex;align-items:flex-end;flex-wrap:wrap;gap:10px;margin-top:12px}
.upload-form input,.upload-form textarea,.upload-form select{max-width:100%;border:1px solid #8888;border-radius:6px;padding:.4rem .6rem;font:inherit;color:inherit}
.upload-form textarea{min-width:min(20rem,100%)}
</style>
