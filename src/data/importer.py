"""
数据导入器
支持 CSV 和 Excel 文件导入
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import io

import pandas as pd
from Logging import logger

from .mongodb import mongodb
from .models import Employee, Department, PerformanceRecord, RecruitmentRecord


class DataImporter:
    """数据导入器"""
    
    # 字段映射配置
    EMPLOYEE_FIELD_MAP = {
        '工号': 'employee_id',
        '员工ID': 'employee_id',
        '姓名': 'name',
        '性别': 'gender',
        '出生日期': 'birth_date',
        '入职日期': 'hire_date',
        '部门ID': 'department_id',
        '部门': 'department_id',
        '职位ID': 'position_id',
        '职位': 'position_name',
        '职级': 'level',
        '上级ID': 'manager_id',
        '状态': 'status',
        '基本工资': 'salary.base',
        '奖金': 'salary.bonus',
        '学历': 'education',
        '邮箱': 'email',
        '电话': 'phone',
    }
    
    DEPARTMENT_FIELD_MAP = {
        '部门ID': 'department_id',
        '部门名称': 'name',
        '上级部门ID': 'parent_id',
        '层级': 'level',
        '编制人数': 'headcount_budget',
        '实际人数': 'headcount_actual',
    }
    
    PERFORMANCE_FIELD_MAP = {
        '员工ID': 'employee_id',
        '工号': 'employee_id',
        '考核周期': 'period',
        '绩效等级': 'rating',
        '绩效分数': 'rating_score',
        'OKR完成度': 'okr_score',
        '评审人ID': 'reviewer_id',
    }
    
    RECRUITMENT_FIELD_MAP = {
        '需求ID': 'requisition_id',
        '职位ID': 'position_id',
        '职位名称': 'position_name',
        '部门ID': 'department_id',
        '渠道': 'channel',
        '渠道成本': 'channel_cost',
        '候选人姓名': 'candidate_name',
        '候选人邮箱': 'candidate_email',
        '当前阶段': 'stage',
    }
    
    def __init__(self):
        self.import_stats = {
            'total_rows': 0,
            'success': 0,
            'failed': 0,
            'errors': []
        }
    
    async def import_csv(
        self,
        file_path: str,
        collection_name: str,
        encoding: str = 'utf-8',
        delimiter: str = ','
    ) -> Dict[str, Any]:
        """导入 CSV 文件"""
        try:
            df = pd.read_csv(file_path, encoding=encoding, delimiter=delimiter)
            return await self._import_dataframe(df, collection_name)
        except Exception as e:
            logger.error(f"CSV import error: {e}")
            return {'success': False, 'error': str(e)}
    
    async def import_csv_content(
        self,
        content: bytes,
        collection_name: str,
        encoding: str = 'utf-8'
    ) -> Dict[str, Any]:
        """导入 CSV 内容（从上传的文件）"""
        try:
            df = pd.read_csv(io.BytesIO(content), encoding=encoding)
            return await self._import_dataframe(df, collection_name)
        except Exception as e:
            logger.error(f"CSV content import error: {e}")
            return {'success': False, 'error': str(e)}
    
    async def import_excel(
        self,
        file_path: str,
        collection_name: str,
        sheet_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """导入 Excel 文件"""
        try:
            if sheet_name:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
            else:
                df = pd.read_excel(file_path)
            return await self._import_dataframe(df, collection_name)
        except Exception as e:
            logger.error(f"Excel import error: {e}")
            return {'success': False, 'error': str(e)}
    
    async def import_excel_content(
        self,
        content: bytes,
        collection_name: str,
        sheet_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """导入 Excel 内容（从上传的文件）"""
        try:
            if sheet_name:
                df = pd.read_excel(io.BytesIO(content), sheet_name=sheet_name)
            else:
                df = pd.read_excel(io.BytesIO(content))
            return await self._import_dataframe(df, collection_name)
        except Exception as e:
            logger.error(f"Excel content import error: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _import_dataframe(
        self,
        df: pd.DataFrame,
        collection_name: str
    ) -> Dict[str, Any]:
        """导入 DataFrame 到 MongoDB"""
        self.import_stats = {
            'total_rows': len(df),
            'success': 0,
            'failed': 0,
            'errors': []
        }
        
        # 选择字段映射
        field_map = self._get_field_map(collection_name)
        
        # 重命名列
        df = self._map_columns(df, field_map)
        
        # 数据清洗和转换
        df = self._clean_dataframe(df, collection_name)
        
        # 转换为字典列表
        records = df.to_dict('records')
        
        # 批量插入
        collection = mongodb.collection(collection_name)
        batch_size = 1000
        
        for i in range(0, len(records), batch_size):
            batch = records[i:i+batch_size]
            try:
                # 添加时间戳
                for record in batch:
                    record['created_at'] = datetime.utcnow()
                    record['updated_at'] = datetime.utcnow()
                    record['_imported'] = True
                
                await collection.insert_many(batch, ordered=False)
                self.import_stats['success'] += len(batch)
            except Exception as e:
                self.import_stats['failed'] += len(batch)
                self.import_stats['errors'].append(str(e))
                logger.error(f"Batch insert error: {e}")
        
        return {
            'success': True,
            'collection': collection_name,
            'stats': self.import_stats
        }
    
    def _get_field_map(self, collection_name: str) -> Dict[str, str]:
        """获取字段映射"""
        maps = {
            'employees': self.EMPLOYEE_FIELD_MAP,
            'departments': self.DEPARTMENT_FIELD_MAP,
            'performance_records': self.PERFORMANCE_FIELD_MAP,
            'recruitment_records': self.RECRUITMENT_FIELD_MAP,
        }
        return maps.get(collection_name, {})
    
    def _map_columns(self, df: pd.DataFrame, field_map: Dict[str, str]) -> pd.DataFrame:
        """映射列名"""
        rename_map = {}
        for col in df.columns:
            if col in field_map:
                rename_map[col] = field_map[col]
            elif col.strip() in field_map:
                rename_map[col] = field_map[col.strip()]
        
        if rename_map:
            df = df.rename(columns=rename_map)
        
        return df
    
    def _clean_dataframe(self, df: pd.DataFrame, collection_name: str) -> pd.DataFrame:
        """清洗数据"""
        # 去除空白
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].astype(str).str.strip()
        
        # 处理日期列
        date_columns = ['birth_date', 'hire_date', 'resignation_date', 'created_at']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        # 处理数值列
        numeric_columns = ['salary.base', 'salary.bonus', 'rating_score', 'okr_score', 'channel_cost']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # 处理性别
        if 'gender' in df.columns:
            df['gender'] = df['gender'].map({'男': 'M', '女': 'F', 'M': 'M', 'F': 'F'}).fillna('O')
        
        # 处理状态
        if 'status' in df.columns:
            status_map = {
                '在职': 'active', '离职': 'resigned', '终止': 'terminated',
                'active': 'active', 'resigned': 'resigned'
            }
            df['status'] = df['status'].map(status_map).fillna('active')
        
        # 处理嵌套字段（salary）
        if 'salary.base' in df.columns:
            df['salary'] = df.apply(
                lambda row: {
                    'base': row.get('salary.base', 0),
                    'bonus': row.get('salary.bonus', 0),
                    'allowance': 0,
                    'total': row.get('salary.base', 0) + row.get('salary.bonus', 0)
                },
                axis=1
            )
            df = df.drop(columns=['salary.base', 'salary.bonus'], errors='ignore')
        
        # 移除空行
        df = df.dropna(how='all')
        
        return df
    
    async def detect_file_type(self, file_path: str) -> str:
        """检测文件类型"""
        path = Path(file_path)
        suffix = path.suffix.lower()
        
        if suffix in ['.csv', '.txt']:
            return 'csv'
        elif suffix in ['.xlsx', '.xls']:
            return 'excel'
        else:
            raise ValueError(f"Unsupported file type: {suffix}")
    
    async def auto_import(
        self,
        file_path: str,
        collection_name: str
    ) -> Dict[str, Any]:
        """自动检测并导入文件"""
        file_type = await self.detect_file_type(file_path)
        
        if file_type == 'csv':
            return await self.import_csv(file_path, collection_name)
        else:
            return await self.import_excel(file_path, collection_name)


# 全局实例
data_importer = DataImporter()
