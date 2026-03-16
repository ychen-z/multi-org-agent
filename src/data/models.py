"""
HR 数据模型定义
使用 Pydantic 进行数据验证
"""

from datetime import datetime, date
from enum import Enum
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, field_validator


# ============ 枚举定义 ============

class Gender(str, Enum):
    MALE = "M"
    FEMALE = "F"
    OTHER = "O"


class EmployeeStatus(str, Enum):
    ACTIVE = "active"
    RESIGNED = "resigned"
    TERMINATED = "terminated"
    ON_LEAVE = "on_leave"


class PerformanceRating(str, Enum):
    S = "S"  # 超出预期
    A = "A"  # 优秀
    B = "B"  # 符合预期
    C = "C"  # 需改进
    D = "D"  # 不符合预期


class RecruitmentStage(str, Enum):
    RESUME = "resume"
    SCREENING = "screening"
    FIRST_INTERVIEW = "first_interview"
    SECOND_INTERVIEW = "second_interview"
    FINAL_INTERVIEW = "final_interview"
    OFFER = "offer"
    OFFER_ACCEPTED = "offer_accepted"
    OFFER_REJECTED = "offer_rejected"
    HIRED = "hired"
    WITHDRAWN = "withdrawn"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Education(str, Enum):
    HIGH_SCHOOL = "high_school"
    ASSOCIATE = "associate"
    BACHELOR = "bachelor"
    MASTER = "master"
    PHD = "phd"


# ============ 基础模型 ============

class Salary(BaseModel):
    """薪资结构"""
    base: float = Field(..., description="基本工资")
    bonus: float = Field(default=0, description="绩效奖金")
    allowance: float = Field(default=0, description="补贴")
    total: float = Field(default=0, description="总包")
    
    def model_post_init(self, __context):
        if self.total == 0:
            object.__setattr__(self, 'total', self.base + self.bonus + self.allowance)


class StageHistory(BaseModel):
    """招聘阶段历史"""
    stage: RecruitmentStage
    timestamp: datetime
    notes: Optional[str] = None


# ============ 主要数据模型 ============

