<script setup>
import Panel from './Panel.vue'

const props = defineProps({
  api: { type: Object, default: () => ({}) },
  pluginId: { type: String, default: 'MusicTagScraper' },
  navKey: { type: String, default: 'main' },
})

const emit = defineEmits(['close', 'switch'])
</script>

<template>
  <div class="mts-page-wrapper">
    <VToolbar density="comfortable" class="mts-toolbar">
      <div class="text-h6 ms-3">音乐标签刮削</div>
      <VSpacer />
      <VTooltip text="插件设置" location="bottom">
        <template #activator="{ props: tooltipProps }">
          <VBtn
            v-bind="tooltipProps"
            icon="mdi-cog-outline"
            variant="text"
            aria-label="插件设置"
            @click="emit('switch')"
          />
        </template>
      </VTooltip>
      <VBtn icon="mdi-close" variant="text" aria-label="关闭" @click="emit('close')" />
    </VToolbar>
    <VDivider />
    <Panel :api="props.api" :plugin-id="props.pluginId" compact />
  </div>
</template>

<style scoped>
.mts-toolbar {
  position: sticky;
  top: 0;
  z-index: 10;
  background: rgb(var(--v-theme-surface));
}
</style>
