"""
日志配置模块
"""

import logging
import sys

# 创建 logger
logger = logging.getLogger("hr-analytics")
logger.setLevel(logging.INFO)

# 控制台 handler
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    
    # 格式化
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)

# 防止日志传播到根 logger
logger.propagate = False
