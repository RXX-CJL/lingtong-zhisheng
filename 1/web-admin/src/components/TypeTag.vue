<template>
  <!-- 文字色随底色亮度自适应：2026-10-23 由 DSH 修（原先硬编码白字，
       在 #F2C14E 抢黄灯等浅底上对比度仅约 1.9:1，读不清） -->
  <el-tag
    size="small"
    class="zt-type-tag"
    :style="{ background: tagColor, '--el-tag-text-color': textColor }"
  >{{ typeName }}</el-tag>
</template>

<script setup>
import { computed } from 'vue'
import { getTypeName, getTypeColor } from '../utils/format'

const props = defineProps({
  type: {
    type: String,
    required: true
  }
})

const tagColor = computed(() => getTypeColor(props.type))

// 按底色相对亮度自动选深/浅字，保证对比度（浅底配深字，深底配白字）
const textColor = computed(() => (isLightColor(tagColor.value) ? '#1F2933' : '#FFFFFF'))

function isLightColor(hex) {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex || '')
  if (!m) return false
  const n = parseInt(m[1], 16)
  const r = (n >> 16) & 255
  const g = (n >> 8) & 255
  const b = n & 255
  // W3C 相对亮度公式（sRGB 线性化后加权）
  const lin = (c) => {
    const s = c / 255
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4)
  }
  const L = 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)
  return L > 0.5
}

const typeName = computed(() => getTypeName(props.type))
</script>

<style scoped>
.zt-type-tag {
  border: none;
  font-weight: 500;
}
</style>
