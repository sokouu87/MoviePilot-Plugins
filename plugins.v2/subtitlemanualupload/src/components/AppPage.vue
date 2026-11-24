<script setup>
import { ref } from 'vue'
import Page from './Page.vue'
import MediaLibrary from './MediaLibrary.vue'

defineProps({ api: Object, pluginId: { type: String, default: 'SubtitleManualUpload' } })

const showLibrary = ref(false)
const libraryOpened = ref(false)

function openLibrary() {
  libraryOpened.value = true
  showLibrary.value = true
}
</script>

<template>
  <div class="hyrule-app">
    <nav class="views" aria-label="海拉鲁页面">
      <VBtn :variant="showLibrary ? 'text' : 'tonal'" color="primary" :aria-pressed="!showLibrary"
            @click="showLibrary = false">任务面板</VBtn>
      <VBtn :variant="showLibrary ? 'tonal' : 'text'" color="primary" :aria-pressed="showLibrary"
            @click="openLibrary">片库字幕</VBtn>
    </nav>
    <Page v-if="!showLibrary" :api="api" :plugin-id="pluginId" :show_switch="false" :show_close="false" />
    <MediaLibrary v-if="libraryOpened" v-show="showLibrary" :api="api" :plugin-id="pluginId" />
  </div>
</template>

<style scoped>
.views {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 8px 12px;
  border-bottom: 1px solid rgba(var(--v-border-color, 92, 92, 110), .16);
  background: rgb(var(--v-theme-surface, 255, 255, 255));
}
</style>
