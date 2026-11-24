<script setup>
import AppPage from './AppPage.vue'
defineProps({ api: Object, pluginId: String, show_switch: { type: Boolean, default: true } })
defineEmits(['switch','close'])
</script>
<template>
  <div>
    <VToolbar density="compact"><VSpacer/><VBtn v-if="show_switch" aria-label="插件设置" icon="mdi-cog-outline" @click="$emit('switch')"/><VBtn aria-label="关闭" icon="mdi-close" @click="$emit('close')"/></VToolbar>
    <AppPage :api="api" :plugin-id="pluginId"/>
  </div>
</template>
