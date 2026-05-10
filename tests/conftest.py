#!/usr/bin/env python3
"""
综合测试脚本 - 验证所有改进功能
"""

import requests
import json
import time
import asyncio
import websockets
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ComprehensiveTest:
    """综合测试类"""
    
    def __init__(self):
        self.api_base_url = "http://localhost:5000/api"
        self.websocket_url = "ws://localhost:8768"
        self.test_results = {
            'technical_indicators': False,
            'websocket_server': False,
            'lstm_predictions': False,
            'api_endpoints': False,
            'data_integrity': False
        }
        
    def test_api_health(self):
        """测试API健康状态"""
        try:
            response = requests.get(f"{self.api_base_url}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                logger.info("✅ API健康检查通过")
                return True
            else:
                logger.error(f"❌ API健康检查失败: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ API健康检查异常: {e}")
            return False
    
    def test_technical_indicators(self):
        """测试技术指标功能"""
        try:
            # 测试单个股票技术指标
            response = requests.get(f"{self.api_base_url}/technical-indicators/000001", timeout=30)
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('data'):
                    indicators = data['data']
                    logger.info(f"✅ 技术指标API测试通过 - 获取到 {len(indicators)} 个指标")
                    self.test_results['technical_indicators'] = True
                    return True
                else:
                    logger.error(f"❌ 技术指标API返回失败: {data.get('error')}")
                    return False
            else:
                logger.error(f"❌ 技术指标API请求失败: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 技术指标测试异常: {e}")
            return False
    
    def test_lstm_predictions(self):
        """测试LSTM预测功能"""
        try:
            # 测试单个股票LSTM预测
            response = requests.get(f"{self.api_base_url}/lstm-predictions/000001", timeout=60)
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('data'):
                    predictions = data['data']['predictions']
                    logger.info(f"✅ LSTM预测API测试通过 - 获取到 {len(predictions)} 个预测")
                    self.test_results['lstm_predictions'] = True
                    return True
                else:
                    logger.error(f"❌ LSTM预测API返回失败: {data.get('error')}")
                    return False
            else:
                logger.error(f"❌ LSTM预测API请求失败: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ LSTM预测测试异常: {e}")
            return False
    
    async def test_websocket_connection(self):
        """测试WebSocket连接"""
        try:
            async with websockets.connect(self.websocket_url) as websocket:
                logger.info("✅ WebSocket连接成功")
                
                # 测试心跳
                await websocket.send(json.dumps({"type": "ping"}))
                response = await websocket.recv()
                data = json.loads(response)
                
                if data.get('type') == 'pong':
                    logger.info("✅ WebSocket心跳测试通过")
                    
                    # 测试订阅
                    await websocket.send(json.dumps({"type": "subscribe", "symbol": "000001"}))
                    response = await websocket.recv()
                    data = json.loads(response)
                    
                    if data.get('type') == 'subscription_confirmed':
                        logger.info("✅ WebSocket订阅测试通过")
                        self.test_results['websocket_server'] = True
                        return True
                    else:
                        logger.error(f"❌ WebSocket订阅失败: {data}")
                        return False
                else:
                    logger.error(f"❌ WebSocket心跳失败: {data}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ WebSocket测试异常: {e}")
            return False
    
    def test_api_endpoints(self):
        """测试所有API端点"""
        endpoints = [
            "/health",
            "/stocks",
            "/technical-indicators/000001",
            "/technical-indicators",
            "/lstm-predictions/000001",
            "/lstm-predictions",
            "/predictions/000001",
            "/dashboard"
        ]
        
        success_count = 0
        
        for endpoint in endpoints:
            try:
                response = requests.get(f"{self.api_base_url}{endpoint}", timeout=30)
                if response.status_code == 200:
                    success_count += 1
                    logger.info(f"✅ {endpoint} - 正常")
                else:
                    logger.warning(f"⚠️ {endpoint} - 状态码: {response.status_code}")
            except Exception as e:
                logger.error(f"❌ {endpoint} - 异常: {e}")
        
        success_rate = success_count / len(endpoints)
        logger.info(f"📊 API端点测试通过率: {success_rate:.1%} ({success_count}/{len(endpoints)})")
        
        if success_rate >= 0.8:
            self.test_results['api_endpoints'] = True
            return True
        else:
            return False
    
    def test_data_integrity(self):
        """测试数据完整性"""
        try:
            # 获取股票列表
            response = requests.get(f"{self.api_base_url}/stocks", timeout=30)
            if response.status_code != 200:
                logger.error("❌ 获取股票列表失败")
                return False
            
            stocks = response.json().get('data', [])
            if not stocks:
                logger.error("❌ 股票列表为空")
                return False
            
            # 测试几只股票的数据完整性
            test_symbols = ['000001', '000002', '600519']
            data_complete = 0
            
            for symbol in test_symbols:
                try:
                    # 检查基础数据
                    response = requests.get(f"{self.api_base_url}/stocks/{symbol}", timeout=30)
                    if response.status_code == 200:
                        stock_data = response.json().get('data', {})
                        if stock_data.get('current_price'):
                            data_complete += 1
                    
                    # 检查技术指标
                    response = requests.get(f"{self.api_base_url}/technical-indicators/{symbol}", timeout=30)
                    if response.status_code == 200:
                        indicators = response.json().get('data', [])
                        if len(indicators) > 0:
                            data_complete += 0.3
                    
                    # 检查预测数据
                    response = requests.get(f"{self.api_base_url}/lstm-predictions/{symbol}", timeout=60)
                    if response.status_code == 200:
                        predictions = response.json().get('data', {}).get('predictions', [])
                        if len(predictions) > 0:
                            data_complete += 0.3
                            
                except Exception as e:
                    logger.warning(f"⚠️ {symbol} 数据完整性检查失败: {e}")
            
            completion_rate = data_complete / (len(test_symbols) * 2)
            logger.info(f"📊 数据完整性通过率: {completion_rate:.1%}")
            
            if completion_rate >= 0.7:
                self.test_results['data_integrity'] = True
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"❌ 数据完整性测试异常: {e}")
            return False
    
    def test_performance(self):
        """测试性能"""
        try:
            # 测试API响应时间
            start_time = time.time()
            response = requests.get(f"{self.api_base_url}/health", timeout=10)
            response_time = time.time() - start_time
            
            if response_time < 0.1:  # 100ms
                logger.info(f"✅ API响应时间: {response_time:.3f}s - 优秀")
            elif response_time < 0.5:  # 500ms
                logger.info(f"✅ API响应时间: {response_time:.3f}s - 良好")
            else:
                logger.warning(f"⚠️ API响应时间: {response_time:.3f}s - 需要优化")
            
            # 测试并发请求
            start_time = time.time()
            import concurrent.futures
            
            def make_request():
                try:
                    requests.get(f"{self.api_base_url}/health", timeout=10)
                    return True
                except:
                    return False
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(make_request) for _ in range(10)]
                results = [f.result() for f in futures]
            
            concurrent_time = time.time() - start_time
            success_rate = sum(results) / len(results)
            
            logger.info(f"📊 并发测试: {success_rate:.1%} 成功率, 耗时: {concurrent_time:.3f}s")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 性能测试异常: {e}")
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🧪 开始综合测试")
        print("=" * 60)
        print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # 基础健康检查
        if not self.test_api_health():
            logger.error("❌ API服务不可用，停止测试")
            return False
        
        # 运行各项测试
        tests = [
            ("技术指标功能", self.test_technical_indicators),
            ("LSTM预测功能", self.test_lstm_predictions),
            ("API端点测试", self.test_api_endpoints),
            ("数据完整性", self.test_data_integrity),
            ("性能测试", self.test_performance)
        ]
        
        for test_name, test_func in tests:
            print(f"\n🔍 测试: {test_name}")
            try:
                test_func()
            except Exception as e:
                logger.error(f"❌ {test_name} 测试失败: {e}")
        
        # WebSocket测试
        print(f"\n🔍 测试: WebSocket连接")
        try:
            asyncio.run(self.test_websocket_connection())
        except Exception as e:
            logger.error(f"❌ WebSocket测试失败: {e}")
        
        # 生成测试报告
        self.generate_test_report()
    
    def generate_test_report(self):
        """生成测试报告"""
        print("\n" + "=" * 60)
        print("📊 测试报告")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(self.test_results.values())
        pass_rate = passed_tests / total_tests
        
        print(f"📈 总体通过率: {pass_rate:.1%} ({passed_tests}/{total_tests})")
        
        for test_name, result in self.test_results.items():
            status = "✅ 通过" if result else "❌ 失败"
            print(f"   {test_name}: {status}")
        
        if pass_rate >= 0.8:
            print(f"\n🎉 系统测试通过！所有核心功能正常运行。")
        elif pass_rate >= 0.6:
            print(f"\n⚠️ 系统基本可用，但部分功能需要优化。")
        else:
            print(f"\n❌ 系统存在严重问题，需要立即修复。")
        
        print("=" * 60)

def main():
    """主函数"""
    tester = ComprehensiveTest()
    tester.run_all_tests()

if __name__ == "__main__":
    main()
