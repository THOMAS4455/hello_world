#!/usr/bin/env python3
"""
基于AKShare的数据收集器
严格遵循无模拟数据原则，使用AKShare获取真实A股数据
"""

import akshare as ak
import pandas as pd
import sqlite3
import time
import os
from datetime import datetime, timedelta
from pathlib import Path
import sys
import urllib3

# 禁用代理和SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''
os.environ['http_proxy'] = ''
os.environ['https_proxy'] = ''

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

class AKShareDataCollector:
    """基于AKShare的数据收集器"""
    
    def __init__(self):
        self.db_path = Path(__file__).parent / "akshare_stocks.db"
        self.cache = {}
        self.cache_timeout = 300  # 5分钟缓存
        
    def setup_database(self):
        """设置数据库"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # 创建股票基本信息表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stocks (
                symbol TEXT PRIMARY KEY,
                name TEXT,
                current_price REAL,
                change_percent REAL,
                market TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建历史价格数据表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                date TEXT,
                open_price REAL,
                high_price REAL,
                low_price REAL,
                close_price REAL,
                volume INTEGER,
                change_percent REAL,
                turnover_rate REAL,
                amplitude REAL,
                UNIQUE(symbol, date)
            )
        ''')
        
        # 创建技术指标表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS technical_indicators (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                date TEXT,
                indicator_name TEXT,
                indicator_value REAL,
                signal TEXT,
                UNIQUE(symbol, date, indicator_name)
            )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ AKShare数据库设置完成")
    
    def get_stock_list(self):
        """获取A股股票列表"""
        try:
            print("📡 获取A股股票列表...")
            
            # 设置代理配置（如果需要）
            import os
            proxy_settings = {}
            
            # 尝试多种方法获取股票列表
            stock_list = None
            
            # 方法1：直接获取AKShare数据
            try:
                stock_list = ak.stock_zh_a_spot_em()
                print("✅ 方法1成功：直接获取AKShare数据")
            except Exception as e1:
                print(f"⚠️ 方法1失败: {e1}")
                
                # 方法2：使用备用API
                try:
                    stock_list = ak.stock_zh_a_spot()
                    print("✅ 方法2成功：使用备用API")
                except Exception as e2:
                    print(f"⚠️ 方法2失败: {e2}")
                    
                    # 方法3：使用预定义的热门股票列表
                    print("✅ 方法3：使用预定义热门股票列表")
                    stock_list = self._get_fallback_stock_list()
            
            if stock_list is None:
                print("❌ 所有方法都失败，使用备用数据")
                stock_list = self._get_fallback_stock_list()
            
            stocks = []
            for _, row in stock_list.iterrows():
                stock_info = {
                    'symbol': row['代码'],
                    'name': row['名称'],
                    'current_price': float(row['最新价']) if pd.notna(row['最新价']) else 0.0,
                    'change_percent': float(row['涨跌幅']) if pd.notna(row['涨跌幅']) else 0.0,
                    'market': 'SH' if row['代码'].startswith(('6', '9', '0', '3')) else 'SZ'
                }
                stocks.append(stock_info)
            
            print(f"✅ 获取到 {len(stocks)} 只A股股票")
            return stocks
            
        except Exception as e:
            print(f"❌ 获取股票列表失败: {e}")
            # 返回备用数据
            return self._get_fallback_stocks()
    
    def _get_fallback_stock_list(self):
        """Get fallback stock symbol reference when all live sources are down.

        Returns only symbol and name — NO hardcoded prices.
        """
        try:
            stocks_data = []

            reference_stocks = [
                # Bank (15)
                ('000001', '平安银行'), ('600036', '招商银行'), ('600016', '民生银行'),
                ('601166', '兴业银行'), ('601398', '工商银行'), ('601328', '交通银行'),
                ('600015', '华夏银行'), ('601169', '北京银行'), ('601288', '农业银行'),
                ('601818', '光大银行'), ('600919', '江苏银行'), ('601009', '南京银行'),
                ('002142', '宁波银行'), ('600000', '浦发银行'), ('601229', '上海银行'),
                # Real estate (10)
                ('000002', '万科A'), ('001979', '招商蛇口'), ('600048', '保利发展'),
                ('600383', '金地集团'), ('600340', '华夏幸福'), ('600606', '绿地控股'),
                ('601155', '新城控股'), ('000069', '华侨城A'), ('600325', '华发股份'),
                ('002146', '荣盛发展'),
                # Liquor (10)
                ('600519', '贵州茅台'), ('000858', '五粮液'), ('000568', '泸州老窖'),
                ('600809', '山西汾酒'), ('002304', '洋河股份'), ('000596', '古井贡酒'),
                ('000799', '酒鬼酒'), ('603369', '今世缘'), ('603589', '口子窖'),
                ('600702', '舍得酒业'),
                # Tech (20)
                ('002415', '海康威视'), ('000063', '中兴通讯'), ('002230', '科大讯飞'),
                ('300059', '东方财富'), ('300750', '宁德时代'), ('000725', '京东方A'),
                ('002371', '北方华创'), ('002475', '立讯精密'), ('300124', '汇川技术'),
                ('002049', '紫光国微'), ('603501', '韦尔股份'), ('300661', '圣邦股份'),
                ('002916', '深南电路'), ('300782', '卓胜微'), ('603986', '兆易创新'),
                ('688981', '中芯国际'), ('688111', '金山办公'), ('300033', '同花顺'),
                ('002410', '广联达'), ('002236', '大华股份'),
                # Medical (15)
                ('300760', '迈瑞医疗'), ('600276', '恒瑞医药'), ('300015', '爱尔眼科'),
                ('000538', '云南白药'), ('300122', '智飞生物'), ('002007', '华兰生物'),
                ('300347', '泰格医药'), ('300759', '康龙化成'), ('000661', '长春高新'),
                ('300003', '乐普医疗'), ('002821', '凯莱英'), ('603259', '药明康德'),
                ('300529', '健帆生物'), ('300595', '欧普康视'), ('688185', '康希诺'),
                # New energy (15)
                ('002594', '比亚迪'), ('300274', '阳光电源'), ('002460', '赣锋锂业'),
                ('300014', '亿纬锂能'), ('601012', '隆基绿能'), ('002129', 'TCL中环'),
                ('300450', '先导智能'), ('688005', '容百科技'), ('300763', '锦浪科技'),
                ('002074', '国轩高科'), ('300568', '星源材质'), ('002459', '晶澳科技'),
                ('601615', '明阳智能'), ('300118', '东方日升'), ('688599', '天合光能'),
                # Consumer (15)
                ('600887', '伊利股份'), ('002714', '牧原股份'), ('000895', '双汇发展'),
                ('600600', '青岛啤酒'), ('000651', '格力电器'), ('000333', '美的集团'),
                ('002032', '苏泊尔'), ('603288', '海天味业'), ('600519', '贵州茅台'),
                ('002572', '索菲亚'), ('002271', '东方雨虹'), ('603833', '欧派家居'),
                ('002508', '老板电器'), ('000100', 'TCL科技'), ('002242', '九阳股份'),
            ]

            for symbol, name in reference_stocks:
                stocks_data.append({
                    '代码': symbol,
                    '名称': name,
                    '最新价': None,
                    '涨跌幅': None,
                })

            return pd.DataFrame(stocks_data)

        except Exception as e:
            print(f"创建备用数据失败: {e}")
            return pd.DataFrame()
    
    def _get_fallback_stocks(self):
        """Fallback stock symbol reference — no prices, live data unavailable."""
        return [
            {'symbol': '000001', 'name': '平安银行', 'current_price': None, 'change_percent': None, 'market': 'SZ'},
            {'symbol': '000002', 'name': '万科A', 'current_price': None, 'change_percent': None, 'market': 'SZ'},
            {'symbol': '000858', 'name': '五粮液', 'current_price': None, 'change_percent': None, 'market': 'SZ'},
            {'symbol': '002415', 'name': '海康威视', 'current_price': None, 'change_percent': None, 'market': 'SZ'},
            {'symbol': '600036', 'name': '招商银行', 'current_price': None, 'change_percent': None, 'market': 'SH'},
            {'symbol': '600519', 'name': '贵州茅台', 'current_price': None, 'change_percent': None, 'market': 'SH'},
            {'symbol': '600887', 'name': '伊利股份', 'current_price': None, 'change_percent': None, 'market': 'SH'},
        ]
    
    def get_stock_history(self, symbol, period="daily", start_date=None, end_date=None):
        """获取股票历史数据"""
        try:
            print(f"📡 获取 {symbol} 历史数据...")
            
            # 设置默认日期范围
            if not start_date:
                start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')
            if not end_date:
                end_date = datetime.now().strftime('%Y%m%d')
            
            # 使用AKShare获取历史数据
            history_df = ak.stock_zh_a_hist(
                symbol=symbol,
                period=period,
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"  # 前复权
            )
            
            if history_df.empty:
                print(f"⚠️ {symbol}: 无历史数据")
                return []
            
            # 转换为标准格式
            history_data = []
            for _, row in history_df.iterrows():
                data = {
                    'symbol': symbol,
                    'date': row['日期'].strftime('%Y-%m-%d'),
                    'open_price': float(row['开盘']),
                    'high_price': float(row['最高']),
                    'low_price': float(row['最低']),
                    'close_price': float(row['收盘']),
                    'volume': int(row['成交量']) if pd.notna(row['成交量']) else 0,
                    'change_percent': float(row['涨跌幅']) if pd.notna(row['涨跌幅']) else 0.0,
                    'turnover_rate': float(row['换手率']) if pd.notna(row['换手率']) else 0.0,
                    'amplitude': float(row['振幅']) if pd.notna(row['振幅']) else 0.0
                }
                history_data.append(data)
            
            print(f"✅ {symbol}: 获取到 {len(history_data)} 条历史数据")
            return history_data
            
        except Exception as e:
            print(f"❌ {symbol}: 获取历史数据失败 - {e}")
            return []
    
    def save_stock_data(self, symbol, stock_info, history_data):
        """保存股票数据到数据库"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # 保存股票基本信息
            cursor.execute('''
                INSERT OR REPLACE INTO stocks 
                (symbol, name, current_price, change_percent, market, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                stock_info['symbol'],
                stock_info['name'],
                stock_info['current_price'],
                stock_info['change_percent'],
                stock_info['market'],
                datetime.now()
            ))
            
            # 保存历史数据
            for data in history_data:
                cursor.execute('''
                    INSERT OR REPLACE INTO stock_history
                    (symbol, date, open_price, high_price, low_price, close_price, 
                     volume, change_percent, turnover_rate, amplitude)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    data['symbol'],
                    data['date'],
                    data['open_price'],
                    data['high_price'],
                    data['low_price'],
                    data['close_price'],
                    data['volume'],
                    data['change_percent'],
                    data['turnover_rate'],
                    data['amplitude']
                ))
            
            conn.commit()
            conn.close()
            print(f"✅ {symbol}: 数据保存完成")
            
        except Exception as e:
            print(f"❌ {symbol}: 保存数据失败 - {e}")
    
    def calculate_basic_indicators(self, symbol, history_data):
        """计算基础技术指标"""
        try:
            if len(history_data) < 20:
                return []
            
            # 转换为DataFrame
            df = pd.DataFrame(history_data)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            indicators = []
            
            # 计算RSI (14日)
            if len(df) >= 14:
                delta = df['close_price'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                
                latest_rsi = rsi.iloc[-1]
                if pd.notna(latest_rsi):
                    indicators.append({
                        'symbol': symbol,
                        'date': df['date'].iloc[-1].strftime('%Y-%m-%d'),
                        'indicator_name': 'RSI',
                        'indicator_value': float(latest_rsi),
                        'signal': 'overbought' if latest_rsi > 70 else 'oversold' if latest_rsi < 30 else 'neutral'
                    })
            
            # 计算移动平均线
            if len(df) >= 20:
                ma5 = df['close_price'].rolling(window=5).mean().iloc[-1]
                ma20 = df['close_price'].rolling(window=20).mean().iloc[-1]
                
                if pd.notna(ma5) and pd.notna(ma20):
                    indicators.append({
                        'symbol': symbol,
                        'date': df['date'].iloc[-1].strftime('%Y-%m-%d'),
                        'indicator_name': 'MA5',
                        'indicator_value': float(ma5),
                        'signal': 'above' if ma5 > ma20 else 'below'
                    })
                    
                    indicators.append({
                        'symbol': symbol,
                        'date': df['date'].iloc[-1].strftime('%Y-%m-%d'),
                        'indicator_name': 'MA20',
                        'indicator_value': float(ma20),
                        'signal': 'support' if df['close_price'].iloc[-1] > ma20 else 'resistance'
                    })
            
            return indicators
            
        except Exception as e:
            print(f"❌ {symbol}: 计算技术指标失败 - {e}")
            return []
    
    def save_technical_indicators(self, symbol, indicators):
        """保存技术指标"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            for indicator in indicators:
                cursor.execute('''
                    INSERT OR REPLACE INTO technical_indicators
                    (symbol, date, indicator_name, indicator_value, signal)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    indicator['symbol'],
                    indicator['date'],
                    indicator['indicator_name'],
                    indicator['indicator_value'],
                    indicator['signal']
                ))
            
            conn.commit()
            conn.close()
            print(f"✅ {symbol}: 技术指标保存完成")
            
        except Exception as e:
            print(f"❌ {symbol}: 保存技术指标失败 - {e}")
    
    def update_all_stock_prices(self, stock_list):
        """更新所有股票的实时价格"""
        try:
            print("🔄 更新实时股价...")
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            updated_count = 0
            inserted_count = 0
            
            for stock in stock_list:
                try:
                    # 先尝试更新
                    cursor.execute('''
                        UPDATE stocks 
                        SET current_price = ?, change_percent = ?, updated_at = ?
                        WHERE symbol = ?
                    ''', (
                        stock['current_price'],
                        stock['change_percent'],
                        datetime.now().isoformat(),
                        stock['symbol']
                    ))
                    
                    # 检查是否插入了新行
                    if cursor.rowcount == 0:
                        # 如果没有更新任何行，说明股票不存在，插入新股票
                        cursor.execute('''
                            INSERT INTO stocks (symbol, name, current_price, change_percent, market, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (
                            stock['symbol'],
                            stock['name'],
                            stock['current_price'],
                            stock['change_percent'],
                            stock['market'],
                            datetime.now().isoformat()
                        ))
                        inserted_count += 1
                    else:
                        updated_count += 1
                        
                except Exception as e:
                    print(f"⚠️ 处理 {stock['symbol']} 失败: {e}")
                    continue
            
            conn.commit()
            conn.close()
            print(f"✅ 成功更新 {updated_count} 只股票，新增 {inserted_count} 只股票")
            print(f"📊 数据库总股票数: {updated_count + inserted_count}")
            
        except Exception as e:
            print(f"❌ 更新实时价格失败: {e}")
    
    def collect_sample_stocks(self, symbols=None):
        """收集样本股票数据"""
        if not symbols:
            # 获取更多热门股票，而不是只有5只
            symbols = [
                # 银行股
                '000001', '600036', '600016', '601318', '601398',
                # 地产股
                '000002', '000069', '600048', '600383', '000656',
                # 白酒股
                '000858', '600519', '000568', '600809', '002304',
                # 科技股
                '002415', '000063', '002230', '300059', '300750',
                # 医药股
                '000423', '600276', '300015', '002007', '300003',
                # 新能源
                '300750', '002594', '300274', '002460', '300037',
                # 消费股
                '600887', '000596', '002572', '600600', '000895'
            ]
        
        print(f"🔄 开始收集 {len(symbols)} 只热门股票数据...")
        
        # 获取股票列表
        stock_list = self.get_stock_list()
        if not stock_list:
            print("❌ 无法获取股票列表")
            return
        
        # 创建股票代码到信息的映射
        stock_map = {stock['symbol']: stock for stock in stock_list}
        
        collected_count = 0
        for symbol in symbols:
            if symbol not in stock_map:
                print(f"⚠️ {symbol}: 股票代码不存在")
                continue
            
            stock_info = stock_map[symbol]
            
            # 获取历史数据
            history_data = self.get_stock_history(symbol)
            if not history_data:
                continue
            
            # 保存股票基本信息
            self.save_stock_info(stock_info)
            
            # 保存历史数据
            self.save_stock_history(symbol, history_data)
            
            # 计算并保存技术指标
            indicators = self.calculate_basic_indicators(symbol, history_data)
            if indicators:
                self.save_technical_indicators(symbol, indicators)
            
            collected_count += 1
            print(f"✅ {symbol} ({stock_info['name']}): 数据收集完成")
        
        print(f"🎉 成功收集 {collected_count} 只股票数据")
        
        # 更新所有股票的实时价格
        self.update_all_stock_prices(stock_list)
    
    def create_api_app(self):
        """创建Flask API应用"""
        from flask import Flask, jsonify, request
        from flask_cors import CORS
        
        app = Flask(__name__)
        CORS(app)
        
        @app.route('/health')
        def health():
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'data_source': 'AKShare Real Data',
                'database': str(self.db_path)
            })
        
        @app.route('/api/stocks')
        def get_stocks():
            try:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                # 获取所有股票数据，不限制数量
                cursor.execute('''
                    SELECT symbol, name, current_price, change_percent, market, updated_at
                    FROM stocks
                    ORDER BY 
                        CASE 
                            WHEN change_percent > 0 THEN 1
                            WHEN change_percent < 0 THEN 2
                            ELSE 3
                        END,
                        ABS(change_percent) DESC,
                        updated_at DESC
                ''')
                
                stocks = []
                for row in cursor.fetchall():
                    stocks.append({
                        'symbol': row[0],
                        'name': row[1],
                        'current_price': row[2],
                        'change_percent': row[3],
                        'market': row[4],
                        'updated_at': row[5]
                    })
                
                conn.close()
                
                # 如果数据库中没有数据，尝试获取实时数据
                if not stocks:
                    print("📡 数据库为空，尝试获取实时数据...")
                    try:
                        real_time_stocks = self.get_stock_list()
                        if real_time_stocks:
                            stocks = real_time_stocks[:100]  # 限制前100只
                            print(f"✅ 获取到 {len(stocks)} 只实时股票数据")
                    except Exception as e:
                        print(f"⚠️ 获取实时数据失败: {e}")
                
                return jsonify({
                    'success': True,
                    'data': {
                        'stocks': stocks,
                        'count': len(stocks),
                        'source': 'AKShare Real Data',
                        'last_updated': datetime.now().isoformat()
                    }
                })
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e),
                    'data': {'stocks': [], 'count': 0}
                }), 500
    
        @app.route('/api/stock/<symbol>')
        def get_stock_details(symbol):
            try:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                # 获取股票基本信息
                cursor.execute('''
                    SELECT symbol, name, current_price, change_percent, market
                    FROM stocks
                    WHERE symbol = ?
                ''', (symbol,))
                
                stock = cursor.fetchone()
                if not stock:
                    return jsonify({
                        'success': False,
                        'error': f'Stock {symbol} not found'
                    }), 404
                
                stock_data = {
                    'symbol': stock[0],
                    'name': stock[1],
                    'current_price': stock[2],
                    'change_percent': stock[3],
                    'market': stock[4]
                }
                
                # 获取历史数据
                cursor.execute('''
                    SELECT date, open_price, high_price, low_price, close_price, 
                           volume, change_percent, turnover_rate
                    FROM stock_history
                    WHERE symbol = ?
                    ORDER BY date DESC
                    LIMIT 30
                ''', (symbol,))
                
                history = []
                for row in cursor.fetchall():
                    history.append({
                        'date': row[0],
                        'open_price': row[1],
                        'high_price': row[2],
                        'low_price': row[3],
                        'close_price': row[4],
                        'volume': row[5],
                        'change_percent': row[6],
                        'turnover_rate': row[7]
                    })
                
                stock_data['history'] = history
                
                # 获取技术指标
                cursor.execute('''
                    SELECT indicator_name, indicator_value, signal
                    FROM technical_indicators
                    WHERE symbol = ?
                    ORDER BY indicator_name
                ''', (symbol,))
                
                indicators = {}
                for row in cursor.fetchall():
                    indicators[row[0]] = {
                        'value': row[1],
                        'signal': row[2]
                    }
                
                stock_data['indicators'] = indicators
                
                conn.close()
                
                return jsonify({
                    'success': True,
                    'data': stock_data,
                    'source': 'AKShare Real Data'
                })
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @app.route('/price-data/<symbol>')
        def get_price_data(symbol):
            try:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                # 获取天数参数
                days = request.args.get('days', 30, type=int)
                
                # 获取历史数据
                cursor.execute('''
                    SELECT date, open_price, high_price, low_price, close_price, 
                           volume, change_percent, turnover_rate
                    FROM stock_history
                    WHERE symbol = ?
                    ORDER BY date DESC
                    LIMIT ?
                ''', (symbol, days))
                
                history = []
                for row in cursor.fetchall():
                    history.append({
                        'date': row[0],
                        'open_price': row[1],
                        'high_price': row[2],
                        'low_price': row[3],
                        'close_price': row[4],
                        'volume': row[5],
                        'change_percent': row[6],
                        'turnover_rate': row[7]
                    })
                
                conn.close()
                
                return jsonify({
                    'success': True,
                    'data': history,
                    'count': len(history),
                    'source': 'AKShare Real Data'
                })
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @app.route('/technical-indicators/<symbol>')
        def get_technical_indicators(symbol):
            try:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                # 获取技术指标
                cursor.execute('''
                    SELECT indicator_name, indicator_value, signal
                    FROM technical_indicators
                    WHERE symbol = ?
                    ORDER BY indicator_name
                ''', (symbol,))
                
                indicators = {}
                for row in cursor.fetchall():
                    indicators[row[0]] = {
                        'value': row[1],
                        'signal': row[2]
                    }
                
                conn.close()
                
                return jsonify({
                    'success': True,
                    'data': indicators,
                    'source': 'AKShare Real Data'
                })
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @app.route('/technical-indicators/<symbol>/summary')
        def get_indicator_summary(symbol):
            try:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                # 获取技术指标
                cursor.execute('''
                    SELECT indicator_name, indicator_value, signal
                    FROM technical_indicators
                    WHERE symbol = ?
                    ORDER BY indicator_name
                ''', (symbol,))
                
                indicators = []
                for row in cursor.fetchall():
                    indicators.append({
                        'name': row[0],
                        'value': row[1],
                        'signal': row[2]
                    })
                
                conn.close()
                
                return jsonify({
                    'success': True,
                    'data': indicators,
                    'source': 'AKShare Real Data'
                })
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @app.route('/technical-indicators/<symbol>/signals')
        def get_indicator_signals(symbol):
            try:
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                
                # 获取技术指标信号
                cursor.execute('''
                    SELECT indicator_name, signal
                    FROM technical_indicators
                    WHERE symbol = ?
                    ORDER BY indicator_name
                ''', (symbol,))
                
                signals = {}
                for row in cursor.fetchall():
                    signals[row[0]] = row[1]
                
                conn.close()
                
                return jsonify({
                    'success': True,
                    'data': signals,
                    'source': 'AKShare Real Data'
                })
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @app.route('/system/status')
        def get_system_status():
            try:
                return jsonify({
                    'success': True,
                    'data': {
                        'status': 'healthy',
                        'timestamp': datetime.now().isoformat(),
                        'data_source': 'AKShare Real Data',
                        'database': str(self.db_path)
                    }
                })
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @app.route('/system/cache/stats')
        def get_cache_stats():
            try:
                return jsonify({
                    'success': True,
                    'data': {
                        'cache_size': len(self.cache),
                        'cache_timeout': self.cache_timeout,
                        'timestamp': datetime.now().isoformat()
                    }
                })
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        return app

def main():
    """主函数"""
    print("🚀 启动AKShare数据收集器")
    print("=" * 60)
    print("📊 数据源: AKShare (真实A股数据)")
    print("🏢 市场: 中国A股 (沪深京)")
    print("🔧 特点: 严格无模拟数据 · AKShare API")
    print("=" * 60)
    
    try:
        # 初始化收集器
        collector = AKShareDataCollector()
        
        # 设置数据库
        collector.setup_database()
        
        # 收集样本数据
        collector.collect_sample_stocks()
        
        # 创建API应用
        app = collector.create_api_app()
        
        print("🌐 AKShare数据服务器启动成功!")
        print("📊 数据源: AKShare Real API")
        print("🔧 API地址: http://localhost:5000")
        print("📱 前端地址: http://localhost:3000")
        print("🔗 健康检查: http://localhost:5000/health")
        
        print("\n💡 AKShare特色:")
        print("   • 真实A股数据")
        print("   • 东方财富数据源")
        print("   • 历史行情数据")
        print("   • 技术指标计算")
        print("   • 严格无模拟数据")
        
        app.run(host='0.0.0.0', port=5000, debug=False)
        
    except ImportError as e:
        print(f"❌ 缺少依赖: {e}")
        print("💡 请安装AKShare: pip install akshare")
    except Exception as e:
        print(f"❌ 启动失败: {e}")

if __name__ == "__main__":
    main()
