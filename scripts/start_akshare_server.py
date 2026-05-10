#!/usr/bin/env python3
"""
启动基于AKShare的数据服务器
严格遵循无模拟数据原则
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def main():
    """启动AKShare数据服务器"""
    print("🚀 启动AKShare数据服务器")
    print("=" * 60)
    print("📊 数据源: AKShare (真实A股数据)")
    print("🏢 市场: 中国A股 (沪深京)")
    print("🔧 特点: 严格无模拟数据原则")
    print("=" * 60)
    
    try:
        # 导入AKShare数据收集器
        from core.akshare_data_collector import AKShareDataCollector
        
        # 初始化收集器
        collector = AKShareDataCollector()
        
        print("📊 初始化AKShare数据库...")
        collector.setup_database()
        
        print("🔄 收集真实A股数据...")
        print("📡 数据源: 东方财富网")
        print("📈 股票类型: 沪深京A股")
        
        # 收集样本数据
        collector.collect_sample_stocks()
        
        print("🌐 启动AKShare API服务器...")
        
        # 创建应用
        app = collector.create_api_app()
        
        print("🌐 AKShare数据服务器启动成功!")
        print("📊 API地址: http://localhost:5000")
        print("🔗 健康检查: http://localhost:5000/health")
        print("📈 股票列表: http://localhost:5000/api/stocks")
        
        print("\n💡 AKShare原则:")
        print("   ✅ 绝不使用硬编码数据")
        print("   ✅ 绝不使用模拟数据")
        print("   ✅ 使用AKShare真实API")
        print("   ✅ 东方财富网数据源")
        
        print("\n🎯 API端点:")
        print("   • GET /health - 健康检查")
        print("   • GET /api/stocks - 股票列表")
        print("   • GET /api/stocks/<symbol> - 股票详情")
        
        print("\n⚠️ 重要说明:")
        print("   • 数据来源: AKShare (东方财富)")
        print("   • 数据类型: 真实A股数据")
        print("   • 更新频率: 实时/日频")
        print("   • 严格遵循无模拟数据原则")
        
        # 启动服务器
        app.run(host='0.0.0.0', port=5000, debug=False)
        
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        print("💡 请安装AKShare:")
        print("   pip install akshare")
        print("   pip install pandas")
        print("   pip install flask flask-cors")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        print("💡 请检查:")
        print("   • 网络连接是否正常")
        print("   • AKShare是否正确安装")
        print("   • 端口5000是否被占用")
        sys.exit(1)

if __name__ == "__main__":
    main()
