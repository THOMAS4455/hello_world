#!/usr/bin/env python3
"""
数据库配置
"""

import os
from pathlib import Path
from typing import Dict, Any

def get_database_config() -> Dict[str, Any]:
    """获取数据库配置"""
    
    # 项目根目录
    project_root = Path(__file__).parent.parent
    
    return {
        'postgres': {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', 5432)),
            'database': os.getenv('POSTGRES_DB', 'stock_prediction'),
            'user': os.getenv('POSTGRES_USER', 'postgres'),
            'password': os.getenv('POSTGRES_PASSWORD', 'password'),
            'sslmode': os.getenv('POSTGRES_SSLMODE', 'prefer'),
            'connect_timeout': 10,
            'application_name': 'stock_prediction_system'
        },
        'redis': {
            'host': os.getenv('REDIS_HOST', 'localhost'),
            'port': int(os.getenv('REDIS_PORT', 6379)),
            'db': int(os.getenv('REDIS_DB', 0)),
            'password': os.getenv('REDIS_PASSWORD', None),
            'decode_responses': True,
            'socket_timeout': 5,
            'socket_connect_timeout': 5,
            'retry_on_timeout': True,
            'health_check_interval': 30
        },
        'fallback': {
            'use_sqlite': True,
            'sqlite_path': project_root / "data" / "astocks_prediction.db"
        },
        'pool': {
            'min_connections': 2,
            'max_connections': 20,
            'connection_timeout': 30,
            'idle_timeout': 300
        },
        'cache': {
            'default_expire': 3600,  # 1小时
            'stock_data_expire': 300,  # 5分钟
            'technical_indicators_expire': 1800,  # 30分钟
            'predictions_expire': 7200,  # 2小时
            'user_preferences_expire': 86400  # 24小时
        }
    }

def get_postgres_connection_string() -> str:
    """获取PostgreSQL连接字符串"""
    config = get_database_config()['postgres']
    
    return f"postgresql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"

def get_redis_connection_string() -> str:
    """获取Redis连接字符串"""
    config = get_database_config()['redis']
    
    if config['password']:
        return f"redis://:{config['password']}@{config['host']}:{config['port']}/{config['db']}"
    else:
        return f"redis://{config['host']}:{config['port']}/{config['db']}"
