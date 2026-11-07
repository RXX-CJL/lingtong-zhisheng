/**
 * ECharts 主题：智瞳亮色 zt-light（2026-10-23 由 DSH 重写）
 *
 * 变更原因（决策 3 选 A）：
 *   原文件是深色主题 zt-dark（backgroundColor 近黑 #12151A），
 *   与 src/styles/design-tokens.css 的亮色体系（--zt-bg:#F6F7F9 / --zt-surface:#FFFFFF）冲突；
 *   且 Dashboard.vue 三处 echarts.init 从未传主题参数 —— 该文件历史上**从未生效**。
 *
 * 用法：
 *   import { registerZtTheme } from '@/utils/echarts-theme'
 *   registerZtTheme(echarts)                        // 注册一次
 *   echarts.init(el, ZT_THEME_NAME)                 // 之后凡是图表都传第二个参数
 *
 * 颜色基准全部取自 design-tokens.css，改主题前先改令牌。
 */

export const ZT_THEME_NAME = 'zt-light'

export const ZT_THEME = {
  // 分类色：与 design-tokens.css 语义色一致，暖=危险 / 冷=静态
  color: ['#D14343', '#ED7D31', '#F2C14E', '#9B5DE5', '#2E9E8F', '#5B8DB8', '#98A2B3', '#4C7A9E'],
  backgroundColor: 'transparent',
  textStyle: {
    fontFamily: 'Inter, -apple-system, "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif'
  },
  title: {
    textStyle: { color: '#101828', fontWeight: 600, fontSize: 14 },
    subtextStyle: { color: '#98A2B3', fontSize: 12 }
  },
  legend: {
    textStyle: { color: '#475467', fontSize: 12 },
    inactiveColor: '#C0C4CC',
    itemWidth: 10,
    itemHeight: 10,
    itemGap: 12
  },
  tooltip: {
    backgroundColor: 'rgba(255,255,255,0.98)',
    borderColor: '#E4E7EC',
    borderWidth: 1,
    padding: [8, 12],
    textStyle: { color: '#101828', fontSize: 12 },
    extraCssText: 'box-shadow: 0 4px 12px rgba(16,24,40,0.08); border-radius: 8px;',
    axisPointer: {
      lineStyle: { color: '#E4E7EC' },
      crossStyle: { color: '#E4E7EC' },
      shadowStyle: { color: 'rgba(29,78,216,0.05)' }
    }
  },
  grid: {
    borderColor: '#E4E7EC',
    containLabel: true,
    left: 12,
    right: 16,
    top: 32,
    bottom: 8
  },
  categoryAxis: {
    axisLine: { lineStyle: { color: '#E4E7EC' } },
    axisTick: { lineStyle: { color: '#E4E7EC' } },
    axisLabel: { color: '#606266', fontSize: 12 },
    splitLine: { show: false }
  },
  valueAxis: {
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { color: '#98A2B3', fontSize: 11 },
    splitLine: { lineStyle: { color: ['#F0F2F5'], type: 'dashed' } }
  },
  line: {
    symbolSize: 6,
    smooth: false,
    lineStyle: { width: 2 },
    itemStyle: { borderWidth: 0 }
  },
  areaStyle: { opacity: 0.18 },
  bar: {
    // 条形图圆角在 Dashboard 里按方向单独设置，这里只放通用
    itemStyle: { borderRadius: 3 }
  },
  pie: {
    itemStyle: { borderColor: '#FFFFFF', borderWidth: 2 },
    label: { color: '#475467', fontSize: 12 },
    labelLine: { lineStyle: { color: '#CDD3DC' } }
  },
  visualMap: { textStyle: { color: '#475467' } },
  dataZoom: {
    textStyle: { color: '#98A2B3' },
    borderColor: '#E4E7EC',
    fillerColor: 'rgba(29,78,216,0.10)',
    handleStyle: { color: '#1D4ED8' },
    dataBackground: { lineStyle: { color: '#E4E7EC' }, areaStyle: { color: '#F6F7F9' } }
  }
}

/** 把亮色主题注册到 echarts（幂等，重复调用安全） */
export function registerZtTheme(echarts) {
  if (!echarts || !echarts.registerTheme) return false
  echarts.registerTheme(ZT_THEME_NAME, ZT_THEME)
  return true
}

export default ZT_THEME
