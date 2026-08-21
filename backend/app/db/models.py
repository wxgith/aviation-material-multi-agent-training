from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class LearnerProfileORM(Base):
    __tablename__ = "learners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    profile_type: Mapped[str] = mapped_column(String(200))
    background: Mapped[str] = mapped_column(Text)
    characteristics: Mapped[str] = mapped_column(Text, default="")
    learning_goal: Mapped[str] = mapped_column(Text)
    level: Mapped[str] = mapped_column(String(40))
    recommended_domains: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DiagnosisRecordORM(Base):
    __tablename__ = "diagnosis_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(80), index=True)
    profile_id: Mapped[str] = mapped_column(String(80), index=True)
    domain: Mapped[str] = mapped_column(String(40), index=True)
    score: Mapped[int] = mapped_column(Integer)
    level: Mapped[str] = mapped_column(String(80))
    weak_points: Mapped[str] = mapped_column(Text)
    strong_points: Mapped[str] = mapped_column(Text)
    diagnosis_summary: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AgentSessionORM(Base):
    __tablename__ = "agent_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    profile_id: Mapped[str] = mapped_column(String(80), index=True)
    domain: Mapped[str] = mapped_column(String(40), index=True)
    learning_goal: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="completed")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AgentStepORM(Base):
    __tablename__ = "agent_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(80), index=True)
    agent_name: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(Text)
    input_summary: Mapped[str] = mapped_column(Text)
    output_summary: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40))
    confidence: Mapped[float] = mapped_column(Float)
    evidence_ids: Mapped[str] = mapped_column(Text)
    details: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class GeneratedResourceORM(Base):
    __tablename__ = "generated_resources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(80), index=True)
    personalized_lecture: Mapped[str] = mapped_column(Text)
    practical_guide: Mapped[str] = mapped_column(Text)
    graded_quiz: Mapped[str] = mapped_column(Text)
    case_task: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class LearningReportORM(Base):
    __tablename__ = "learning_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(80), index=True)
    report_markdown: Mapped[str] = mapped_column(Text)
    weak_points: Mapped[str] = mapped_column(Text)
    learning_path: Mapped[str] = mapped_column(Text)
    next_training_plan: Mapped[str] = mapped_column(Text)
    review_comments: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FeedbackRecordORM(Base):
    __tablename__ = "feedback_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(80), index=True)
    feedback_score: Mapped[int] = mapped_column(Integer)
    self_feedback: Mapped[str] = mapped_column(Text)
    next_action: Mapped[str] = mapped_column(String(100))
    explanation: Mapped[str] = mapped_column(Text)
    updated_learning_path: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class LearningInteractionORM(Base):
    __tablename__ = "learning_interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    interaction_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    session_id: Mapped[str] = mapped_column(String(80), index=True)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    evidence_ids: Mapped[str] = mapped_column(Text)
    retrieval_mode: Mapped[str] = mapped_column(String(80))
    knowledge_source: Mapped[str] = mapped_column(String(100))
    generation_mode: Mapped[str] = mapped_column(String(80))
    review_status: Mapped[str] = mapped_column(String(100))
    next_action: Mapped[str] = mapped_column(String(100))
    payload: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AsyncTaskORM(Base):
    __tablename__ = "async_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    task_type: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(String(40), index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str] = mapped_column(Text, default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    current_agent: Mapped[str] = mapped_column(String(200), default="")
    step_index: Mapped[int] = mapped_column(Integer, default=0)
    total_steps: Mapped[int] = mapped_column(Integer, default=0)
    created_at_text: Mapped[str] = mapped_column(Text, default="")
    started_at_text: Mapped[str] = mapped_column(Text, default="")
    completed_at_text: Mapped[str] = mapped_column(Text, default="")
    updated_at_text: Mapped[str] = mapped_column(Text, default="")
    elapsed_ms: Mapped[int] = mapped_column(Integer, default=0)
    step_timings: Mapped[str] = mapped_column(Text, default="[]")
    result_payload: Mapped[str] = mapped_column(Text, default="null")
    error: Mapped[str] = mapped_column(Text, default="")
    metadata_payload: Mapped[str] = mapped_column(Text, default="{}")
    request_payload: Mapped[str] = mapped_column(Text, default="{}")
    events_payload: Mapped[str] = mapped_column(Text, default="[]")
    retry_of: Mapped[str] = mapped_column(String(80), default="", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
