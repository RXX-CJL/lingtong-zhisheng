/**
 * ECharts 主题：智瞳深色（2026-10-03 由 DSH 新增）
 * 设计语言参考 Mineradio：近黑底 + 电光蓝强调 + 极细描边
 *
 * 用法：
 *   import { ztDarkTheme } from '@/utils/echarts-theme'
 *   chart.setOption(option, true)   // 或在 init 时注册主题
 */

export const ZT_THEME = {
  // 配色：与 design-tokens.css 的深色语义色一致
  color: ['#3B5BFF', '#34D399', '#FBBF24', '#F87171', '#22D3EE', '#A78BFA'],
  backgroundColor: 'transparent',
  textStyle: {
    fontFamily: 'Inter, "Microsoft YaHei", "PingFang SC", sans-serif'
  },
  title: {
    textStyle: { color: '#E8ECEF', fontWeight: 600, fontSize: 14 },
    subtextStyle: { color: '#8A9099', fontSize: 12 }
  },
  legend: {
    textStyle: { color: '#C3C9D0', fontSize: 12 },
    inactiveColor: '#5A6070'
  },
  tooltip: {
    backgroundColor: 'rgba(18,21,26,0.96)',
    borderColor: '#2E343D',
    borderWidth: 1,
    textStyle: { color: '#E8ECEF', fontSize: 12 },
    axisPointer: {
      lineStyle: { color: '#3E4652' },
      crossStyle: { color: '#3E4652' }
    }
  },
  grid: {
    borderColor: '#22272F',
    containLabel: true,
    left: 12, right: 16, top: 32, bottom: 8
  },
  categoryAxis: {
    axisLine: { lineStyle: { color: '#2E343D' } },
    axisTick: { lineStyle: { color: '#2E343D' } },
    axisLabel: { color: '#98A2B3', fontSize: 11 },
    splitLine: { show: false, lineStyle: { color: ['#1E232B'] } }
  },
  valueAxis: {
    axisLine: { show: false, lineStyle: { color: '#2E343D' } },
    axisTick: { show: false },
    axisLabel: { color: '#98A2B3', fontSize: 11 },
    splitLine: { lineStyle: { color: ['#1E232B'], type: 'dashed' } }
  },
  line: {
    symbolSize: 6,
    smooth: false,
    lineStyle: { width: 2 },
    itemStyle: { borderWidth: 0 }
  },
  areaStyle: { opacity: 0.18 },
  pie: {
    itemStyle: { borderColor: '#12151A', borderWidth: 2 },
    label: { color: '#C3C9D0', fontSize: 11 },
    labelLine: { lineStyle: { color: '#3E4652' } }
  },
  // 深色下"视觉映射/数据缩放"的样式
  visualMap: { textStyle: { color: '#C3C9D0' } },
  dataZoom: {
    textStyle: { color: '#98A2B3' },
    borderColor: '#2E343D',
    fillerColor: 'rgba(59,91,255,0.16)',
    handleStyle: { color: '#3B5BFF' },
    dataBackground: { lineStyle: { color: '#3E4652' }, areaStyle: { color: '#252B36' } }
  }
}

/** 供 ECharts init 使用：把主题对象注册到 echarts */
export function registerZtTheme(echarts) {
  if (!echarts || !echarts.registerTheme) return false
  echarts.registerTheme('zt-dark', ZT_THEME)
  return true
}

export default ZT_THEME
