<template>
  <el-tag :type="tagType" size="small">{{ statusName }}</el-tag>
</template>

<script setup>
import { computed } from 'vue'
import { getStatusName, getStatusColor } from '../utils/format'

const props = defineProps({
  status: {
    type: String,
    required: true
  }
})

const tagType = computed(() => getStatusColor(props.status))
const statusName = computed(() => getStatusName(props.status))
</script>