<script setup>
import Panel from './Panel.vue'

const props = defineProps({
  api: { type: Object, default: () => ({}) },
  pluginId: { type: String, default: 'MusicTagScraper' },
  navKey: { type: String, default: 'main' },
})
</script>

<template>
  <Panel :api="props.api" :plugin-id="props.pluginId" />
</template>
