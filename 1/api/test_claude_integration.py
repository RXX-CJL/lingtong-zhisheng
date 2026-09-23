import sys
sys.path.insert(0, 'e:\\output\\1\\api')

print("=== TASK-025: Claude 3.5 Sonnet 集成测试 ===\n")

print("[1] 测试 analyze_with_claude 函数导入...")
try:
    from image_recognizer import analyze_with_claude
    print("✓ analyze_with_claude 导入成功")
except Exception as e:
    print(f"✗ 导入失败: {e}")
    sys.exit(1)

print("\n[2] 测试 analyze_with_claude 函数（无 API Key）...")
test_image = 'uploads/violation_b0b9a3ad_20260609_112733.jpg'
result = analyze_with_claude(test_image, 'no_helmet')
print(f"返回结构: {list(result.keys())}")
print(f"success: {result.get('success')}")
print(f"message: {result.get('message')}")
print(f"is_violation_confirmed: {result.get('is_violation_confirmed')}")
print(f"confidence_adjusted: {result.get('confidence_adjusted')}")
print(f"risk_level: {result.get('risk_level')}")

expected_keys = ['success', 'result_text', 'is_violation_confirmed', 'confidence_adjusted', 'risk_level', 'message', 'prompt']
missing_keys = [k for k in expected_keys if k not in result]
if missing_keys:
    print(f"✗ 缺少必要字段: {missing_keys}")
else:
    print("✓ 返回结构完整")

if result.get('success') == False and '未配置' in result.get('message', ''):
    print("✓ 无 API Key 时正确返回错误信息")
else:
    print("✗ 无 API Key 处理逻辑异常")

print("\n[3] 测试 CloudCollaborator 导入 Claude...")
try:
    from cloud_collaborator import CloudCollaborator
    import inspect
    src = inspect.getsource(CloudCollaborator.consult_cloud)
    if 'analyze_with_claude' in src:
        print("✓ CloudCollaborator 已集成 Claude")
    else:
        print("✗ CloudCollaborator 未集成 Claude")
except Exception as e:
    print(f"✗ CloudCollaborator 导入失败: {e}")

print("\n[4] 测试 Config 配置...")
try:
    from config import Config
    print(f"CLAUDE_API_KEY: {'已配置' if Config.CLAUDE_API_KEY else '未配置'}")
    print(f"CLAUDE_API_URL: {Config.CLAUDE_API_URL}")
    print("✓ Config 配置加载成功")
except Exception as e:
    print(f"✗ Config 加载失败: {e}")

print("\n[5] 测试 build_ai_trace 支持 Claude 参数...")
try:
    cc = CloudCollaborator()
    sig = inspect.signature(cc.build_ai_trace)
    params = list(sig.parameters.keys())
    print(f"build_ai_trace 参数: {params}")
    if 'claude_result' in params:
        print("✓ build_ai_trace 支持 claude_result 参数")
    else:
        print("✗ build_ai_trace 不支持 claude_result 参数")
except Exception as e:
    print(f"✗ build_ai_trace 测试失败: {e}")

print("\n=== 测试完成 ===")