class Employee(BaseModel):
    """员工模型"""
    employee_id: str = Field(..., description="员工工号")
    name: str = Field(..., description="姓名")
    gender: Gender = Field(..., description="性别")
    birth_date: date = Field(..., description="出生日期")
    hire_date: date = Field(..., description="入职日期")
    
    # 组织信息
    department_id: str = Field(..., description="部门ID")
    position_id: str = Field(..., description="职位ID")
    position_name: str = Field(default="", description="职位名称")
    level: str = Field(..., description="职级")
    manager_id: Optional[str] = Field(None, description="直属上级ID")
    
    # 状态
    status: EmployeeStatus = Field(default=EmployeeStatus.ACTIVE)
    resignation_date: Optional[date] = Field(None, description="离职日期")
    
    # 薪资
    salary: Salary
    
    # 教育背景
    education: Education = Field(default=Education.BACHELOR)
    major: Optional[str] = None
    
    # 联系方式
    email: Optional[str] = None
    phone: Optional[str] = None
    
    # 元数据
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def age(self) -> int:
        """计算年龄"""
        today = date.today()
        return today.year - self.birth_date.year - (
            (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
        )
    
    @property
    def tenure_years(self) -> float:
        """计算司龄(年)"""
        end_date = self.resignation_date or date.today()
        delta = end_date - self.hire_date
        return delta.days / 365.25


class Department(BaseModel):
    """部门模型"""
    department_id: str = Field(..., description="部门ID")
    name: str = Field(..., description="部门名称")
    parent_id: Optional[str] = Field(None, description="上级部门ID")
    level: int = Field(default=1, description="部门层级")
    
    # 编制
    headcount_budget: int = Field(default=0, description="编制人数")
    headcount_actual: int = Field(default=0, description="实际人数")
    
    # 负责人
    head_id: Optional[str] = Field(None, description="部门负责人ID")
    
    # 元数据
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def headcount_utilization(self) -> float:
        """编制使用率"""
        if self.headcount_budget == 0:
            return 0
        return self.headcount_actual / self.headcount_budget


class PerformanceRecord(BaseModel):
    """绩效记录"""
    employee_id: str = Field(..., description="员工ID")
    period: str = Field(..., description="考核周期，如 2024-H1")
    
    # 评级
    rating: PerformanceRating = Field(..., description="绩效等级")
    rating_score: float = Field(default=0, ge=0, le=100, description="绩效分数")
    
    # OKR
    okr_score: float = Field(default=0, ge=0, le=1, description="OKR完成度")
    okr_details: Optional[List[Dict[str, Any]]] = Field(None, description="OKR详情")
    
    # 评审
    reviewer_id: str = Field(..., description="评审人ID")
    self_review: Optional[str] = Field(None, description="自评")
    manager_review: Optional[str] = Field(None, description="上级评语")
    
    # 元数据
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RecruitmentRecord(BaseModel):
    """招聘记录"""
    requisition_id: str = Field(..., description="招聘需求ID")
    position_id: str = Field(..., description="职位ID")
    position_name: str = Field(default="", description="职位名称")
    department_id: str = Field(..., description="部门ID")
    
    # 渠道
    channel: str = Field(..., description="招聘渠道")
    channel_cost: float = Field(default=0, description="渠道成本")
    
    # 候选人
    candidate_name: str = Field(..., description="候选人姓名")
    candidate_email: Optional[str] = None
    candidate_phone: Optional[str] = None
    
    # 状态
    stage: RecruitmentStage = Field(default=RecruitmentStage.RESUME)
    stage_history: List[StageHistory] = Field(default_factory=list)
    
    # 结果
    hired_employee_id: Optional[str] = Field(None, description="入职后的员工ID")
    
    # 时间
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def days_in_pipeline(self) -> int:
        """在招聘流程中的天数"""
        return (datetime.utcnow() - self.created_at).days


class RiskAssessment(BaseModel):
    """风险评估记录"""
    employee_id: str = Field(..., description="员工ID")
    assessment_date: datetime = Field(default_factory=datetime.utcnow)
    
    # 离职风险
    turnover_risk_score: float = Field(..., ge=0, le=1, description="离职风险评分")
    risk_level: RiskLevel = Field(..., description="风险等级")
    
    # 风险因素
    risk_factors: List[str] = Field(default_factory=list, description="风险因素")
    factor_weights: Optional[Dict[str, float]] = Field(None, description="因素权重")
    
    # 建议行动
    recommended_actions: List[str] = Field(default_factory=list)
    
    # 高潜评估
    high_potential_score: Optional[float] = Field(None, ge=0, le=1)
    high_potential_factors: Optional[List[str]] = None
    
    # 元数据
    model_version: str = Field(default="1.0")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AnalyticsCache(BaseModel):
    """分析结果缓存"""
    analysis_type: str = Field(..., description="分析类型")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="分析参数")
    result: Dict[str, Any] = Field(..., description="分析结果")
    expires_at: datetime = Field(..., description="过期时间")
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ============ 分析结果模型 ============

class RecruitmentChannelMetrics(BaseModel):
    """招聘渠道指标"""
    channel: str
    total_cost: float
    resume_count: int
    interview_count: int
    offer_count: int
    hired_count: int
    cost_per_hire: float
    conversion_rate: float
    avg_time_to_hire: float


class PerformanceDistribution(BaseModel):
    """绩效分布"""
    period: str
    total_count: int
    distribution: Dict[str, int]  # rating -> count
    average_score: float
    by_department: Optional[Dict[str, Dict[str, int]]] = None


class TurnoverRiskSummary(BaseModel):
    """离职风险摘要"""
    total_employees: int
    high_risk_count: int
    critical_risk_count: int
    avg_risk_score: float
    top_risk_factors: List[Dict[str, Any]]
    by_department: Dict[str, Dict[str, int]]


class OrgHealthMetrics(BaseModel):
    """组织健康指标"""
    revenue_per_employee: float
    profit_per_employee: float
    labor_cost_ratio: float
    avg_tenure_years: float
    turnover_rate: float
    avg_age: float
    headcount_utilization: float
    management_span: float
    org_depth: int
