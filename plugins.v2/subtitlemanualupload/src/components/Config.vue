<script setup>
import { ref, watch } from 'vue'
const props=defineProps({initialConfig:{type:Object,default:()=>({})},saving:Boolean})
const emit=defineEmits(['save','close'])
const models=['gpt-6.2-astra', 'gpt-6.2-sol']
const data=ref({})
watch(()=>props.initialConfig, (value)=>{
  const v=value || {}
  data.value={...v, enabled:v.enabled ?? false, auto_translate:v.auto_translate ?? v.auto_search_on_transfer ?? true,
    show_sidebar_nav:v.show_sidebar_nav ?? true, model:v.model || 'gpt-6.2-astra', effort:v.effort || 'high',
    bridge_key:v.bridge_key || '', whisper:v.whisper || '', banned:v.banned ?? '破防、内卷、绝绝子、老铁、诸葛亮、塞翁失马、三顾茅庐',
    manual_dirs:v.manual_dirs ?? (v.manual_strm_enabled ? [].concat(v.manual_strm_paths || []).join('\n') : ''),
    emby_directory_map:v.emby_directory_map || ''}
},{immediate:true})
</script>
<template>
 <form class="options" @submit.prevent="emit('save', {...data, auto_search_on_transfer: data.auto_translate})">
  <h3>海拉鲁 AI 字幕设置</h3>
  <label><input v-model="data.enabled" type="checkbox"> 启用插件</label>
  <label><input v-model="data.auto_translate" type="checkbox"> 入库后自动翻译</label>
  <label><input v-model="data.show_sidebar_nav" type="checkbox"> 在侧栏显示</label>
  <label>订阅模型
   <select v-model="data.model" required>
    <option v-for="model in models" :key="model" :value="model">{{ model }}</option>
    <option v-if="initialConfig?.model && !models.includes(initialConfig.model)" :value="initialConfig.model">{{ initialConfig.model }}（当前配置）</option>
   </select>
  </label>
  <label>推理档位<select v-model="data.effort"><option>medium</option><option>high</option><option>xhigh</option></select></label>
  <label>本机订阅服务密钥<input v-model.trim="data.bridge_key" type="password" autocomplete="new-password" placeholder="已配置旧订阅线路时可留空"></label>
  <label>Whisper 模型目录<input v-model.trim="data.whisper" placeholder="留空使用 AutoSubv3 已缓存的模型"></label>
  <label>额外 STRM 目录，每行一条<textarea v-model="data.manual_dirs" rows="2"></textarea></label>
  <label>Emby 目录映射，每行一条<textarea v-model="data.emby_directory_map" rows="2" placeholder="/Emby目录=/MoviePilot目录"></textarea></label>
  <label>翻译禁用词，以顿号或换行分隔<textarea v-model="data.banned" rows="2"></textarea></label>
  <VBtn type="submit" color="primary" :loading="saving">保存</VBtn> <VBtn :disabled="saving" @click="emit('close')">关闭</VBtn>
 </form>
</template>
<style scoped>
.options{padding:1rem;max-width:42rem;margin:auto}.options label{display:block;margin:.85rem 0}
.options input:not([type=checkbox]),.options textarea,.options select{display:block;width:100%;border:1px solid #8888;border-radius:5px;padding:.38rem .55rem;color:inherit;background:rgb(var(--v-theme-surface,255,255,255))}
.options select{appearance:auto}
</style>
