#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
智瞳项目后端开发进程全面检查与完整度评估脚本

评估维度：
1. 后端架构设计实现情况
2. 核心功能模块开发进度
3. API接口开发完成度
4. 数据库设计与实现状态
5. 业务逻辑代码编写情况
6. 错误处理机制完善程度
7. 安全措施实施状况
"""

import os
import sys
import json
import ast
import re
from datetime import datetime
from typing import Dict, List, Any, Optional
import requests

# DeepSeek API配置
DEEPSEEK_API_KEY = "***REMOVED***"
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

class BackendEvaluator:
    """后端评估器"""
    
    def __init__(self, project_root: str):
        self.project_root = project_root
        self.api_dir = os.path.join(project_root, 'api')
        self.evaluation_results = {}
        self.start_time = datetime.now()
    
    def call_deepseek_api(self, prompt: str) -> str:
        """调用DeepSeek API进行智能分析"""
        try:
            headers = {
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个专业的后端开发评估专家，请对代码进行全面分析并提供专业建议。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 2000
            }
            
            response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                return f"API调用失败: {response.status_code} - {response.text}"
        
        except Exception as e:
            return f"API调用异常: {str(e)}"
    
    def evaluate_architecture(self) -> Dict[str, Any]:
        """评估后端架构设计"""
        print("正在评估后端架构设计...")
        
        architecture_score = {
            'framework': {'score': 0, 'details': '', 'suggestions': ''},
            'structure': {'score': 0, 'details': '', 'suggestions': ''},
            'separation': {'score': 0, 'details': '', 'suggestions': ''},
            'total_score': 0
        }
        
        # 检查框架选择
        main_py = os.path.join(self.api_dir, 'main.py')
        if os.path.exists(main_py):
            with open(main_py, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 检查FastAPI框架
                if 'from fastapi import' in content:
                    architecture_score['framework']['score'] = 90
                    architecture_score['framework']['details'] = '使用FastAPI框架，现代化异步Web框架，性能优秀'
                    architecture_score['framework']['suggestions'] = '建议添加中间件配置和CORS设置'
                else:
                    architecture_score['framework']['score'] = 50
                    architecture_score['framework']['details'] = '未使用现代化Web框架'
                    architecture_score['framework']['suggestions'] = '建议使用FastAPI或Flask等现代化框架'
                
                # 检查代码结构
                if 'class' in content and 'def' in content:
                    architecture_score['structure']['score'] = 75
                    architecture_score['structure']['details'] = '代码包含类和函数定义，结构基本合理'
                    architecture_score['structure']['suggestions'] = '建议将代码拆分为多个模块，如models.py, schemas.py, routers.py等'
                else:
                    architecture_score['structure']['score'] = 40
                    architecture_score['structure']['details'] = '代码结构较为简单'
                    architecture_score['structure']['suggestions'] = '建议采用模块化设计，分离关注点'
                
                # 检查关注点分离
                has_models = 'Base' in content and 'Column' in content
                has_schemas = 'BaseModel' in content
                has_routers = '@app.' in content
                
                if has_models and has_schemas and has_routers:
                    architecture_score['separation']['score'] = 80
                    architecture_score['separation']['details'] = '实现了基本的关注点分离'
                    architecture_score['separation']['suggestions'] = '建议进一步分离路由、业务逻辑和数据访问层'
                else:
                    architecture_score['separation']['score'] = 50
                    architecture_score['separation']['details'] = '关注点分离不够完善'
                    architecture_score['separation']['suggestions'] = '建议明确分离数据模型、API模式和路由处理'
        
        # 计算总分
        architecture_score['total_score'] = sum([
            architecture_score['framework']['score'],
            architecture_score['structure']['score'],
            architecture_score['separation']['score']
        ]) / 3
        
        return architecture_score
    
    def evaluate_api_development(self) -> Dict[str, Any]:
        """评估API接口开发完成度"""
        print("正在评估API接口开发完成度...")
        
        api_score = {
            'endpoints': {'score': 0, 'details': '', 'suggestions': '', 'endpoints': []},
            'documentation': {'score': 0, 'details': '', 'suggestions': ''},
            'validation': {'score': 0, 'details': '', 'suggestions': ''},
            'total_score': 0
        }
        
        main_py = os.path.join(self.api_dir, 'main.py')
        if os.path.exists(main_py):
            with open(main_py, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 检查API端点
                endpoints = re.findall(r'@app\.(get|post|put|delete)\(["\']([^"\']+)["\']', content)
                api_score['endpoints']['endpoints'] = [
                    {'method': method.upper(), 'path': path} for method, path in endpoints
                ]
                
                endpoint_count = len(endpoints)
                if endpoint_count >= 10:
                    api_score['endpoints']['score'] = 85
                    api_score['endpoints']['details'] = f'发现{endpoint_count}个API端点，覆盖主要功能'
                    api_score['endpoints']['suggestions'] = '建议添加更多边缘情况和错误处理端点'
                elif endpoint_count >= 5:
                    api_score['endpoints']['score'] = 70
                    api_score['endpoints']['details'] = f'发现{endpoint_count}个API端点，基本功能覆盖'
                    api_score['endpoints']['suggestions'] = '建议补充更多业务相关的API端点'
                else:
                    api_score['endpoints']['score'] = 40
                    api_score['endpoints']['details'] = f'仅发现{endpoint_count}个API端点，功能覆盖不足'
                    api_score['endpoints']['suggestions'] = '需要大幅增加API端点以覆盖业务需求'
                
                # 检查文档支持
                if 'FastAPI(title=' in content or 'description=' in content:
                    api_score['documentation']['score'] = 75
                    api_score['documentation']['details'] = 'FastAPI自动生成API文档'
                    api_score['documentation']['suggestions'] = '建议为每个端点添加详细的docstring和参数说明'
                else:
                    api_score['documentation']['score'] = 40
                    api_score['documentation']['details'] = '缺少API文档支持'
                    api_score['documentation']['suggestions'] = '建议集成Swagger/OpenAPI文档'
                
                # 检查数据验证
                if 'BaseModel' in content and 'Optional' in content:
                    api_score['validation']['score'] = 80
                    api_score['validation']['details'] = '使用Pydantic进行数据验证'
                    api_score['validation']['suggestions'] = '建议添加更复杂的验证规则和自定义验证器'
                else:
                    api_score['validation']['score'] = 30
                    api_score['validation']['details'] = '缺少数据验证机制'
                    api_score['validation']['suggestions'] = '建议使用Pydantic进行请求和响应数据验证'
        
        # 计算总分
        api_score['total_score'] = sum([
            api_score['endpoints']['score'],
            api_score['documentation']['score'],
            api_score['validation']['score']
        ]) / 3
        
        return api_score
    
    def evaluate_database_design(self) -> Dict[str, Any]:
        """评估数据库设计与实现"""
        print("正在评估数据库设计与实现...")
        
        db_score = {
            'schema': {'score': 0, 'details': '', 'suggestions': '', 'tables': []},
            'orm': {'score': 0, 'details': '', 'suggestions': ''},
            'migrations': {'score': 0, 'details': '', 'suggestions': ''},
            'total_score': 0
        }
        
        main_py = os.path.join(self.api_dir, 'main.py')
        if os.path.exists(main_py):
            with open(main_py, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 检查数据表设计
                tables = re.findall(r'class (\w+)\(Base\):', content)
                db_score['schema']['tables'] = tables
                
                table_count = len(tables)
                if table_count >= 4:
                    db_score['schema']['score'] = 80
                    db_score['schema']['details'] = f'设计了{table_count}个数据表，覆盖主要业务实体'
                    db_score['schema']['suggestions'] = '建议添加索引优化和表关联约束'
                elif table_count >= 2:
                    db_score['schema']['score'] = 65
                    db_score['schema']['details'] = f'设计了{table_count}个数据表，基本业务覆盖'
                    db_score['schema']['suggestions'] = '建议补充更多业务相关的数据表'
                else:
                    db_score['schema']['score'] = 30
                    db_score['schema']['details'] = f'仅设计{table_count}个数据表，业务覆盖不足'
                    db_score['schema']['suggestions'] = '需要完善数据表设计以支持业务需求'
                
                # 检查ORM使用
                if 'sqlalchemy' in content.lower() and 'sessionmaker' in content:
                    db_score['orm']['score'] = 85
                    db_score['orm']['details'] = '使用SQLAlchemy ORM，功能完善'
                    db_score['orm']['suggestions'] = '建议添加查询优化和连接池配置'
                else:
                    db_score['orm']['score'] = 40
                    db_score['orm']['details'] = '缺少ORM支持或使用原生SQL'
                    db_score['orm']['suggestions'] = '建议使用SQLAlchemy等ORM框架'
                
                # 检查数据库迁移
                if 'alembic' in content.lower() or 'migration' in content.lower():
                    db_score['migrations']['score'] = 75
                    db_score['migrations']['details'] = '支持数据库迁移'
                    db_score['migrations']['suggestions'] = '建议完善迁移脚本和版本控制'
                else:
                    db_score['migrations']['score'] = 30
                    db_score['migrations']['details'] = '缺少数据库迁移支持'
                    db_score['migrations']['suggestions'] = '建议集成Alembic进行数据库迁移管理'
        
        # 计算总分
        db_score['total_score'] = sum([
            db_score['schema']['score'],
            db_score['orm']['score'],
            db_score['migrations']['score']
        ]) / 3
        
        return db_score
    
    def evaluate_security(self) -> Dict[str, Any]:
        """评估安全措施实施状况"""
        print("正在评估安全措施实施状况...")
        
        security_score = {
            'authentication': {'score': 0, 'details': '', 'suggestions': ''},
            'authorization': {'score': 0, 'details': '', 'suggestions': ''},
            'data_protection': {'score': 0, 'details': '', 'suggestions': ''},
            'total_score': 0
        }
        
        main_py = os.path.join(self.api_dir, 'main.py')
        if os.path.exists(main_py):
            with open(main_py, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 检查身份认证
                if 'jwt' in content.lower() or 'oauth2' in content.lower():
                    security_score['authentication']['score'] = 80
                    security_score['authentication']['details'] = '实现了JWT/OAuth2身份认证'
                    security_score['authentication']['suggestions'] = '建议添加token刷新机制和双因素认证'
                else:
                    security_score['authentication']['score'] = 30
                    security_score['authentication']['details'] = '缺少身份认证机制'
                    security_score['authentication']['suggestions'] = '建议实现JWT或OAuth2认证'
                
                # 检查权限控制
                if 'role' in content.lower() and 'admin' in content.lower():
                    security_score['authorization']['score'] = 75
                    security_score['authorization']['details'] = '实现了基于角色的权限控制'
                    security_score['authorization']['suggestions'] = '建议细化权限粒度和添加权限审计'
                else:
                    security_score['authorization']['score'] = 40
                    security_score['authorization']['details'] = '权限控制不够完善'
                    security_score['authorization']['suggestions'] = '建议实现基于角色的访问控制(RBAC)'
                
                # 检查数据保护
                if 'hash' in content.lower() or 'encrypt' in content.lower():
                    security_score['data_protection']['score'] = 70
                    security_score['data_protection']['details'] = '实现了密码哈希等数据保护措施'
                    security_score['data_protection']['suggestions'] = '建议添加数据加密和敏感信息脱敏'
                else:
                    security_score['data_protection']['score'] = 30
                    security_score['data_protection']['details'] = '缺少数据保护措施'
                    security_score['data_protection']['suggestions'] = '建议实现密码哈希、数据加密等保护措施'
        
        # 计算总分
        security_score['total_score'] = sum([
            security_score['authentication']['score'],
            security_score['authorization']['score'],
            security_score['data_protection']['score']
        ]) / 3
        
        return security_score
    
    def evaluate_error_handling(self) -> Dict[str, Any]:
        """评估错误处理机制"""
        print("正在评估错误处理机制...")
        
        error_score = {
            'exception_handling': {'score': 0, 'details': '', 'suggestions': ''},
            'logging': {'score': 0, 'details': '', 'suggestions': ''},
            'user_feedback': {'score': 0, 'details': '', 'suggestions': ''},
            'total_score': 0
        }
        
        main_py = os.path.join(self.api_dir, 'main.py')
        if os.path.exists(main_py):
            with open(main_py, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 检查异常处理
                if 'try:' in content and 'except' in content:
                    error_score['exception_handling']['score'] = 70
                    error_score['exception_handling']['details'] = '实现了基本的异常处理'
                    error_score['exception_handling']['suggestions'] = '建议添加全局异常处理器和自定义异常类'
                else:
                    error_score['exception_handling']['score'] = 30
                    error_score['exception_handling']['details'] = '缺少异常处理机制'
                    error_score['exception_handling']['suggestions'] = '建议实现全面的异常处理机制'
                
                # 检查日志记录
                if 'log' in content.lower() or 'logger' in content.lower():
                    error_score['logging']['score'] = 65
                    error_score['logging']['details'] = '实现了日志记录功能'
                    error_score['logging']['suggestions'] = '建议完善日志级别和日志格式'
                else:
                    error_score['logging']['score'] = 30
                    error_score['logging']['details'] = '缺少日志记录'
                    error_score['logging']['suggestions'] = '建议集成日志记录系统'
                
                # 检查用户反馈
                if 'HTTPException' in content or 'status_code' in content:
                    error_score['user_feedback']['score'] = 75
                    error_score['user_feedback']['details'] = '提供了HTTP状态码和错误信息'
                    error_score['user_feedback']['suggestions'] = '建议统一错误响应格式和错误码'
                else:
                    error_score['user_feedback']['score'] = 40
                    error_score['user_feedback']['details'] = '错误反馈不够完善'
                    error_score['user_feedback']['suggestions'] = '建议提供清晰的错误信息和状态码'
        
        # 计算总分
        error_score['total_score'] = sum([
            error_score['exception_handling']['score'],
            error_score['logging']['score'],
            error_score['user_feedback']['score']
        ]) / 3
        
        return error_score
    
    def evaluate_business_logic(self) -> Dict[str, Any]:
        """评估业务逻辑代码编写情况"""
        print("正在评估业务逻辑代码编写情况...")
        
        business_score = {
            'core_functions': {'score': 0, 'details': '', 'suggestions': ''},
            'code_quality': {'score': 0, 'details': '', 'suggestions': ''},
            'testing': {'score': 0, 'details': '', 'suggestions': ''},
            'total_score': 0
        }
        
        main_py = os.path.join(self.api_dir, 'main.py')
        if os.path.exists(main_py):
            with open(main_py, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # 检查核心功能实现
                function_count = len(re.findall(r'def \w+\(', content))
                if function_count >= 15:
                    business_score['core_functions']['score'] = 75
                    business_score['core_functions']['details'] = f'实现了{function_count}个函数，核心功能基本覆盖'
                    business_score['core_functions']['suggestions'] = '建议补充更多业务逻辑和边缘情况处理'
                elif function_count >= 8:
                    business_score['core_functions']['score'] = 60
                    business_score['core_functions']['details'] = f'实现了{function_count}个函数，核心功能部分覆盖'
                    business_score['core_functions']['suggestions'] = '需要补充更多业务逻辑函数'
                else:
                    business_score['core_functions']['score'] = 30
                    business_score['core_functions']['details'] = f'仅实现{function_count}个函数，功能覆盖不足'
                    business_score['core_functions']['suggestions'] = '需要大幅增加业务逻辑函数'
                
                # 检查代码质量
                if 'async def' in content and 'typing' in content:
                    business_score['code_quality']['score'] = 70
                    business_score['code_quality']['details'] = '使用异步编程和类型提示，代码质量较好'
                    business_score['code_quality']['suggestions'] = '建议添加更多注释和文档字符串'
                else:
                    business_score['code_quality']['score'] = 50
                    business_score['code_quality']['details'] = '代码质量有提升空间'
                    business_score['code_quality']['suggestions'] = '建议使用异步编程、类型提示和代码注释'
                
                # 检查测试覆盖
                test_files = ['test_main.py', 'test_api.py', 'tests.py']
                has_tests = any(os.path.exists(os.path.join(self.api_dir, f)) for f in test_files)
                
                if has_tests:
                    business_score['testing']['score'] = 60
                    business_score['testing']['details'] = '存在测试文件'
                    business_score['testing']['suggestions'] = '建议提高测试覆盖率并添加集成测试'
                else:
                    business_score['testing']['score'] = 20
                    business_score['testing']['details'] = '缺少测试文件'
                    business_score['testing']['suggestions'] = '建议添加单元测试和集成测试'
        
        # 计算总分
        business_score['total_score'] = sum([
            business_score['core_functions']['score'],
            business_score['code_quality']['score'],
            business_score['testing']['score']
        ]) / 3
        
        return business_score
    
    def generate_deepseek_analysis(self, code_content: str) -> str:
        """使用DeepSeek API进行代码智能分析"""
        print("正在调用DeepSeek API进行智能分析...")
        
        prompt = f"""
