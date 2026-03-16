"""
HR 模拟数据生成器
支持生成 500 万级符合真实分布的 HR 数据
"""

import asyncio
import random
from datetime import datetime, date, timedelta
from typing import Generator, List, Dict, Any, Optional
import uuid

import numpy as np
from faker import Faker
from loguru import logger

from .models import (
    Employee, Department, PerformanceRecord, RecruitmentRecord, RiskAssessment,
    Gender, EmployeeStatus, PerformanceRating, RecruitmentStage, RiskLevel,
    Education, Salary, StageHistory
)
from .mongodb import mongodb


class HRDataGenerator:
    """HR 数据生成器"""
    
    # 部门配置
    DEPARTMENTS = [
        {"name": "CEO办公室", "level": 1},
        {"name": "研发中心", "level": 2, "children": [
            {"name": "前端开发部", "level": 3},
            {"name": "后端开发部", "level": 3},
            {"name": "移动开发部", "level": 3},
            {"name": "测试部", "level": 3},
            {"name": "运维部", "level": 3},
        ]},
        {"name": "产品中心", "level": 2, "children": [
            {"name": "产品设计部", "level": 3},
            {"name": "用户研究部", "level": 3},
        ]},
        {"name": "销售中心", "level": 2, "children": [
            {"name": "华北区销售", "level": 3},
            {"name": "华东区销售", "level": 3},
            {"name": "华南区销售", "level": 3},
            {"name": "西区销售", "level": 3},
        ]},
        {"name": "市场部", "level": 2, "children": [
            {"name": "品牌推广", "level": 3},
            {"name": "渠道运营", "level": 3},
        ]},
        {"name": "人力资源部", "level": 2, "children": [
            {"name": "招聘组", "level": 3},
            {"name": "HRBP组", "level": 3},
            {"name": "薪酬绩效组", "level": 3},
        ]},
        {"name": "财务部", "level": 2},
        {"name": "法务部", "level": 2},
        {"name": "行政部", "level": 2},
    ]
    
    # 职级体系
    LEVELS = ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "M1", "M2", "M3", "M4"]
    LEVEL_SALARY_RANGES = {
        "P1": (5000, 8000),
        "P2": (7000, 12000),
        "P3": (10000, 18000),
        "P4": (15000, 25000),
        "P5": (20000, 35000),
        "P6": (30000, 50000),
        "P7": (45000, 70000),
        "P8": (60000, 100000),
        "P9": (80000, 150000),
        "M1": (25000, 40000),
        "M2": (35000, 60000),
        "M3": (50000, 90000),
        "M4": (70000, 150000),
    }
    
    # 招聘渠道
    CHANNELS = [
        {"name": "猎聘", "cost_range": (3000, 8000), "quality": 0.7},
        {"name": "BOSS直聘", "cost_range": (2000, 5000), "quality": 0.65},
        {"name": "拉勾", "cost_range": (2500, 6000), "quality": 0.6},
        {"name": "智联招聘", "cost_range": (1500, 4000), "quality": 0.5},
        {"name": "前程无忧", "cost_range": (1500, 4000), "quality": 0.5},
        {"name": "内推", "cost_range": (1000, 3000), "quality": 0.85},
        {"name": "猎头", "cost_range": (20000, 50000), "quality": 0.9},
        {"name": "校园招聘", "cost_range": (500, 2000), "quality": 0.6},
        {"name": "LinkedIn", "cost_range": (5000, 15000), "quality": 0.75},
    ]
    
    # 职位配置
    POSITIONS = [
        {"id": "POS001", "name": "软件工程师", "dept_pattern": "开发"},
        {"id": "POS002", "name": "高级软件工程师", "dept_pattern": "开发"},
        {"id": "POS003", "name": "技术专家", "dept_pattern": "开发"},
        {"id": "POS004", "name": "前端工程师", "dept_pattern": "前端"},
        {"id": "POS005", "name": "后端工程师", "dept_pattern": "后端"},
        {"id": "POS006", "name": "测试工程师", "dept_pattern": "测试"},
        {"id": "POS007", "name": "运维工程师", "dept_pattern": "运维"},
        {"id": "POS008", "name": "产品经理", "dept_pattern": "产品"},
        {"id": "POS009", "name": "高级产品经理", "dept_pattern": "产品"},
        {"id": "POS010", "name": "销售代表", "dept_pattern": "销售"},
        {"id": "POS011", "name": "销售经理", "dept_pattern": "销售"},
        {"id": "POS012", "name": "HRBP", "dept_pattern": "人力"},
        {"id": "POS013", "name": "招聘专员", "dept_pattern": "招聘"},
        {"id": "POS014", "name": "财务专员", "dept_pattern": "财务"},
        {"id": "POS015", "name": "市场专员", "dept_pattern": "市场"},
    ]
    
    def __init__(self, seed: int = 42):
        """初始化生成器"""
        self.seed = seed
        self.fake = Faker('zh_CN')
        Faker.seed(seed)
        np.random.seed(seed)
        random.seed(seed)
        
        self.departments: List[Dict] = []
        self.employees: List[Dict] = []
        self.dept_employee_map: Dict[str, List[str]] = {}
    
    def _flatten_departments(self, dept_list: List[Dict], parent_id: Optional[str] = None, counter: Optional[List[int]] = None) -> List[Dict]:
        """扁平化部门结构"""
        if counter is None:
            counter = [0]  # 使用列表来保持引用，实现跨递归调用的计数
        
        result = []
        for dept in dept_list:
            counter[0] += 1
            dept_id = f"DEPT{counter[0]:03d}"
            dept_data = {
                "department_id": dept_id,
                "name": dept["name"],
                "parent_id": parent_id,
                "level": dept["level"],
                "headcount_budget": random.randint(20, 200),
                "headcount_actual": 0,
                "head_id": None,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
            result.append(dept_data)
            
            if "children" in dept:
                result.extend(self._flatten_departments(dept["children"], dept_id, counter))
        
        return result
    
    def generate_departments(self) -> List[Dict]:
        """生成部门数据"""
        self.departments = self._flatten_departments(self.DEPARTMENTS)
        self.dept_employee_map = {d["department_id"]: [] for d in self.departments}
        logger.info(f"Generated {len(self.departments)} departments")
        return self.departments
    
    def generate_employee(self, employee_id: str, dept_id: str) -> Dict:
        """生成单个员工数据"""
        # 年龄：正态分布 (μ=32, σ=8)，范围 22-60
        age = int(np.clip(np.random.normal(32, 8), 22, 60))
        birth_year = date.today().year - age
        # 使用 datetime 而非 date，MongoDB 不支持 date 类型
        birth_date = datetime(birth_year, random.randint(1, 12), random.randint(1, 28))
        
        # 司龄：指数分布，多数人司龄短
        max_tenure = min(age - 22, 20)
        tenure_years = min(np.random.exponential(3), max_tenure)
        hire_days = int(tenure_years * 365)
        hire_date = datetime.utcnow() - timedelta(days=hire_days)
        
        # 职级：与司龄相关
        if tenure_years < 1:
            level = random.choice(["P1", "P2", "P3"])
        elif tenure_years < 3:
            level = random.choice(["P3", "P4", "P5"])
        elif tenure_years < 5:
            level = random.choice(["P4", "P5", "P6", "M1"])
        elif tenure_years < 8:
            level = random.choice(["P5", "P6", "P7", "M1", "M2"])
        else:
            level = random.choice(["P6", "P7", "P8", "P9", "M2", "M3", "M4"])
        
        # 薪资：对数正态分布
        salary_range = self.LEVEL_SALARY_RANGES[level]
        base_salary = int(np.clip(
            np.random.lognormal(np.log(np.mean(salary_range)), 0.3),
            salary_range[0],
            salary_range[1]
        ))
        bonus = int(base_salary * random.uniform(0.1, 0.3))
        
        # 状态：大部分在职
        status = random.choices(
            [EmployeeStatus.ACTIVE.value, EmployeeStatus.RESIGNED.value],
            weights=[0.92, 0.08]
        )[0]
        
        resignation_date = None
        if status == EmployeeStatus.RESIGNED.value:
            # 确保离职日期范围合理
            max_days = max(91, hire_days)  # 至少 91 天，避免 randint 范围错误
            resignation_date = hire_date + timedelta(days=random.randint(90, max_days))
        
        # 性别
        gender = random.choice([Gender.MALE.value, Gender.FEMALE.value])
        
        # 学历
        education = random.choices(
            [e.value for e in Education],
            weights=[0.05, 0.1, 0.55, 0.25, 0.05]
        )[0]
        
        # 职位
        dept_name = next((d["name"] for d in self.departments if d["department_id"] == dept_id), "")
        matching_positions = [p for p in self.POSITIONS if p["dept_pattern"] in dept_name]
        if not matching_positions:
            matching_positions = self.POSITIONS[:3]
        position = random.choice(matching_positions)
        
        return {
            "employee_id": employee_id,
            "name": self.fake.name(),
            "gender": gender,
            "birth_date": birth_date,
            "hire_date": hire_date,
            "department_id": dept_id,
            "position_id": position["id"],
            "position_name": position["name"],
            "level": level,
            "manager_id": None,  # 稍后设置
            "status": status,
            "resignation_date": resignation_date,
            "salary": {
                "base": base_salary,
                "bonus": bonus,
                "allowance": random.randint(500, 3000),
                "total": base_salary + bonus + random.randint(500, 3000)
            },
            "education": education,
            "major": self.fake.job()[:10] if random.random() > 0.5 else None,
            "email": f"{employee_id.lower()}@company.com",
            "phone": self.fake.phone_number(),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
    
    def generate_employees(self, count: int) -> Generator[Dict, None, None]:
        """生成员工数据（生成器模式）"""
        if not self.departments:
            self.generate_departments()
        
        # 按部门分配员工
        dept_weights = [d["headcount_budget"] for d in self.departments]
        total_weight = sum(dept_weights)
        dept_weights = [w / total_weight for w in dept_weights]
        
        for i in range(count):
            employee_id = f"EMP{i + 1:07d}"
            dept_id = np.random.choice(
                [d["department_id"] for d in self.departments],
                p=dept_weights
            )
            
            employee = self.generate_employee(employee_id, dept_id)
            self.dept_employee_map[dept_id].append(employee_id)
            
            if (i + 1) % 100000 == 0:
                logger.info(f"Generated {i + 1:,} employees")
            
            yield employee
    
    def generate_performance_records(
        self,
        employee_ids: List[str],
        periods: List[str] = None
    ) -> Generator[Dict, None, None]:
        """生成绩效记录"""
        if periods is None:
            periods = ["2023-H1", "2023-H2", "2024-H1"]
        
        # 绩效分布：正态 + 强制分布约束
        rating_weights = [0.05, 0.20, 0.50, 0.20, 0.05]  # S, A, B, C, D
        ratings = list(PerformanceRating)
        
        for employee_id in employee_ids:
            for period in periods:
                rating = random.choices(ratings, weights=rating_weights)[0]
                
                # 评分与等级对应
                rating_score_ranges = {
                    PerformanceRating.S: (90, 100),
                    PerformanceRating.A: (80, 89),
                    PerformanceRating.B: (70, 79),
                    PerformanceRating.C: (60, 69),
                    PerformanceRating.D: (0, 59),
                }
                score_range = rating_score_ranges[rating]
                rating_score = random.uniform(score_range[0], score_range[1])
                
                # OKR 完成度与绩效正相关
                okr_base = {
                    PerformanceRating.S: 0.95,
                    PerformanceRating.A: 0.85,
                    PerformanceRating.B: 0.75,
                    PerformanceRating.C: 0.60,
                    PerformanceRating.D: 0.40,
                }[rating]
                okr_score = np.clip(okr_base + np.random.normal(0, 0.1), 0, 1)
                
                yield {
                    "employee_id": employee_id,
                    "period": period,
                    "rating": rating.value,
                    "rating_score": round(rating_score, 1),
                    "okr_score": round(okr_score, 2),
                    "okr_details": None,
                    "reviewer_id": f"EMP{random.randint(1, 1000):07d}",
                    "self_review": None,
                    "manager_review": None,
                    "created_at": datetime.utcnow(),
                }
    
    def generate_recruitment_records(self, count: int) -> Generator[Dict, None, None]:
        """生成招聘记录"""
        stages = list(RecruitmentStage)
        
        for i in range(count):
            channel = random.choice(self.CHANNELS)
            channel_cost = random.uniform(*channel["cost_range"])
            
            # 根据渠道质量决定最终阶段
            quality = channel["quality"]
            if random.random() < quality * 0.3:
                final_stage = RecruitmentStage.HIRED
            elif random.random() < quality * 0.5:
                final_stage = random.choice([
                    RecruitmentStage.OFFER_ACCEPTED,
                    RecruitmentStage.OFFER_REJECTED
                ])
            elif random.random() < quality * 0.7:
                final_stage = random.choice([
                    RecruitmentStage.FIRST_INTERVIEW,
                    RecruitmentStage.SECOND_INTERVIEW,
                    RecruitmentStage.FINAL_INTERVIEW
                ])
            else:
                final_stage = random.choice([
                    RecruitmentStage.RESUME,
                    RecruitmentStage.SCREENING,
                    RecruitmentStage.WITHDRAWN
                ])
            
            # 生成阶段历史
            created_at = datetime.utcnow() - timedelta(days=random.randint(1, 365))
            stage_history = []
            current_time = created_at
            
            for stage in stages:
                stage_history.append({
                    "stage": stage.value,
                    "timestamp": current_time,
                    "notes": None
                })
                current_time += timedelta(days=random.randint(1, 7))
                if stage == final_stage:
                    break
            
            dept = random.choice(self.departments)
            position = random.choice(self.POSITIONS)
            
            yield {
                "requisition_id": f"REQ{i + 1:06d}",
                "position_id": position["id"],
                "position_name": position["name"],
                "department_id": dept["department_id"],
                "channel": channel["name"],
                "channel_cost": round(channel_cost, 2),
                "candidate_name": self.fake.name(),
                "candidate_email": self.fake.email(),
                "candidate_phone": self.fake.phone_number(),
                "stage": final_stage.value,
                "stage_history": stage_history,
                "hired_employee_id": f"EMP{random.randint(1, 1000000):07d}" if final_stage == RecruitmentStage.HIRED else None,
                "created_at": created_at,
                "updated_at": datetime.utcnow(),
            }
    
    def generate_risk_assessments(self, employee_ids: List[str]) -> Generator[Dict, None, None]:
        """生成风险评估数据"""
        risk_factors_pool = [
            "salary_below_market",
            "no_promotion_2_years",
            "manager_change",
            "low_engagement",
            "high_workload",
            "limited_growth",
            "peer_departures",
            "performance_decline",
            "attendance_issues",
            "training_decrease"
        ]
        
        for employee_id in employee_ids:
            # 离职风险分数：Beta分布，大多数人低风险
            risk_score = np.random.beta(2, 5)
            
            # 风险等级
            if risk_score >= 0.85:
                risk_level = RiskLevel.CRITICAL
            elif risk_score >= 0.7:
                risk_level = RiskLevel.HIGH
            elif risk_score >= 0.4:
                risk_level = RiskLevel.MEDIUM
            else:
                risk_level = RiskLevel.LOW
            
            # 风险因素：风险越高，因素越多
            num_factors = min(int(risk_score * 10) + 1, 5)
            risk_factors = random.sample(risk_factors_pool, num_factors)
            
            # 建议行动
            actions_map = {
                "salary_below_market": "salary_review",
                "no_promotion_2_years": "career_discussion",
                "manager_change": "onboarding_support",
                "low_engagement": "engagement_survey",
                "high_workload": "workload_review",
                "limited_growth": "development_plan",
                "peer_departures": "retention_talk",
                "performance_decline": "performance_coaching",
                "attendance_issues": "welfare_check",
                "training_decrease": "training_opportunity"
            }
            recommended_actions = [actions_map.get(f, "general_check") for f in risk_factors[:3]]
            
            # 高潜评分
            high_potential_score = np.random.beta(3, 7) if random.random() > 0.7 else None
            
            yield {
                "employee_id": employee_id,
                "assessment_date": datetime.utcnow(),
                "turnover_risk_score": round(risk_score, 3),
                "risk_level": risk_level.value,
                "risk_factors": risk_factors,
                "factor_weights": {f: round(random.uniform(0.1, 0.3), 2) for f in risk_factors},
                "recommended_actions": recommended_actions,
                "high_potential_score": round(high_potential_score, 3) if high_potential_score else None,
                "high_potential_factors": ["performance", "learning", "leadership"] if high_potential_score and high_potential_score > 0.7 else None,
                "model_version": "1.0",
                "created_at": datetime.utcnow(),
            }


async def generate_and_insert_data(
    employee_count: int = 5000000,
    recruitment_count: int = 500000,
    batch_size: int = 10000
) -> Dict[str, int]:
    """生成数据并批量插入 MongoDB"""
    generator = HRDataGenerator()
    stats = {
        "departments": 0,
        "employees": 0,
        "performance_records": 0,
        "recruitment_records": 0,
        "risk_assessments": 0,
    }
    
    # 生成部门
    departments = generator.generate_departments()
    await mongodb.departments.delete_many({})
    await mongodb.departments.insert_many(departments)
    stats["departments"] = len(departments)
    logger.info(f"Inserted {stats['departments']} departments")
    
    # 生成员工（批量）
    await mongodb.employees.delete_many({})
    employee_batch = []
    employee_ids = []
    
    for employee in generator.generate_employees(employee_count):
        employee_batch.append(employee)
        employee_ids.append(employee["employee_id"])
        
        if len(employee_batch) >= batch_size:
            await mongodb.employees.insert_many(employee_batch, ordered=False)
            stats["employees"] += len(employee_batch)
            employee_batch = []
    
    if employee_batch:
        await mongodb.employees.insert_many(employee_batch, ordered=False)
        stats["employees"] += len(employee_batch)
    
    logger.info(f"Inserted {stats['employees']:,} employees")
    
    # 生成绩效记录（批量）
    await mongodb.performance_records.delete_many({})
    perf_batch = []
    
    for record in generator.generate_performance_records(employee_ids[:min(100000, len(employee_ids))]):
        perf_batch.append(record)
        
        if len(perf_batch) >= batch_size:
            await mongodb.performance_records.insert_many(perf_batch, ordered=False)
            stats["performance_records"] += len(perf_batch)
            perf_batch = []
    
    if perf_batch:
        await mongodb.performance_records.insert_many(perf_batch, ordered=False)
        stats["performance_records"] += len(perf_batch)
    
    logger.info(f"Inserted {stats['performance_records']:,} performance records")
    
    # 生成招聘记录（批量）
    await mongodb.recruitment_records.delete_many({})
    recruit_batch = []
    
    for record in generator.generate_recruitment_records(recruitment_count):
        recruit_batch.append(record)
        
        if len(recruit_batch) >= batch_size:
            await mongodb.recruitment_records.insert_many(recruit_batch, ordered=False)
            stats["recruitment_records"] += len(recruit_batch)
            recruit_batch = []
    
    if recruit_batch:
        await mongodb.recruitment_records.insert_many(recruit_batch, ordered=False)
        stats["recruitment_records"] += len(recruit_batch)
    
    logger.info(f"Inserted {stats['recruitment_records']:,} recruitment records")
    
    # 生成风险评估（批量）
    await mongodb.risk_assessments.delete_many({})
    risk_batch = []
    
    for record in generator.generate_risk_assessments(employee_ids[:min(100000, len(employee_ids))]):
        risk_batch.append(record)
        
        if len(risk_batch) >= batch_size:
            await mongodb.risk_assessments.insert_many(risk_batch, ordered=False)
            stats["risk_assessments"] += len(risk_batch)
            risk_batch = []
    
    if risk_batch:
        await mongodb.risk_assessments.insert_many(risk_batch, ordered=False)
        stats["risk_assessments"] += len(risk_batch)
    
    logger.info(f"Inserted {stats['risk_assessments']:,} risk assessments")
    
    return stats


# CLI 入口
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate HR mock data")
    parser.add_argument("--count", type=int, default=5000000, help="Number of employees to generate")
    parser.add_argument("--uri", type=str, default="mongodb://localhost:27017", help="MongoDB URI")
    parser.add_argument("--database", type=str, default="hr_analytics", help="Database name")
    args = parser.parse_args()
    
    async def main():
        from .mongodb import init_mongodb, close_mongodb
        
        await init_mongodb(uri=args.uri, database=args.database)
        
        logger.info(f"Starting data generation: {args.count:,} employees")
        stats = await generate_and_insert_data(
            employee_count=args.count,
            recruitment_count=args.count // 10,
        )
        
        logger.info(f"Data generation complete: {stats}")
        await close_mongodb()
    
    asyncio.run(main())
