<template>
  <el-progress
    :percentage="percentage"
    :color="progressColor"
    :stroke-width="8"
    :show-text="true"
  />
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  value: {
    type: Number,
    default: 0
  }
})

const percentage = computed(() => {
  if (props.value === null || props.value === undefined) return 0
  return Math.round(props.value * 100)
})

const progressColor = computed(() => {
  const p = percentage.value
  if (p >= 90) return '#52c41a'
  if (p >= 70) return '#1890ff'
  if (p >= 50) return '#faad14'
  return '#ff4d4f'
})
</script>