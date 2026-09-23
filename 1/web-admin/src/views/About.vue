<template>
  <div class="about">
    <el-card shadow="hover">
      <template #header>
        <div class="header">
          <el-icon size="32" color="#1890ff"><VideoCamera /></el-icon>
          <h1>智瞳灵声 · 智慧交管违规检测系统</h1>
        </div>
      </template>

      <div class="content">
        <p class="description">
          智瞳灵声是一款基于深度学习的智慧交通违规检测系统，采用 YOLOv8 目标检测算法
          结合 DeepSORT 多目标跟踪技术，实现对交通违规行为的实时检测与智能分析。
        </p>

        <h2>技术栈</h2>
        <div class="tech-list">
          <el-tag v-for="tech in techs" :key="tech" type="primary">{{ tech }}</el-tag>
        </div>

        <h2>团队成员</h2>
        <el-row :gutter="20" class="team-row">
          <el-col :span="6" v-for="member in members" :key="member.name">
            <el-card shadow="hover" class="member-card">
              <div class="member-avatar">
                <el-icon size="40"><User /></el-icon>
              </div>
              <div class="member-name">{{ member.name }}</div>
              <div class="member-role">{{ member.role }}</div>
            </el-card>
          </el-col>
        </el-row>

        <h2>系统架构</h2>
        <el-card shadow="hover" class="architecture-card">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="本地检测端">
              YOLOv8n + DeepSORT + TensorRT 加速，45ms/帧推理速度
            </el-descriptions-item>
            <el-descriptions-item label="云端管理平台">
              Spring Boot + FastAPI 双架构，支持 Doubao 大模型分析
            </el-descriptions-item>
            <el-descriptions-item label="移动端">
              微信小程序，支持实时举报与状态查询
            </el-descriptions-item>
            <el-descriptions-item label="嵌入式">
              适配嘉楠 K230 开发板
            </el-descriptions-item>
          </el-descriptions>
        </el-card>

        <h2>功能特性</h2>
        <ul class="feature-list">
          <li>支持 6 种违规类型检测：闯红灯、未戴头盔、逆行、违规停车、压线行驶、超速</li>
          <li>实时目标跟踪与速度检测</li>
          <li>边缘计算 + 云端协同分析</li>
          <li>自动化证据链生成与存储</li>
          <li>多端实时数据同步</li>
        </ul>
      </div>
    </el-card>
  </div>
</template>

<script setup>
const techs = [
  'YOLOv8',
  'DeepSORT',
  'TensorRT',
  'Vue 3',
  'FastAPI',
  'Spring Boot',
  'Element Plus',
  'ECharts',
  'MySQL',
  'Redis'
]

const members = [
  { name: '陈俊龙', role: '项目负责人' },
  { name: '母书祯', role: '算法工程师' },
  { name: '苗博文', role: '前端开发' },
  { name: '余林峰', role: '后端开发' },
  { name: '王泽轩', role: '嵌入式开发' }
]
</script>

<style scoped lang="scss">
.about {
  .header {
    display: flex;
    align-items: center;
    gap: 16px;

    h1 {
      margin: 0;
      font-size: 24px;
      color: #333;
    }
  }

  .content {
    h2 {
      margin: 30px 0 20px;
      font-size: 18px;
      color: #333;
      padding-left: 12px;
      border-left: 4px solid #1890ff;
    }

    .description {
      font-size: 15px;
      line-height: 1.8;
      color: #666;
    }

    .tech-list {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;

      .el-tag {
        padding: 8px 16px;
        font-size: 14px;
      }
    }

    .team-row {
      margin-top: 16px;
    }

    .member-card {
      text-align: center;
      padding: 20px 0;

      .member-avatar {
        width: 80px;
        height: 80px;
        border-radius: 50%;
        background: #f0f7ff;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto 16px;
        color: #1890ff;
      }

      .member-name {
        font-size: 16px;
        font-weight: 600;
        color: #333;
        margin-bottom: 8px;
      }

      .member-role {
        font-size: 13px;
        color: #999;
      }
    }

    .architecture-card {
      margin-top: 16px;
    }

    .feature-list {
      margin: 0;
      padding-left: 20px;
      color: #666;
      line-height: 2;

      li {
        margin-bottom: 8px;
      }
    }
  }
}
</style>