<script setup>
import Page from './Page.vue'

defineProps({ api: Object, pluginId: { type: String, default: 'SubtitleManualUpload' } })
</script>

<template>
  <Page :api="api" :plugin-id="pluginId" :show_switch="false" :show_close="false" />
</template>
