/**
 * 启动前清理脚本
 * 自动清理 Vite 生成的临时文件，避免锁定问题
 */

const fs = require('fs');
const path = require('path');

function cleanViteTempFiles() {
  const currentDir = __dirname;
  const files = fs.readdirSync(currentDir);
  
  let cleanedCount = 0;
  
  files.forEach(file => {
    // 匹配 vite.config.js.timestamp-xxx.mjs 格式的临时文件
    if (file.startsWith('vite.config.js.timestamp')) {
      const filePath = path.join(currentDir, file);
      try {
        fs.unlinkSync(filePath);
        console.log(`✓ 已清理临时文件: ${file}`);
        cleanedCount++;
      } catch (error) {
        console.log(`✗ 清理失败: ${file} - ${error.message}`);
      }
    }
  });
  
  if (cleanedCount > 0) {
    console.log(`总计清理了 ${cleanedCount} 个临时文件`);
  }
}

// 执行清理
cleanViteTempFiles();
