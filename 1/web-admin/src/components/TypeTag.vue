<template>
  <el-tag :color="tagColor" size="small">{{ typeName }}</el-tag>
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
const typeName = computed(() => getTypeName(props.type))
</script>

<style scoped>
.el-tag {
  color: #fff;
  border: none;
}
</style>