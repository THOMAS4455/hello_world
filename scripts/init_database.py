#!/usr/bin/env python3
"""
数据库初始化脚本
"""

import sqlite3
import os
from pathlib import Path
from datetime import datetime

def create_database():
    """创建数据库和表"""
    
    # 确保数据目录存在
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    # 数据库文件路径
    db_path = data_dir / "stock_prediction.db"
    
    try:
        # 连接数据库
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 创建股票信息表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                price REAL,
                change REAL,
                change_percent REAL,
                volume INTEGER,
                market_cap REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建股票历史数据表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                price REAL NOT NULL,
                change REAL,
                change_percent REAL,
                volume INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (symbol) REFERENCES stocks (symbol)
            )
        ''')
        
        # 创建AI分析结果表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                analysis_type TEXT NOT NULL,
                content TEXT,
                sentiment_score REAL,
                confidence REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建用户查询记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_text TEXT NOT NULL,
                query_type TEXT,
                response_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建系统日志表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                module TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stocks_symbol ON stocks(symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stock_history_symbol ON stock_history(symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stock_history_timestamp ON stock_history(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ai_analysis_symbol ON ai_analysis(symbol)')
        
        # 提交更改
        conn.commit()
        print(f"✅ 数据库初始化完成: {db_path}")
        
        # 插入一些示例数据
        insert_sample_data(cursor)
        conn.commit()
        
        return True
        
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        return False
    finally:
        conn.close()

def insert_sample_data(cursor):
    """插入示例数据"""
    
    sample_stocks = [
        ('sh000001', '上证指数', 3074.51, 15.55, 0.51, 1000000, 0),
        ('sz399001', '深证成指', 13760.37, 153.93, 1.13, 500000, 0),
        ('sz000001', '平安银行', 11.02, 0.08, 0.73, 100000, 0),
        ('000002', '万科A', 8.45, -0.12, -1.40, 80000, 0),
        ('000858', '五粮液', 145.67, 2.34, 1.63, 120000, 0)
    ]
    
    cursor.executemany('''
        INSERT OR REPLACE INTO stocks (symbol, name, price, change, change_percent, volume, market_cap)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', sample_stocks)
    
    print("✅ 示例数据插入完成")

def check_database():
    """检查数据库状态"""
    db_path = Path("data/stock_prediction.db")
    
    if not db_path.exists():
        print("❌ 数据库文件不存在")
        return False
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        required_tables = ['stocks', 'stock_history', 'ai_analysis', 'user_queries', 'system_logs']
        
        for table in required_tables:
            if table in tables:
                print(f"✅ 表 {table} 存在")
            else:
                print(f"❌ 表 {table} 不存在")
                return False
        
        # 检查数据
        cursor.execute("SELECT COUNT(*) FROM stocks")
        stock_count = cursor.fetchone()[0]
        print(f"📊 股票数据: {stock_count} 条")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 数据库检查失败: {e}")
        return False

def main():
    """主函数"""
    print("🔧 开始数据库初始化...")
    
    # 创建数据库
    if create_database():
        print("🎉 数据库初始化成功！")
        
        # 检查数据库
        if check_database():
            print("✅ 数据库状态正常")
        else:
            print("⚠️ 数据库状态异常")
    else:
        print("❌ 数据库初始化失败")

if __name__ == "__main__":
    main()