请对以下后端代码进行全面分析，重点关注：
1. 代码质量和最佳实践
2. 潜在的安全漏洞
3. 性能优化建议
4. 架构改进建议
5. 错误处理和异常管理
6. 可维护性和扩展性

代码内容：
```python
{code_content[:3000]}  # 限制长度避免超出API限制
```

请提供具体的改进建议和代码示例。
"""
        
        return self.call_deepseek_api(prompt)
    
    def run_evaluation(self) -> Dict[str, Any]:
        """运行完整评估"""
        print("="*60)
        print("智瞳项目后端开发进程全面评估")
        print("="*60)
        print(f"评估时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"项目路径: {self.project_root}")
        print("="*60)
        
        # 执行各项评估
        self.evaluation_results['architecture'] = self.evaluate_architecture()
        self.evaluation_results['api_development'] = self.evaluate_api_development()
        self.evaluation_results['database_design'] = self.evaluate_database_design()
        self.evaluation_results['security'] = self.evaluate_security()
        self.evaluation_results['error_handling'] = self.evaluate_error_handling()
        self.evaluation_results['business_logic'] = self.evaluate_business_logic()
        
        # 计算总体评分
        total_scores = [
            self.evaluation_results['architecture']['total_score'],
            self.evaluation_results['api_development']['total_score'],
            self.evaluation_results['database_design']['total_score'],
            self.evaluation_results['security']['total_score'],
            self.evaluation_results['error_handling']['total_score'],
            self.evaluation_results['business_logic']['total_score']
        ]
        
        self.evaluation_results['overall_score'] = sum(total_scores) / len(total_scores)
        
        # DeepSeek智能分析
        main_py = os.path.join(self.api_dir, 'main.py')
        if os.path.exists(main_py):
            with open(main_py, 'r', encoding='utf-8') as f:
                code_content = f.read()
            self.evaluation_results['deepseek_analysis'] = self.generate_deepseek_analysis(code_content)
        
        self.evaluation_results['evaluation_time'] = datetime.now().isoformat()
        self.evaluation_results['evaluation_duration'] = str(datetime.now() - self.start_time)
        
        return self.evaluation_results
    
    def generate_report(self) -> str:
        """生成评估报告"""
        report = []
        report.append("# 智瞳项目后端开发进程全面评估报告")
        report.append(f"\n**评估时间**: {self.evaluation_results['evaluation_time']}")
        report.append(f"**评估时长**: {self.evaluation_results['evaluation_duration']}")
        report.append(f"**总体评分**: {self.evaluation_results['overall_score']:.1f}/100")
        
        # 评分等级
        if self.evaluation_results['overall_score'] >= 80:
            grade = "优秀"
        elif self.evaluation_results['overall_score'] >= 60:
            grade = "良好"
        elif self.evaluation_results['overall_score'] >= 40:
            grade = "及格"
        else:
            grade = "需要改进"
        
        report.append(f"**评级**: {grade}")
        
        # 各项评估详情
        report.append("\n## 一、后端架构设计")
        arch = self.evaluation_results['architecture']
        report.append(f"**评分**: {arch['total_score']:.1f}/100")
        report.append(f"**框架选择**: {arch['framework']['details']} (评分: {arch['framework']['score']})")
        report.append(f"**建议**: {arch['framework']['suggestions']}")
        report.append(f"**代码结构**: {arch['structure']['details']} (评分: {arch['structure']['score']})")
        report.append(f"**建议**: {arch['structure']['suggestions']}")
        report.append(f"**关注点分离**: {arch['separation']['details']} (评分: {arch['separation']['score']})")
        report.append(f"**建议**: {arch['separation']['suggestions']}")
        
        report.append("\n## 二、API接口开发")
        api = self.evaluation_results['api_development']
        report.append(f"**评分**: {api['total_score']:.1f}/100")
        report.append(f"**端点数量**: {len(api['endpoints']['endpoints'])}个 (评分: {api['endpoints']['score']})")
        report.append(f"**建议**: {api['endpoints']['suggestions']}")
        report.append(f"**API文档**: {api['documentation']['details']} (评分: {api['documentation']['score']})")
        report.append(f"**建议**: {api['documentation']['suggestions']}")
        report.append(f"**数据验证**: {api['validation']['details']} (评分: {api['validation']['score']})")
        report.append(f"**建议**: {api['validation']['suggestions']}")
        
        report.append("\n## 三、数据库设计")
        db = self.evaluation_results['database_design']
        report.append(f"**评分**: {db['total_score']:.1f}/100")
        report.append(f"**数据表数量**: {len(db['schema']['tables'])}个 (评分: {db['schema']['score']})")
        report.append(f"**数据表**: {', '.join(db['schema']['tables'])}")
        report.append(f"**建议**: {db['schema']['suggestions']}")
        report.append(f"**ORM使用**: {db['orm']['details']} (评分: {db['orm']['score']})")
        report.append(f"**建议**: {db['orm']['suggestions']}")
        report.append(f"**数据库迁移**: {db['migrations']['details']} (评分: {db['migrations']['score']})")
        report.append(f"**建议**: {db['migrations']['suggestions']}")
        
        report.append("\n## 四、安全措施")
        security = self.evaluation_results['security']
        report.append(f"**评分**: {security['total_score']:.1f}/100")
        report.append(f"**身份认证**: {security['authentication']['details']} (评分: {security['authentication']['score']})")
        report.append(f"**建议**: {security['authentication']['suggestions']}")
        report.append(f"**权限控制**: {security['authorization']['details']} (评分: {security['authorization']['score']})")
        report.append(f"**建议**: {security['authorization']['suggestions']}")
        report.append(f"**数据保护**: {security['data_protection']['details']} (评分: {security['data_protection']['score']})")
        report.append(f"**建议**: {security['data_protection']['suggestions']}")
        
        report.append("\n## 五、错误处理")
        error = self.evaluation_results['error_handling']
        report.append(f"**评分**: {error['total_score']:.1f}/100")
        report.append(f"**异常处理**: {error['exception_handling']['details']} (评分: {error['exception_handling']['score']})")
        report.append(f"**建议**: {error['exception_handling']['suggestions']}")
        report.append(f"**日志记录**: {error['logging']['details']} (评分: {error['logging']['score']})")
        report.append(f"**建议**: {error['logging']['suggestions']}")
        report.append(f"**用户反馈**: {error['user_feedback']['details']} (评分: {error['user_feedback']['score']})")
        report.append(f"**建议**: {error['user_feedback']['suggestions']}")
        
        report.append("\n## 六、业务逻辑")
        business = self.evaluation_results['business_logic']
        report.append(f"**评分**: {business['total_score']:.1f}/100")
        report.append(f"**核心功能**: {business['core_functions']['details']} (评分: {business['core_functions']['score']})")
        report.append(f"**建议**: {business['core_functions']['suggestions']}")
        report.append(f"**代码质量**: {business['code_quality']['details']} (评分: {business['code_quality']['score']})")
        report.append(f"**建议**: {business['code_quality']['suggestions']}")
        report.append(f"**测试覆盖**: {business['testing']['details']} (评分: {business['testing']['score']})")
        report.append(f"**建议**: {business['testing']['suggestions']}")
        
        # DeepSeek分析结果
        if 'deepseek_analysis' in self.evaluation_results:
            report.append("\n## 七、DeepSeek智能分析")
            report.append(self.evaluation_results['deepseek_analysis'])
        
        # 总结建议
        report.append("\n## 八、总体建议")
        
        # 找出得分最低的三个维度
        scores = [
            ('后端架构设计', self.evaluation_results['architecture']['total_score']),
            ('API接口开发', self.evaluation_results['api_development']['total_score']),
            ('数据库设计', self.evaluation_results['database_design']['total_score']),
            ('安全措施', self.evaluation_results['security']['total_score']),
            ('错误处理', self.evaluation_results['error_handling']['total_score']),
            ('业务逻辑', self.evaluation_results['business_logic']['total_score'])
        ]
        
        scores.sort(key=lambda x: x[1])
        
        report.append("\n### 优先改进项（按重要性排序）:")
        for i, (name, score) in enumerate(scores[:3], 1):
            report.append(f"{i}. **{name}** (评分: {score:.1f}/100) - 需要重点改进")
        
        report.append("\n### 改进路线图:")
        report.append("1. **短期目标** (1-2周):")
        report.append("   - 完善错误处理和日志记录")
        report.append("   - 添加API文档和参数验证")
        report.append("   - 实现数据库迁移机制")
        
        report.append("\n2. **中期目标** (1个月):")
        report.append("   - 重构代码结构，实现模块化设计")
        report.append("   - 加强安全措施，完善权限控制")
        report.append("   - 添加单元测试和集成测试")
        
        report.append("\n3. **长期目标** (2-3个月):")
        report.append("   - 性能优化和缓存机制")
        report.append("   - 微服务架构改造")
        report.append("   - 监控和告警系统")
        
        return "\n".join(report)
    
    def save_results(self, output_dir: str = None):
        """保存评估结果"""
        if output_dir is None:
            output_dir = self.api_dir
        
        # 保存JSON格式的详细结果
        json_file = os.path.join(output_dir, 'backend_evaluation_results.json')
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.evaluation_results, f, ensure_ascii=False, indent=2)
        
        # 保存Markdown格式的报告
        report_file = os.path.join(output_dir, 'backend_evaluation_report.md')
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(self.generate_report())
        
        print(f"\n评估结果已保存:")
        print(f"- 详细结果: {json_file}")
        print(f"- 评估报告: {report_file}")

def main():
    """主函数"""
    # 设置项目根目录
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 创建评估器
    evaluator = BackendEvaluator(project_root)
    
    # 运行评估
    results = evaluator.run_evaluation()
    
    # 生成并保存报告
    evaluator.save_results()
    
    # 打印总体评分
    print("\n" + "="*60)
    print("评估完成！")
    print(f"总体评分: {results['overall_score']:.1f}/100")
    print("="*60)
    
    return results

if __name__ == '__main__':
    main()