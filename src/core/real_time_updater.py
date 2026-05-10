#!/usr/bin/env python3
"""
实时数据更新模块
提供自动化的股票数据更新服务
"""

import time
import threading
import schedule
from datetime import datetime, timedelta
import logging
from .akshare_data_collector import AKShareDataCollector

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RealTimeUpdater:
    """实时数据更新器"""
    
    def __init__(self, update_interval=60):  # 默认60秒更新一次
        self.update_interval = update_interval
        self.collector = AKShareDataCollector()
        self.is_running = False
        self.update_thread = None
        self.last_update = None
        self.update_count = 0
        
    def start_auto_update(self):
        """启动自动更新"""
        if self.is_running:
            logger.warning("自动更新已在运行中")
            return
            
        self.is_running = True
        self.update_thread = threading.Thread(target=self._auto_update_loop, daemon=True)
        self.update_thread.start()
        logger.info(f"🚀 自动更新已启动，更新间隔: {self.update_interval}秒")
        
    def stop_auto_update(self):
        """停止自动更新"""
        self.is_running = False
        if self.update_thread:
            self.update_thread.join(timeout=5)
        logger.info("🛑 自动更新已停止")
        
    def _auto_update_loop(self):
        """自动更新循环"""
        while self.is_running:
            try:
                self._update_all_stocks()
                time.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"❌ 自动更新失败: {e}")
                time.sleep(10)  # 出错后等待10秒再重试
                
    def _update_all_stocks(self):
        """更新所有股票数据"""
        try:
            start_time = time.time()
            logger.info("🔄 开始自动更新股票数据...")
            
            # 获取股票列表
            stock_list = self.collector.get_stock_list()
            if stock_list:
                # 更新股票价格
                self.collector.update_all_stock_prices(stock_list)
                self.last_update = datetime.now()
                self.update_count += 1
                
                elapsed_time = time.time() - start_time
                logger.info(f"✅ 自动更新完成，更新了 {len(stock_list)} 只股票，耗时: {elapsed_time:.2f}秒")
            else:
                logger.warning("⚠️ 无法获取股票列表，跳过本次更新")
                
        except Exception as e:
            logger.error(f"❌ 更新股票数据失败: {e}")
            
    def force_update(self):
        """强制立即更新"""
        logger.info("🔄 强制更新股票数据...")
        self._update_all_stocks()
        
    def get_status(self):
        """获取更新状态"""
        return {
            'is_running': self.is_running,
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'update_count': self.update_count,
            'update_interval': self.update_interval,
            'next_update': (self.last_update + timedelta(seconds=self.update_interval)).isoformat() if self.last_update else None
        }

# 全局更新器实例
real_time_updater = RealTimeUpdater()

def start_real_time_service():
    """启动实时更新服务"""
    real_time_updater.start_auto_update()
    return real_time_updater

def stop_real_time_service():
    """停止实时更新服务"""
    real_time_updater.stop_auto_update()

if __name__ == "__main__":
    # 测试自动更新
    updater = RealTimeUpdater(update_interval=30)  # 30秒更新一次
    updater.start_auto_update()
    
    try:
        while True:
            status = updater.get_status()
            print(f"状态: {status}")
            time.sleep(10)
    except KeyboardInterrupt:
        print("\n🛑 停止自动更新...")
        updater.stop_auto_update()
