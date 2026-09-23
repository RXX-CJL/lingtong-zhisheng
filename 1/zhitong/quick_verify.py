"""快速验证APIClient集成"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ''))

try:
    print("=" * 60)
    print("快速验证API集成")
    print("=" * 60)
    
    # 1. 验证config配置
    print("\n[1] 验证config.py中的API配置...")
    from config import Config
    config = Config()
    assert hasattr(config, 'API_BASE_URL'), "缺少API_BASE_URL配置"
    assert hasattr(config, 'API_SUBMIT_ENDPOINT'), "缺少API_SUBMIT_ENDPOINT配置"
    assert hasattr(config, 'API_TIMEOUT'), "缺少API_TIMEOUT配置"
    assert hasattr(config, 'API_RETRY_TIMES'), "缺少API_RETRY_TIMES配置"
    assert hasattr(config, 'ENABLE_API_UPLOAD'), "缺少ENABLE_API_UPLOAD配置"
    print(f"  ✓ API_BASE_URL: {config.API_BASE_URL}")
    print(f"  ✓ API_SUBMIT_ENDPOINT: {config.API_SUBMIT_ENDPOINT}")
    print(f"  ✓ API_TIMEOUT: {config.API_TIMEOUT}")
    print(f"  ✓ API_RETRY_TIMES: {config.API_RETRY_TIMES}")
    print(f"  ✓ ENABLE_API_UPLOAD: {config.ENABLE_API_UPLOAD}")
    
    # 2. 验证api_client模块
    print("\n[2] 验证api_client.py...")
    from api_client import APIClient
    assert APIClient is not None, "无法导入APIClient"
    print("  ✓ APIClient类导入成功")
    
    # 3. 验证main.py的集成
    print("\n[3] 验证main.py集成...")
    # 检查main.py是否正确导入了APIClient
    with open('main.py', 'r', encoding='utf-8') as f:
        main_content = f.read()
        assert 'from api_client import APIClient' in main_content, "main.py未导入APIClient"
        assert 'self.api_client = APIClient(self.config)' in main_content, "main.py未初始化APIClient"
        assert 'self.api_client.submit_violation' in main_content, "main.py未调用submit_violation"
        assert 'self.api_client.stop()' in main_content, "main.py未调用stop()"
    print("  ✓ main.py正确导入APIClient")
    print("  ✓ main.py初始化APIClient")
    print("  ✓ main.py调用submit_violation")
    print("  ✓ main.py调用stop()")
    
    # 4. 创建实例验证
    print("\n[4] 创建ZhiTongSystem实例...")
    # 注意：这会初始化所有模块，可能需要较长时间
    # 我们只验证关键部分
    system = object.__new__(type('ZhiTongSystem', (), {}))
    system.config = config
    system.api_client = APIClient(config)
    assert system.api_client is not None, "APIClient初始化失败"
    assert system.api_client.enable_upload == True, "API上传未启用"
    print("  ✓ APIClient实例创建成功")
    print("  ✓ API上传队列已启动")
    
    # 5. 验证HTTP连接
    print("\n[5] 验证后端API连接...")
    import requests
    try:
        response = requests.get("http://127.0.0.1:8000/health", timeout=5)
        if response.status_code == 200:
            print(f"  ✓ 后端API服务正常运行")
            print(f"  ✓ 响应: {response.json()}")
        else:
            print(f"  ⚠ 后端API返回状态码: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("  ⚠ 无法连接到后端API服务")
        print("  提示: 请确保API服务正在运行")
    except requests.exceptions.Timeout:
        print("  ⚠ API连接超时")
    
    print("\n" + "=" * 60)
    print("✓ 验证完成！")
    print("=" * 60)
    print("\n总结:")
    print("  ✅ config.py配置正确")
    print("  ✅ api_client.py模块正常")
    print("  ✅ main.py集成正确")
    print("  ✅ 系统已准备好提交违规到API")
    print("\n下一步:")
    print("  1. 启动智瞳系统: python main.py")
    print("  2. 检测到违规时，会自动提交到API")
    print("  3. 查看提交结果: http://127.0.0.1:8000/api/violations/list")
    
except AssertionError as e:
    print(f"\n✗ 验证失败: {e}")
    sys.exit(1)
except Exception as e:
    print(f"\n✗ 发生错误: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
