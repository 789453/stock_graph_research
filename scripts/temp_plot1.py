#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

font_name = "WenQuanYi Micro Hei"

# 验证字体是否存在
if font_name not in (f.name for f in fm.fontManager.ttflist):
    raise Exception("❌ 未找到字体：" + font_name)

# 全局设置
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": [font_name, "DejaVu Sans"],
    "axes.unicode_minus": False,  # 负号正常显示
})

# ==================== 极简画图测试 ====================
plt.figure(figsize=(8, 4))
plt.plot([1,2,3], [2,5,3], label="测试曲线")
plt.title("中文标题测试", fontsize=14)
plt.xlabel("横轴X", fontsize=12)
plt.ylabel("纵轴Y", fontsize=12)
plt.legend()
plt.grid(True)

# 保存
plt.savefig("outputs/simple_test.png", bbox_inches="tight")
plt.close()

print(f"✅ 画图完成，使用字体：{font_name}")