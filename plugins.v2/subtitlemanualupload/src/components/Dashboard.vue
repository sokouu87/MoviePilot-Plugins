<script setup>
import Page from './Page.vue'

defineProps({ api: Object, config: Object, allowRefresh: { type: Boolean, default: true } })
</script>

<template>
  <Page :api="api" :plugin-id="config?.id || 'SubtitleManualUpload'" :allow-refresh="allowRefresh"
        compact :show_switch="false" :show_close="false" />
</template>
