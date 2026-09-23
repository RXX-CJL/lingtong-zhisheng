# -*- coding: utf-8 -*-
"""
快速验证 v2 版豆包解析逻辑是否能正确处理各种返回文本
直接运行：python test_parser_logic.py
"""
import re

def parse_doubao_result_v2(result_text):
    """模拟 image_recognizer.py 中改进后的解析逻辑"""
    is_confirmed = False
    confidence_adjusted = 0.3

    # 第 1 步：优先查找方括号标记
    bracket_match = re.search(r'[【\[]\s*(是|否|不确定|不確定|未违规|未发现|不存在)\s*[】\]]', result_text)
    if bracket_match:
        signal = bracket_match.group(1)
        if signal in ['是']:
            is_confirmed = True
        elif signal in ['否', '不确定', '不確定', '未违规', '未发现', '不存在']:
            is_confirmed = False
    else:
        # 第 2 步：严格关键字分析
        neg_patterns = [
            r'不存在违规', r'没有发现.*违规', r'未发现.*违规',
            r'未.*违规', r'不是违规', r'并未.*违规', r'不算违规',
            r'不构成违规', r'不属于.*违规',
            r'判断为.*否', r'结论为.*否', r'判定为.*否',
            r'：否', r':\s*否',
            r'不存在',
        ]
        found_neg = any(re.search(p, result_text) for p in neg_patterns)

        pos_patterns = [
            r'存在违规', r'发现.*违规', r'确认.*违规',
            r'属于.*违规', r'判定为.*是', r'结论为.*是',
            r'：是', r':\s*是',
        ]
        found_pos = any(re.search(p, result_text) for p in pos_patterns)

        if found_neg and not found_pos:
            is_confirmed = False
        elif found_pos and not found_neg:
            is_confirmed = True
        elif found_pos and found_neg:
            m = re.search(r'(?:是否违规|第二步|第二步.*是否|结论|判定|判断)[^。\n]*[：:]\s*([^。\n]+)', result_text)
            if m:
                is_confirmed = '是' in m.group(1) and '否' not in m.group(1)
            else:
                is_confirmed = False
        else:
            cleaned = re.sub(r'(不是|是否|但是|可是|只是|于是|还是|特别是|尤其是)', '', result_text)
            is_confirmed = bool(re.search(r'[，^|\s)]是(?![否个])', cleaned))

    # 第 3 步：提取置信度
    conf_match = re.search(r'(?:置信度|置信|评分|可能性|信心)[^0-9]{0,10}(\d{1,3})\s*(?:分|%|％)?', result_text)
    if conf_match:
        try:
            confidence_adjusted = max(0.05, min(int(conf_match.group(1)) / 100.0, 1.0))
        except ValueError:
            pass
    else:
        pct_match = re.search(r'(\d{1,3})\s*(?:%|％|分(?!$))', result_text)
        if pct_match:
            try:
                confidence_adjusted = max(0.05, min(int(pct_match.group(1)) / 100.0, 1.0))
            except ValueError:
                pass
        else:
            confidence_adjusted = 0.65 if is_confirmed else 0.20

    return is_confirmed, confidence_adjusted


# ============== 测试用例 ==============
test_cases = [
    # (描述, 返回文本, 期望 is_confirmed, 期望置信度范围)
    ("旧逻辑会误判的典型案例：'不存在违规'",
     "第一步·场景描述：图片中有一辆小型汽车在道路上正常行驶。\n第二步·是否违规：【否】\n第三步·判断依据：不存在违规行为。\n第四步·置信度评分：15分",
     False, (0.1, 0.3)),

    ("明确说【是】的案例",
     "第一步·场景描述：图片中可见一辆白色轿车正在越过道路中央黄实线驶入对向车道。\n第二步·是否违规：【是】\n第三步·判断依据：1. 车辆明显处于对向车道；2. 车辆朝向与正常行驶方向相反。\n第四步·置信度评分：85分",
     True, (0.75, 0.95)),

    ("明确说【否】的案例",
     "第一步·场景描述：图片中有一辆车停在合法的停车位内。\n第二步·是否违规：【否】\n第三步·判断依据：车辆停放在合法车位内。\n第四步·置信度评分：20分",
     False, (0.1, 0.3)),

    ("说'不确定'的案例",
     "第一步·场景描述：图片较为模糊，无法清晰判断车辆行驶方向。\n第二步·是否违规：【不确定】\n第三步·判断依据：图片信息不足。\n第四步·置信度评分：40分",
     False, (0.3, 0.5)),

    ("没有方括号但说'不是违规'的案例",
     "图片中的车辆在正常行驶，不是违规。置信度：25%",
     False, (0.1, 0.4)),

    ("没有方括号但说'存在违规'的案例",
     "经分析，该车辆存在违规行为（闯红灯）。置信度：80%",
     True, (0.7, 0.9)),

    # ---- 补充更多真实场景测试 ----
    ("旧版会误判的'不存在违规'",
     "分析结果：\n场景描述：车辆在路边合法停车位停靠\n是否违规：否\n判断依据：不存在违规停车行为\n置信度：10分",
     False, (0.05, 0.3)),

    ("'没有发现违规行为'",
     "场景描述：路口车辆有序通过\n是否违规：否\n判断依据：没有发现违规行为\n置信度评分：15分",
     False, (0.05, 0.3)),

    ("豆包中文返回：'属于逆行违规'",
     "第一步·场景描述：可见一辆电动车逆向行驶在非机动车道上。\n第二步·是否违规：【是】\n第三步·判断依据：属于逆行违规。\n第四步·置信度评分：90分",
     True, (0.8, 1.0)),

    ("含数字'1920分'等干扰项的文本",
     "第一步·场景描述：图片分辨率1920x1080，可见一辆车。\n第二步·是否违规：【否】\n第三步·判断依据：正常行驶。\n第四步·置信度评分：20分",
     False, (0.05, 0.3)),
]

print("=" * 70)
print("豆包 v2 解析逻辑测试")
print("=" * 70)

passed = 0
failed = 0
for i, (desc, text, expected_conf, conf_range) in enumerate(test_cases, 1):
    result_conf, result_score = parse_doubao_result_v2(text)
    ok_conf = (result_conf == expected_conf)
    ok_score = conf_range[0] <= result_score <= conf_range[1]
    ok = ok_conf and ok_score
    status = "✅ 通过" if ok else "❌ 失败"
    if ok:
        passed += 1
    else:
        failed += 1

    print(f"\n[{i}] {desc}")
    print(f"    期望: is_confirmed={expected_conf}, score∈[{conf_range[0]}, {conf_range[1]}]")
    print(f"    实际: is_confirmed={result_conf}, score={result_score:.2f}")
    print(f"    结果: {status}")
    if not ok:
        # 展示完整文本的前 80 字
        print(f"    文本: {text[:80]}...")

print("\n" + "=" * 70)
print(f"测试结果: {passed}/{passed + failed} 通过, {failed} 失败")
print("=" * 70)
