from typing import Any, Literal

from pydantic import BaseModel, Field


TrainingDomain = Literal["tire", "brake", "composite"]
LearnerLevel = Literal["低", "中", "高"]
AgentStatus = Literal["completed", "running", "pending", "failed"]
NextAction = Literal["降维解释", "继续巩固", "补充案例", "进阶挑战"]


class LearnerProfile(BaseModel):
    profile_id: str
    name: str
    learner_type: str
    background: str
    characteristics: str
    default_goal: str
    self_level: LearnerLevel
    recommended_domains: list[TrainingDomain] = Field(default_factory=list)


class DomainInfo(BaseModel):
    domain: TrainingDomain
    title: str
    summary: str


class Question(BaseModel):
    id: str
    domain: TrainingDomain
    question: str
    options: list[str]
    answer: str
    knowledge_point: str
    difficulty: str
    explanation: str


class AnswerSubmission(BaseModel):
    question_id: str
    answer: str


class DiagnosisSubmitRequest(BaseModel):
    profile_id: str
    domain: TrainingDomain
    answers: list[AnswerSubmission] = Field(default_factory=list)
    profile_override: LearnerProfile | None = None


class QuestionDiagnosisDetail(BaseModel):
    question_id: str
    knowledge_point: str
    correct: bool
    learner_answer: str | None = None
    correct_answer: str
    explanation: str


class DiagnosisResult(BaseModel):
    profile_id: str
    domain: TrainingDomain
    score: int
    level: str
    weak_points: list[str]
    strong_points: list[str]
    diagnosis_summary: str
    details: list[QuestionDiagnosisDetail] = Field(default_factory=list)


class AgentStep(BaseModel):
    agent_name: str
    role: str
    input_summary: str
    output_summary: str
    status: AgentStatus = "completed"
    confidence: float = Field(ge=0, le=1)
    evidence_ids: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class AgentRunRequest(BaseModel):
    profile_id: str
    domain: TrainingDomain
    diagnosis_result: DiagnosisResult
    learning_goal: str
    profile_override: LearnerProfile | None = None


class AgentRunResponse(BaseModel):
    session_id: str
    agent_steps: list[AgentStep]


class FeedbackRequest(BaseModel):
    answers: list[AnswerSubmission] = Field(default_factory=list)
    self_feedback: str = ""


class FeedbackResponse(BaseModel):
    feedback_score: int
    next_action: NextAction
    explanation: str
    updated_learning_path: list[str]
    updated_resources: dict[str, Any] | None = None
    iteration_agent_steps: list[AgentStep] = Field(default_factory=list)


class GuidedInquiryRequest(BaseModel):
    question: str = Field(min_length=5, max_length=800)


class GuidedInquiryResponse(BaseModel):
    interaction_id: str
    session_id: str
    question: str
    answer: str
    explanation_level: str
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_titles: list[str] = Field(default_factory=list)
    evidence_snippets: list[dict[str, str]] = Field(default_factory=list)
    boundaries: list[str] = Field(default_factory=list)
    follow_up_question: str
    practice_task: str
    next_action: str
    generation_mode: str
    generation_audit: dict[str, Any] = Field(default_factory=dict)
    retrieval_mode: str
    knowledge_source: str
    review: dict[str, Any] = Field(default_factory=dict)
    agent_steps: list[AgentStep] = Field(default_factory=list)


class InterfaceAssistantContext(BaseModel):
    active_view: str = "home"
    active_view_label: str = "首页"
    domain: TrainingDomain = "tire"
    profile_id: str | None = None
    learner_type: str = ""
    learning_goal: str = ""
    diagnosis_score: int | None = None
    diagnosis_level: str = ""
    feedback_score: int | None = None
    weak_points: list[str] = Field(default_factory=list)
    strong_points: list[str] = Field(default_factory=list)
    session_id: str | None = None
    recommended_action: str = ""
    next_training_suggestion: str = ""
    visible_summary: str = Field(default="", max_length=1600)
    recent_messages: list[dict[str, str]] = Field(default_factory=list, max_length=6)


class InterfaceAssistantRequest(BaseModel):
    question: str = Field(min_length=2, max_length=800)
    context: InterfaceAssistantContext = Field(default_factory=InterfaceAssistantContext)


class InterfaceAssistantResponse(BaseModel):
    answer: str
    answer_type: str
    context_summary: str
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_titles: list[str] = Field(default_factory=list)
    boundaries: list[str] = Field(default_factory=list)
    suggested_questions: list[str] = Field(default_factory=list)
    recommended_view: str | None = None
    generation_mode: str
    knowledge_source: str
    agent_steps: list[AgentStep] = Field(default_factory=list)


class LegacyDiagnosticRequest(BaseModel):
    profile: dict[str, Any]
    answers: list[AnswerSubmission] = Field(default_factory=list)
