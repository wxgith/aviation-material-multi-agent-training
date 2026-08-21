import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  BarChart3,
  Bot,
  BookOpen,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  CircleGauge,
  Clock3,
  ClipboardCheck,
  Cpu,
  Database,
  Download,
  FileText,
  Flame,
  FlaskConical,
  GitBranch,
  House,
  History,
  Layers3,
  Library,
  Lightbulb,
  MessageSquare,
  Maximize2,
  Minus,
  Network,
  PanelRightClose,
  PanelRightOpen,
  Play,
  RefreshCw,
  RotateCcw,
  ScanSearch,
  Search,
  Send,
  Server,
  ShieldCheck,
  Sparkles,
  Target,
  Trash2,
  UserPlus,
  UserRound,
  Workflow,
  Wrench,
  X,
} from "lucide-react";
import { api } from "./api/client";
import "./styles/app.css";

const domainLabels = {
  tire: "航空轮胎",
  brake: "航空刹车片",
  composite: "复合材料板",
};

const views = [
  { id: "home", label: "首页", icon: House },
  { id: "knowledge", label: "知识证据库", icon: Library },
  { id: "history", label: "历史训练会话", icon: History },
  { id: "profile", label: "画像输入", icon: UserRound },
  { id: "diagnosis", label: "学情诊断", icon: ClipboardCheck },
  { id: "agents", label: "多智能体协同", icon: Network },
  { id: "resources", label: "资源生成", icon: BookOpen },
  { id: "inquiry", label: "智能训练工作台", icon: MessageSquare },
  { id: "report", label: "学情报告", icon: BarChart3 },
  { id: "feedback", label: "反馈迭代", icon: RefreshCw },
];

const navigationGroups = [
  { label: "系统总览", ids: ["home", "knowledge", "history"] },
  { label: "训练闭环", ids: ["profile", "diagnosis", "agents", "resources", "inquiry", "report", "feedback"] },
];

const workflowSteps = [
  ["画像", UserRound],
  ["诊断", ClipboardCheck],
  ["路由", GitBranch],
  ["检索", ScanSearch],
  ["生成", Sparkles],
  ["审核", ShieldCheck],
  ["决策", BarChart3],
  ["反馈", RefreshCw],
];

const agentOverviewLabels = ["学情诊断", "材料路由", "专业检索", "资源生成", "审核纠偏", "路径决策"];

const domainIcons = {
  tire: CircleGauge,
  brake: Flame,
  composite: Layers3,
};

const ACTIVE_TASK_STORAGE_KEY = "aviation-training-active-task";
const ASSISTANT_HISTORY_STORAGE_KEY = "aviation-training-assistant-history";
const ASSISTANT_HISTORY_TTL = 24 * 60 * 60 * 1000;

const assistantWelcomeMessage = {
  id: "assistant-welcome",
  role: "assistant",
  answer: "我可以结合当前页面、训练方向、学习者画像和已有会话，解释系统操作或回答材料损伤问题。",
  answer_type: "welcome",
  evidence_ids: [],
  evidence_titles: [],
  boundaries: [],
  suggested_questions: ["我第一次使用应该从哪里开始？", "三个训练方向有什么区别？"],
};

function readAssistantMessages(sessionId) {
  if (!sessionId) return [assistantWelcomeMessage];
  try {
    const saved = JSON.parse(window.localStorage.getItem(ASSISTANT_HISTORY_STORAGE_KEY) || "null");
    if (!saved?.saved_at || Date.now() - saved.saved_at > ASSISTANT_HISTORY_TTL || !saved.sessions) {
      window.localStorage.removeItem(ASSISTANT_HISTORY_STORAGE_KEY);
      return [assistantWelcomeMessage];
    }
    const messages = saved.sessions[sessionId];
    if (!Array.isArray(messages)) return [assistantWelcomeMessage];
    return [assistantWelcomeMessage, ...messages.filter((item) => item?.id !== assistantWelcomeMessage.id).slice(-24)];
  } catch {
    window.localStorage.removeItem(ASSISTANT_HISTORY_STORAGE_KEY);
    return [assistantWelcomeMessage];
  }
}

function persistAssistantMessages(messages, sessionId) {
  if (!sessionId) return;
  try {
    const current = JSON.parse(window.localStorage.getItem(ASSISTANT_HISTORY_STORAGE_KEY) || "null");
    const sessions = current?.sessions && Date.now() - (current.saved_at || 0) <= ASSISTANT_HISTORY_TTL
      ? current.sessions
      : {};
    window.localStorage.setItem(ASSISTANT_HISTORY_STORAGE_KEY, JSON.stringify({
      saved_at: Date.now(),
      sessions: {
        ...sessions,
        [sessionId]: messages.filter((item) => item.id !== assistantWelcomeMessage.id).slice(-24),
      },
    }));
  } catch {
    // The assistant remains usable when browser storage is restricted.
  }
}

function clearStoredAssistantMessages(sessionId) {
  try {
    if (!sessionId) return;
    const current = JSON.parse(window.localStorage.getItem(ASSISTANT_HISTORY_STORAGE_KEY) || "null");
    if (!current?.sessions?.[sessionId]) return;
    const sessions = { ...current.sessions };
    delete sessions[sessionId];
    window.localStorage.setItem(ASSISTANT_HISTORY_STORAGE_KEY, JSON.stringify({
      saved_at: Date.now(),
      sessions,
    }));
  } catch {
    // Nothing to clear when browser storage is unavailable.
  }
}

function repairInlineExperimentTable(value) {
  const source = String(value || "");
  const number = "[+-]?(?:\\d+(?:\\.\\d+)?|\\.\\d+)";
  const rowPattern = new RegExp(
    `\\|\\s*(${number})\\s*\\|\\s*([^|\\n]+?)\\s*\\|\\s*(${number})\\s*\\|\\s*(${number})\\s*\\|\\s*(${number})\\s*\\|\\s*(${number})\\s*\\|\\s*([A-Z][A-Z0-9_-]+)\\s*\\|`,
    "g",
  );
  const rows = [...source.matchAll(rowPattern)];
  if (rows.length < 2) return source;

  const fieldMatch = source.match(/记录了([^。]+?)等结构化字段/);
  const inferredHeaders = fieldMatch?.[1]
    ?.split(/[、，,]/)
    .map((item) => item.trim())
    .filter(Boolean);
  const headers = inferredHeaders?.length === 6
    ? [...inferredHeaders, "证据 ID"]
    : ["工况 1", "工况 2", "指标 1", "指标 2", "指标 3", "指标 4", "证据 ID"];
  const table = [
    `| ${headers.join(" | ")} |`,
    `| ${headers.map(() => "---").join(" | ")} |`,
    ...rows.map((row) => `| ${row.slice(1, 8).map((cell) => cell.trim()).join(" | ")} |`),
  ].join("\n");

  const firstRow = rows[0];
  const lastRow = rows.at(-1);
  const colonIndex = source.lastIndexOf("：", firstRow.index);
  const start = colonIndex >= 0 ? colonIndex + 1 : firstRow.index;
  const end = lastRow.index + lastRow[0].length;
  const remainder = source.slice(end).replace(/^\s*\|\s*/, "").trimStart();
  return `${source.slice(0, start).trimEnd()}\n\n${table}${remainder ? `\n\n${remainder}` : ""}`;
}

function repairTruncatedEvidenceRows(value) {
  return String(value || "").replace(
    /^\|\s*(.+?…\s*\[[^\]\n]+\])\s*\|?\s*$/gm,
    (_, row) => {
      const fields = row.split("|").map((field) => field.trim()).filter(Boolean);
      return `\n\n> 截断记录（字段不完整，未参与表格对齐）：${fields.join("；")}\n`;
    },
  );
}

function normalizeStructuredMarkdown(value) {
  const normalizedRows = repairInlineExperimentTable(value)
    .replace(/\r\n?/g, "\n")
    .replace(/([：:])\s*(\|(?=[^|\n]+\|))/g, "$1\n\n$2")
    .replace(/\|\s+\|(?=\s*(?:---|[^|\n]+)\s*\|)/g, "|\n|");
  return repairTruncatedEvidenceRows(normalizedRows)
    .replace(/([：:])\s*-\s+(?=`|\*\*|[\u4e00-\u9fffA-Za-z0-9])/g, "$1\n\n- ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function summarizeStructuredText(value, maxLength = 190) {
  const normalized = normalizeStructuredMarkdown(value);
  const lead = normalized.split(/\n\s*(?:证据链|个性化讲解)[：:]/)[0] || normalized;
  const plain = lead
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/^[-*+]\s+/gm, "")
    .replace(/\|?\s*:?-{3,}:?\s*\|/g, " ")
    .replace(/[|`*_>]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  return plain.length > maxLength ? `${plain.slice(0, maxLength).trim()}…` : plain;
}

function StructuredMarkdown({ children, compact = false }) {
  return (
    <div className={`structured-markdown ${compact ? "compact" : ""}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          table: ({ children: tableChildren }) => (
            <div className="markdown-table-scroll" tabIndex="0" role="region" aria-label="回答数据表格">
              <table>{tableChildren}</table>
            </div>
          ),
        }}
      >
        {normalizeStructuredMarkdown(children)}
      </ReactMarkdown>
    </div>
  );
}

function readPersistedTask() {
  try {
    const task = JSON.parse(window.localStorage.getItem(ACTIVE_TASK_STORAGE_KEY) || "null");
    if (task?.saved_at && Date.now() - task.saved_at > 30 * 60 * 1000) {
      window.localStorage.removeItem(ACTIVE_TASK_STORAGE_KEY);
      return null;
    }
    return task;
  } catch {
    window.localStorage.removeItem(ACTIVE_TASK_STORAGE_KEY);
    return null;
  }
}

function persistTask(taskId, kind) {
  try {
    window.localStorage.setItem(ACTIVE_TASK_STORAGE_KEY, JSON.stringify({
      task_id: taskId,
      kind,
      saved_at: Date.now(),
    }));
  } catch {
    // Task execution remains available when browser storage is restricted.
  }
}

function clearPersistedTask(taskId) {
  try {
    const current = readPersistedTask();
    if (!taskId || current?.task_id === taskId) window.localStorage.removeItem(ACTIVE_TASK_STORAGE_KEY);
  } catch {
    // Nothing to clear when browser storage is unavailable.
  }
}

function App() {
  const [health, setHealth] = useState(null);
  const [evaluationSummary, setEvaluationSummary] = useState(null);
  const [profiles, setProfiles] = useState([]);
  const [domains, setDomains] = useState([]);
  const [demoSessions, setDemoSessions] = useState([]);
  const [knowledgeCatalog, setKnowledgeCatalog] = useState(null);
  const [literatureExperiments, setLiteratureExperiments] = useState(null);
  const [profile, setProfile] = useState(null);
  const [domain, setDomain] = useState("tire");
  const [learningGoal, setLearningGoal] = useState("");
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState({});
  const [diagnosis, setDiagnosis] = useState(null);
  const [agentRun, setAgentRun] = useState(null);
  const [resources, setResources] = useState(null);
  const [report, setReport] = useState(null);
  const [feedbackAnswers, setFeedbackAnswers] = useState({});
  const [feedbackResult, setFeedbackResult] = useState(null);
  const [inquiryHistory, setInquiryHistory] = useState([]);
  const [recentSessions, setRecentSessions] = useState([]);
  const [taskState, setTaskState] = useState(null);
  const [pendingDemo, setPendingDemo] = useState(null);
  const [demoMessage, setDemoMessage] = useState("");
  const [activeView, setActiveView] = useState("home");
  const [assistantOpen, setAssistantOpen] = useState(false);
  const [assistantMessages, setAssistantMessages] = useState([assistantWelcomeMessage]);
  const [assistantTask, setAssistantTask] = useState(null);
  const [assistantLoading, setAssistantLoading] = useState(false);
  const [assistantError, setAssistantError] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState(null);
  const preserveSessionOnDomainChange = useRef(false);
  const resumeAttempted = useRef(false);

  useEffect(() => {
    Promise.all([
      api.health(),
      api.profiles(),
      api.domains(),
      api.demoSessions(),
      api.knowledgeSources(),
      api.literatureExperiments(),
      api.evaluationSummary(),
    ])
      .then(([healthData, profileData, domainData, demoData, catalogData, experimentData, evaluationData]) => {
        setHealth(healthData);
        setEvaluationSummary(evaluationData);
        setProfiles(profileData);
        setDomains(domainData);
        setDemoSessions(demoData);
        setKnowledgeCatalog(catalogData);
        setLiteratureExperiments(experimentData);
        const firstProfile = profileData[0];
        if (firstProfile) {
          setProfile(firstProfile);
          setLearningGoal(firstProfile.default_goal);
          setDomain(firstProfile.recommended_domains?.[0] || "tire");
        }
      })
      .catch((err) => setError(`后端接口不可用：${err.message}`));
  }, []);

  useEffect(() => {
    if (!domain) return;
    const preserveCurrentSession = preserveSessionOnDomainChange.current;
    preserveSessionOnDomainChange.current = false;
    api.questions(domain)
      .then((data) => {
        setQuestions(data);
        if (pendingDemo?.domain === domain) {
          setAnswers(toAnswerMap(pendingDemo.diagnosis_answers));
          setPendingDemo(null);
        } else if (!preserveCurrentSession) {
          setAnswers({});
        }
        if (!preserveCurrentSession) {
          setDiagnosis(null);
          setAgentRun(null);
          setResources(null);
          setReport(null);
          setFeedbackResult(null);
          setInquiryHistory([]);
        }
      })
      .catch((err) => setError(`诊断题加载失败：${err.message}`));
  }, [domain]);

  useEffect(() => {
    window.scrollTo(0, 0);
    document.title = `${views.find((item) => item.id === activeView)?.label || "系统"} | 航空材料损伤智能训练系统`;
  }, [activeView]);

  useEffect(() => {
    if (!notice) return undefined;
    const timer = window.setTimeout(() => setNotice(null), 3600);
    return () => window.clearTimeout(timer);
  }, [notice]);

  const hasRunningTask = assistantLoading || loading;

  useEffect(() => {
    if (!hasRunningTask) return undefined;
    const warnBeforeLeaving = (event) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warnBeforeLeaving);
    return () => window.removeEventListener("beforeunload", warnBeforeLeaving);
  }, [hasRunningTask]);

  useEffect(() => {
    persistAssistantMessages(assistantMessages, agentRun?.session_id);
  }, [assistantMessages, agentRun?.session_id]);

  useEffect(() => {
    if (activeView !== "inquiry" || !agentRun?.session_id) return;
    api.inquiries(agentRun.session_id)
      .then((data) => setInquiryHistory(data.items || []))
      .catch((err) => setError(`追问历史恢复失败：${err.message}`));
  }, [activeView, agentRun?.session_id]);

  useEffect(() => {
    if (activeView !== "history") return;
    api.sessions()
      .then((data) => setRecentSessions(data.items || []))
      .catch((err) => setError(`历史会话加载失败：${err.message}`));
  }, [activeView]);

  useEffect(() => {
    if (!profiles.length || resumeAttempted.current) return;
    resumeAttempted.current = true;
    const persisted = readPersistedTask();
    if (!persisted?.task_id || !persisted?.kind) return;

    let active = true;
    async function resumeTask() {
      setLoading(true);
      setError("");
      try {
        let task = await api.task(persisted.task_id);
        if (!active) return;
        setTaskState({ ...task, kind: persisted.kind, resumed: true });
        if (["queued", "running", "cancelling"].includes(task.status)) {
          task = await waitForManagedTask(task, persisted.kind);
        }
        if (task.status === "completed") {
          const sessionId = task.result?.session_id || task.metadata?.session_id;
          if (sessionId) {
            const snapshot = await api.session(sessionId);
            if (active) {
              hydrateSessionSnapshot(snapshot, persisted.kind === "agent_run" ? "agents" : "inquiry", true);
              clearPersistedTask(task.task_id);
            }
          }
        }
      } catch (err) {
        clearPersistedTask(persisted.task_id);
        if (active) setError(`任务续接失败：${err.message}。可从历史训练会话恢复已保存结果。`);
      } finally {
        if (active) setLoading(false);
      }
    }
    resumeTask();
    return () => {
      active = false;
    };
  }, [profiles.length]);

  const workflowProgress = useMemo(() => {
    const stages = [
      [Boolean(profile), "画像就绪"],
      [Boolean(diagnosis), "诊断完成"],
      [Boolean(agentRun), "Agent 完成"],
      [Boolean(resources), "资源生成"],
      [Boolean(report), "报告生成"],
      [Boolean(feedbackResult || report?.feedback_history?.length), "反馈更新"],
    ];
    const completed = stages.filter(([done]) => done).length;
    const next = stages.find(([done]) => !done)?.[1];
    return {
      completed,
      total: stages.length,
      label: next ? `待完成：${next}` : "训练闭环已完成",
    };
  }, [profile, diagnosis, agentRun, resources, report, feedbackResult]);

  const completedViewIds = useMemo(() => new Set([
    ...(profile ? ["profile"] : []),
    ...(diagnosis ? ["diagnosis"] : []),
    ...(agentRun ? ["agents"] : []),
    ...(resources ? ["resources"] : []),
    ...(inquiryHistory.length ? ["inquiry"] : []),
    ...(report ? ["report"] : []),
    ...(feedbackResult || report?.feedback_history?.length ? ["feedback"] : []),
  ]), [profile, diagnosis, agentRun, resources, inquiryHistory.length, report, feedbackResult]);

  function showNotice(message, detail = "") {
    setNotice({ id: Date.now(), message, detail });
  }

  function invalidateTrainingState({ clearAnswers = true, clearDemo = true } = {}) {
    if (clearAnswers) setAnswers({});
    setDiagnosis(null);
    setAgentRun(null);
    setResources(null);
    setReport(null);
    setFeedbackAnswers({});
    setFeedbackResult(null);
    setInquiryHistory([]);
    setTaskState(null);
    clearPersistedTask();
    setAssistantMessages([assistantWelcomeMessage]);
    setAssistantTask(null);
    setAssistantError("");
    if (clearDemo) {
      setPendingDemo(null);
      setDemoMessage("");
    }
  }

  const assistantContext = useMemo(() => ({
    active_view: activeView,
    active_view_label: views.find((item) => item.id === activeView)?.label || activeView,
    domain,
    profile_id: profile?.profile_id || null,
    learner_type: profile?.learner_type || "",
    learning_goal: learningGoal,
    diagnosis_score: diagnosis?.score ?? null,
    diagnosis_level: diagnosis?.level || "",
    feedback_score: feedbackResult?.feedback_score
      ?? report?.feedback_history?.at(-1)?.feedback_score
      ?? null,
    weak_points: diagnosis?.weak_points || [],
    strong_points: diagnosis?.strong_points || [],
    session_id: agentRun?.session_id || null,
    recommended_action: feedbackResult?.next_action || report?.recommended_action || "",
    next_training_suggestion: feedbackResult?.explanation || report?.next_training_suggestion || "",
    visible_summary: buildAssistantVisibleSummary({
      activeView,
      health,
      questions,
      answers,
      diagnosis,
      agentRun,
      resources,
      report,
      feedbackResult,
    }),
    recent_messages: assistantMessages
      .filter((item) => item.id !== assistantWelcomeMessage.id)
      .slice(-4)
      .map((item) => ({ role: item.role, content: item.answer })),
  }), [activeView, domain, profile, learningGoal, diagnosis, agentRun, health, questions, answers, resources, report, feedbackResult, assistantMessages]);

  async function askInterfaceAssistant(question) {
    const normalizedQuestion = question.trim();
    if (normalizedQuestion.length < 2 || assistantLoading) return;
    setAssistantError("");
    setAssistantMessages((current) => [
      ...current,
      { id: `user-${Date.now()}`, role: "user", answer: normalizedQuestion },
    ]);
    setAssistantLoading(true);
    try {
      const task = await api.startAssistantTask({ question: normalizedQuestion, context: assistantContext });
      setAssistantTask(task);
      const completedTask = await api.waitForTask(task.task_id, (event) => {
        setAssistantTask((current) => ({ ...current, ...event }));
      });
      if (["cancelled", "interrupted"].includes(completedTask.status)) {
        setAssistantTask(completedTask);
        setAssistantError(completedTask.status === "interrupted"
          ? "后端重启中断了本次回答，请重新发送问题。"
          : "本次回答已停止，可以修改问题后重新发送。");
        return;
      }
      if (completedTask.status !== "completed") {
        throw new Error(completedTask.error || "智能助手任务未完成");
      }
      setAssistantMessages((current) => [
        ...current,
        { id: `assistant-${Date.now()}`, role: "assistant", ...completedTask.result },
      ]);
      setAssistantTask(completedTask);
    } catch (err) {
      setAssistantError(err.message || "智能助手暂时不可用");
    } finally {
      setAssistantLoading(false);
    }
  }

  async function cancelAssistantTask() {
    if (!assistantTask?.task_id || !["queued", "running"].includes(assistantTask.status)) return;
    try {
      const cancelled = await api.cancelTask(assistantTask.task_id);
      setAssistantTask((current) => ({ ...current, ...cancelled }));
    } catch (err) {
      setAssistantError(`停止任务失败：${err.message}`);
    }
  }

  function clearAssistantHistory() {
    setAssistantMessages([assistantWelcomeMessage]);
    setAssistantTask(null);
    setAssistantError("");
    clearStoredAssistantMessages(agentRun?.session_id);
  }

  function applyPreset(profileId) {
    const selected = profiles.find((item) => item.profile_id === profileId);
    if (!selected) return;
    invalidateTrainingState();
    setProfile(selected);
    setLearningGoal(selected.default_goal);
    setDomain(selected.recommended_domains?.[0] || "tire");
    setActiveView("profile");
  }

  function updateProfile(field, value) {
    if (profile?.[field] !== value) invalidateTrainingState();
    setProfile((current) => ({ ...current, [field]: value }));
    if (field === "default_goal") setLearningGoal(value);
  }

  function updateDomain(value) {
    if (value === domain) return;
    invalidateTrainingState();
    setDomain(value);
  }

  function updateLearningGoal(value) {
    if (value !== learningGoal) invalidateTrainingState();
    setLearningGoal(value);
  }

  function applyDemoAnswers() {
    const demo = demoSessions.find((item) => item.profile_id === profile?.profile_id && item.domain === domain);
    if (!demo) return;
    setAnswers(toAnswerMap(demo.diagnosis_answers));
    setDemoMessage(demo.diagnosis_performance || demo.expected_result || "");
    showNotice("演示答案已载入", "诊断题已自动填写，可以直接启动 Agent 管线。");
  }

  function loadDemoCase() {
    const demo = demoSessions[0];
    if (!demo) return;
    invalidateTrainingState();
    const selected = profiles.find((item) => item.profile_id === demo.profile_id);
    if (selected) setProfile(selected);
    setDomain(demo.domain);
    setLearningGoal(demo.learning_goal);
    setPendingDemo(demo);
    setAnswers(toAnswerMap(demo.diagnosis_answers));
    setDiagnosis(null);
    setAgentRun(null);
    setResources(null);
    setReport(null);
    setFeedbackResult(null);
    setInquiryHistory([]);
    setDemoMessage(demo.diagnosis_performance || demo.expected_result || "");
    setActiveView("diagnosis");
    showNotice("演示案例已载入", "本科生航空轮胎训练画像、目标和诊断答案已准备完成。");
  }

  function loadEngineeringRetrievalCase() {
    const demo = demoSessions.find((item) => item.domain === "tire") || demoSessions[0];
    if (!demo) return;
    invalidateTrainingState();
    const selected = profiles.find((item) => item.profile_id === "undergrad_basic")
      || profiles.find((item) => item.profile_id === demo.profile_id);
    if (selected) setProfile(selected);
    setDomain("tire");
    setLearningGoal(
      "基于 Elasticsearch 检索 60 N、160 m 圆柱-平面往复摩擦实验依据，比较磨损量、硬度与光学形貌，识别工况边界并提出复检建议。",
    );
    setPendingDemo(domain === "tire" ? null : { ...demo, domain: "tire" });
    setAnswers(toAnswerMap(demo.diagnosis_answers));
    setDiagnosis(null);
    setAgentRun(null);
    setResources(null);
    setReport(null);
    setFeedbackResult(null);
    setInquiryHistory([]);
    setDemoMessage(
      "工程检索案例：固定检索 60 N、160 m 往复摩擦工况，重点核对趋势图、代表性光学形貌、磨损量、硬度、证据 ID 与使用边界。",
    );
    setActiveView("diagnosis");
    showNotice("工程检索案例已载入", "已锁定 60 N、160 m 往复摩擦检索工况。");
  }

  async function waitForManagedTask(task, kind) {
    persistTask(task.task_id, kind);
    setTaskState({ ...task, kind });
    const finalTask = await api.waitForTask(task.task_id, (event) => {
      setTaskState((current) => ({ ...current, ...event, kind }));
    });
    setTaskState((current) => ({ ...current, ...finalTask, kind }));
    if (["cancelled", "interrupted"].includes(finalTask.status)) {
      clearPersistedTask(finalTask.task_id);
      const cancelledError = new Error(finalTask.status === "interrupted" ? "任务因后端重启中断" : "任务已由用户停止");
      cancelledError.code = "TASK_CANCELLED";
      throw cancelledError;
    }
    if (finalTask.status !== "completed") {
      throw new Error(finalTask.error || "任务执行失败，请重试或使用系统自动兜底模式。");
    }
    return finalTask.result;
  }

  async function applyAgentTaskResult(agentResult) {
    setAssistantMessages(readAssistantMessages(agentResult.session_id));
    setAssistantTask(null);
    setAssistantError("");
    setAgentRun(agentResult);
    const [resourceData, reportData] = await Promise.all([
      api.resources(agentResult.session_id),
      api.report(agentResult.session_id),
    ]);
    setResources(resourceData);
    setReport(reportData);
    setRecentSessions((current) => current.filter((item) => item.session_id !== agentResult.session_id));
    setActiveView("agents");
    showNotice("多智能体闭环运行完成", "6 个 Agent 的结论、证据和审核记录已生成。");
  }

  async function applyInquiryTaskResult(result) {
    setInquiryHistory((current) => (
      current.some((item) => item.interaction_id === result.interaction_id)
        ? current
        : [...current, result]
    ));
    const updatedReport = await api.report(result.session_id);
    setReport(updatedReport);
    return result;
  }

  async function submitDiagnosisAndRunAgents() {
    if (!profile) return;
    invalidateTrainingState({ clearAnswers: false, clearDemo: false });
    setLoading(true);
    setError("");
    try {
      const answerList = Object.entries(answers).map(([question_id, answer]) => ({ question_id, answer }));
      const diagnosisResult = await api.submitDiagnosis({
        profile_id: profile.profile_id,
        domain,
        answers: answerList,
        profile_override: profile,
      });
      setDiagnosis(diagnosisResult);

      const task = await api.startAgentTask({
        profile_id: profile.profile_id,
        domain,
        diagnosis_result: diagnosisResult,
        learning_goal: learningGoal,
        profile_override: profile,
      });
      const agentResult = await waitForManagedTask(task, "agent_run");
      await applyAgentTaskResult(agentResult);
      clearPersistedTask(task.task_id);
    } catch (err) {
      if (err.code !== "TASK_CANCELLED") setError(`闭环运行失败：${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  async function submitFeedback(selfFeedback) {
    if (!agentRun?.session_id) return;
    setLoading(true);
    setError("");
    try {
      const answerList = Object.entries(feedbackAnswers).map(([question_id, answer]) => ({ question_id, answer }));
      const result = await api.feedback(agentRun.session_id, {
        answers: answerList,
        self_feedback: selfFeedback,
      });
      setFeedbackResult(result);
      showNotice("学习路径已更新", `${result.feedback_score} 分，下一动作：${result.next_action}。`);
      if (result.updated_resources) {
        setResources(result.updated_resources);
      }
      if (result.iteration_agent_steps?.length) {
        setAgentRun((current) => ({
          ...current,
          agent_steps: [...current.agent_steps, ...result.iteration_agent_steps],
        }));
      }
      try {
        const updatedReport = await api.report(agentRun.session_id);
        setReport(updatedReport);
      } catch (refreshError) {
        setReport((current) => current ? {
          ...current,
          recommended_learning_path: result.updated_learning_path,
          recommended_action: result.next_action,
          next_training_suggestion: result.explanation,
          resource_difficulty_match: result.updated_resources?.difficulty_match || current.resource_difficulty_match,
        } : current);
        setError(`反馈已提交并完成决策更新，但学情报告刷新失败：${refreshError.message}。可重新进入学情报告页加载最新结果。`);
      }
    } catch (err) {
      setError(`反馈提交失败：${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  async function submitInquiry(question) {
    if (!agentRun?.session_id || !question.trim()) return;
    setLoading(true);
    setError("");
    try {
      const task = await api.startInquiryTask(agentRun.session_id, question.trim());
      const result = await waitForManagedTask(task, "guided_inquiry");
      const applied = await applyInquiryTaskResult(result);
      clearPersistedTask(task.task_id);
      return applied;
    } catch (err) {
      if (err.code !== "TASK_CANCELLED") setError(`动态追问失败：${err.message}`);
      return null;
    } finally {
      setLoading(false);
    }
  }

  async function cancelCurrentTask() {
    if (!taskState?.task_id || !["queued", "running", "cancelling"].includes(taskState.status)) return;
    try {
      const cancelled = await api.cancelTask(taskState.task_id);
      clearPersistedTask(taskState.task_id);
      setTaskState((current) => ({ ...current, ...cancelled }));
    } catch (err) {
      setError(`停止任务失败：${err.message}`);
    }
  }

  async function retryCurrentTask() {
    if (!taskState?.task_id || !["failed", "cancelled", "interrupted"].includes(taskState.status)) return;
    const kind = taskState.kind;
    setLoading(true);
    setError("");
    try {
      const retried = await api.retryTask(taskState.task_id);
      const result = await waitForManagedTask(retried, kind);
      if (kind === "agent_run") await applyAgentTaskResult(result);
      if (kind === "guided_inquiry") await applyInquiryTaskResult(result);
      clearPersistedTask(retried.task_id);
    } catch (err) {
      if (err.code !== "TASK_CANCELLED") setError(`任务重试失败：${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  async function restoreSession(sessionId) {
    setLoading(true);
    setError("");
    try {
      const snapshot = await api.session(sessionId);
      hydrateSessionSnapshot(snapshot, "inquiry");
      showNotice("训练会话已恢复", `会话 ${sessionId.slice(0, 8)} 的画像、资源和报告已载入。`);
    } catch (err) {
      setError(`恢复会话失败：${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  function hydrateSessionSnapshot(snapshot, targetView, keepTaskState = false) {
    const latestFeedback = snapshot.report?.feedback_history?.at(-1);
    if (snapshot.domain !== domain) preserveSessionOnDomainChange.current = true;
    setDomain(snapshot.domain);
    setProfile(snapshot.profile);
    setLearningGoal(snapshot.learning_goal);
    setDiagnosis(snapshot.diagnosis_result);
    setAgentRun({ session_id: snapshot.session_id, agent_steps: snapshot.agent_steps });
    setResources(snapshot.resources);
    setReport(snapshot.report);
    setInquiryHistory(snapshot.inquiry_history || []);
    setFeedbackAnswers({});
    setFeedbackResult(latestFeedback ? {
      feedback_score: latestFeedback.feedback_score,
      next_action: latestFeedback.next_action,
      explanation: latestFeedback.explanation || latestFeedback.self_feedback || "已恢复最近一次反馈决策。",
      updated_learning_path: latestFeedback.updated_learning_path || snapshot.report?.recommended_learning_path || [],
      restored: true,
    } : null);
    setPendingDemo(null);
    setDemoMessage("");
    setAssistantMessages(readAssistantMessages(snapshot.session_id));
    setAssistantTask(null);
    setAssistantError("");
    if (!keepTaskState) setTaskState(null);
    setActiveView(targetView);
  }

  async function exportLearningReport() {
    if (!agentRun?.session_id) return;
    setError("");
    try {
      const markdown = await api.exportReport(agentRun.session_id);
      const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `航空材料损伤训练学情报告-${agentRun.session_id}.md`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      showNotice("学情报告已导出", "Markdown 报告已下载，可使用浏览器或文档工具打印为 PDF。");
    } catch (err) {
      setError(`报告导出失败：${err.message}`);
    }
  }

  return (
    <main className="app-shell">
      <a className="skip-link" href="#main-content">跳到主要内容</a>
      <aside className="sidebar">
        <div className="brand-block">
          <div className="brand-mark"><Layers3 size={22} strokeWidth={1.8} /></div>
          <div>
            <p className="brand-kicker">AVIATION MATERIALS LAB</p>
            <h1>航空材料损伤<br />智能训练系统</h1>
          </div>
        </div>
        <nav aria-label="系统主导航">
          {navigationGroups.map((group) => (
            <div className="nav-group" key={group.label}>
              <span className="nav-group-label">{group.label}</span>
              {group.ids.map((id) => {
                const item = views.find((view) => view.id === id);
                if (!item) return null;
                const Icon = item.icon;
                return (
                  <button
                    key={id}
                    className={`${activeView === id ? "active" : ""} ${completedViewIds.has(id) ? "completed" : ""}`}
                    aria-current={activeView === id ? "page" : undefined}
                    onClick={() => setActiveView(id)}
                  >
                    <Icon size={18} strokeWidth={1.8} />
                    <span>{item.label}</span>
                    {completedViewIds.has(id) && <CheckCircle2 className="nav-complete" size={13} />}
                  </button>
                );
              })}
            </div>
          ))}
        </nav>
        <div className="progress">
          <div className="progress-copy">
            <span>闭环进度</span>
            <strong>{workflowProgress.completed} / {workflowProgress.total}</strong>
          </div>
          <div><i style={{ width: `${(workflowProgress.completed / workflowProgress.total) * 100}%` }} /></div>
          <p>{workflowProgress.label}</p>
        </div>
      </aside>

      <section className="workspace" id="main-content">
        <header className="workspace-toolbar">
          <div>
            <span>航空工程材料损伤分析</span>
            <strong>{views.find((item) => item.id === activeView)?.label}</strong>
          </div>
          <div className="workspace-toolbar-actions">
            <button
              type="button"
              className="toolbar-assistant-button"
              onClick={() => setAssistantOpen(true)}
              aria-label="打开智能问答助手"
              title="打开智能问答助手"
            >
              <Bot size={17} /><span>智能助手</span>
            </button>
            <div className={`runtime-state ${health?.database_connected && health?.es_connected ? "online" : "fallback"}`}>
              <Activity size={15} strokeWidth={2} />
              <div>
                <span>运行环境</span>
                <strong>{health?.database_connected && health?.es_connected ? "SQL + ES 工程模式" : "本地兜底模式"}</strong>
              </div>
              <i />
            </div>
          </div>
        </header>
        {error && <div className="error-banner" role="alert"><AlertTriangle size={17} /><span>{error}</span><button type="button" onClick={() => setError("")} aria-label="关闭错误提示"><X size={16} /></button></div>}
        {taskState && ["failed", "cancelled", "interrupted"].includes(taskState.status) && (
          <TaskRecoveryBanner task={taskState} loading={loading} onRetry={retryCurrentTask} />
        )}
        {activeView === "home" && (
          <Home
            health={health}
            evaluationSummary={evaluationSummary}
            domains={domains}
            knowledgeCatalog={knowledgeCatalog}
            onStart={() => setActiveView("profile")}
            onDemo={loadDemoCase}
            onEngineeringDemo={loadEngineeringRetrievalCase}
            onKnowledge={() => setActiveView("knowledge")}
            onAssistant={() => setAssistantOpen(true)}
          />
        )}
        {activeView === "knowledge" && (
          <KnowledgeLibrary catalog={knowledgeCatalog} experiments={literatureExperiments} />
        )}
        {activeView === "history" && (
          <SessionHistory
            sessions={recentSessions}
            loading={loading}
            profiles={profiles}
            onRestore={restoreSession}
          />
        )}
        {activeView === "profile" && (
          <ProfileForm
            profile={profile}
            profiles={profiles}
            domains={domains}
            domain={domain}
            learningGoal={learningGoal}
            onPreset={applyPreset}
            onChange={updateProfile}
            onDomainChange={updateDomain}
            onGoalChange={updateLearningGoal}
            onDemo={loadDemoCase}
            onNext={() => setActiveView("diagnosis")}
          />
        )}
        {activeView === "diagnosis" && (
          <Diagnosis
            health={health}
            questions={questions}
            answers={answers}
            setAnswers={setAnswers}
            diagnosis={diagnosis}
            loading={loading}
            taskState={taskState?.kind === "agent_run" ? taskState : null}
            hasDemo={demoSessions.some((item) => item.profile_id === profile?.profile_id && item.domain === domain)}
            demoMessage={demoMessage}
            onDemo={applyDemoAnswers}
            onSubmit={submitDiagnosisAndRunAgents}
            onCancel={cancelCurrentTask}
          />
        )}
        {activeView === "agents" && <Agents agentRun={agentRun} taskState={taskState} onNext={() => setActiveView("resources")} />}
        {activeView === "resources" && (
          <Resources
            resources={resources}
            onInquiry={() => setActiveView("inquiry")}
            onNext={() => setActiveView("report")}
          />
        )}
        {activeView === "inquiry" && (
          <GuidedInquiry
            sessionId={agentRun?.session_id}
            health={health}
            profile={profile}
            domain={domain}
            learningGoal={learningGoal}
            diagnosis={diagnosis}
            history={inquiryHistory}
            loading={loading}
            taskState={taskState?.kind === "guided_inquiry" ? taskState : null}
            onSubmit={submitInquiry}
            onCancel={cancelCurrentTask}
            onNext={() => setActiveView("report")}
          />
        )}
        {activeView === "report" && <Report report={report} onNext={() => setActiveView("feedback")} onExport={exportLearningReport} />}
        {activeView === "feedback" && (
          <Feedback
            health={health}
            resources={resources}
            answers={feedbackAnswers}
            setAnswers={setFeedbackAnswers}
            result={feedbackResult}
            loading={loading}
            onSubmit={submitFeedback}
          />
        )}
      </section>
      {notice && (
        <div className="success-toast" role="status" aria-live="polite" aria-atomic="true">
          <CheckCircle2 size={19} />
          <div><strong>{notice.message}</strong>{notice.detail && <span>{notice.detail}</span>}</div>
          <button type="button" aria-label="关闭成功提示" onClick={() => setNotice(null)}><X size={15} /></button>
        </div>
      )}
      <ContextAssistant
        open={assistantOpen}
        onOpen={() => setAssistantOpen(true)}
        onClose={() => setAssistantOpen(false)}
        messages={assistantMessages}
        loading={assistantLoading}
        task={assistantTask}
        error={assistantError}
        context={assistantContext}
        onSubmit={askInterfaceAssistant}
        onCancel={cancelAssistantTask}
        onClear={clearAssistantHistory}
        onNavigate={(view) => {
          if (views.some((item) => item.id === view)) setActiveView(view);
          setAssistantOpen(false);
        }}
      />
    </main>
  );
}

function toAnswerMap(answerList) {
  const nextAnswers = {};
  answerList.forEach((item) => {
    nextAnswers[item.question_id] = item.answer;
  });
  return nextAnswers;
}

function TaskRecoveryBanner({ task, loading, onRetry }) {
  const cancelled = task.status === "cancelled";
  const interrupted = task.status === "interrupted";
  return (
    <section className={`task-recovery ${cancelled || interrupted ? "cancelled" : "failed"}`} role="status">
      <div>{cancelled ? <X size={18} /> : <AlertTriangle size={18} />}</div>
      <section>
        <strong>{cancelled ? "任务已停止" : (interrupted ? "任务因后端重启中断" : "任务未完成")}</strong>
        <p>{cancelled
          ? "已保留此前完成的会话数据，可以重新运行同一任务。"
          : (interrupted ? "重启前的进度与事件已保存在 MySQL，可按原请求重新执行。" : (task.error || task.detail))}</p>
      </section>
      <button type="button" disabled={loading} onClick={onRetry}>
        <RotateCcw size={15} />重试任务
      </button>
    </section>
  );
}

function SessionHistory({ sessions, loading, profiles, onRestore }) {
  const [query, setQuery] = useState("");
  const [domainFilter, setDomainFilter] = useState("all");
  const profileName = (profileId) => profiles.find((item) => item.profile_id === profileId)?.name || profileId;
  const normalizedQuery = query.trim().toLowerCase();
  const filteredSessions = sessions.filter((item) => {
    const matchesDomain = domainFilter === "all" || item.domain === domainFilter;
    const searchable = [
      profileName(item.profile_id),
      item.learning_goal,
      item.diagnosis_level,
      item.session_id,
    ].join(" ").toLowerCase();
    return matchesDomain && (!normalizedQuery || searchable.includes(normalizedQuery));
  });
  const scoredSessions = sessions.filter((item) => Number.isFinite(Number(item.diagnosis_score)));
  const averageScore = scoredSessions.length
    ? Math.round(scoredSessions.reduce((sum, item) => sum + Number(item.diagnosis_score), 0) / scoredSessions.length)
    : 0;
  const interactionTotal = sessions.reduce((sum, item) => sum + Number(item.interaction_count || 0), 0);
  const latestSessionId = sessions[0]?.session_id;
  return (
    <div className="view history-view">
      <header className="page-intro history-page-intro">
        <div>
          <p className="eyebrow">MySQL 学习过程持久化</p>
          <h2>历史训练会话</h2>
          <p className="muted">恢复画像、诊断结果、Agent 步骤、生成资源、动态问答和学情报告。</p>
        </div>
        <div className="history-count"><Database size={16} /><strong>{filteredSessions.length}</strong><span>/ {sessions.length} 条会话</span></div>
      </header>
      <section className="history-summary" aria-label="历史训练数据摘要">
        <div><Database size={17} /><span>已保存会话</span><strong>{sessions.length}</strong></div>
        <div><CircleGauge size={17} /><span>平均诊断分</span><strong>{averageScore}</strong></div>
        <div><MessageSquare size={17} /><span>累计动态问答</span><strong>{interactionTotal} 轮</strong></div>
        <div><Clock3 size={17} /><span>最近更新</span><strong>{formatSessionTime(sessions[0]?.updated_at || sessions[0]?.created_at)}</strong></div>
      </section>
      <div className="history-tools" role="search">
        <label>
          <Search size={16} />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="搜索学习者、目标或会话 ID"
          />
        </label>
        <label>
          <FlaskConical size={16} />
          <select value={domainFilter} onChange={(event) => setDomainFilter(event.target.value)}>
            <option value="all">全部训练方向</option>
            {Object.entries(domainLabels).map(([value, label]) => <option value={value} key={value}>{label}</option>)}
          </select>
        </label>
      </div>
      {!sessions.length ? (
        <div className="history-empty"><History size={24} /><strong>暂无可恢复会话</strong><span>完成一次诊断与 Agent 管线后，会话将出现在这里。</span></div>
      ) : !filteredSessions.length ? (
        <div className="history-empty"><Search size={24} /><strong>没有匹配的训练会话</strong><span>请调整关键词或训练方向筛选条件。</span></div>
      ) : (
        <div className="session-table" role="table" aria-label="历史训练会话">
          <div className="session-table-head" role="row">
            <span>学习者与方向</span><span>诊断结果</span><span>学习目标</span><span>会话记录</span><span>操作</span>
          </div>
          {filteredSessions.map((item) => (
            <article className={item.session_id === latestSessionId ? "latest" : ""} role="row" key={item.session_id}>
              <div>
                <strong>{profileName(item.profile_id)}{item.session_id === latestSessionId && <span className="latest-label">最近</span>}</strong>
                <span className={`domain-accent ${item.domain}`}>{domainLabels[item.domain] || item.domain}</span>
                <code>{item.session_id.slice(0, 8)}</code>
              </div>
              <div><strong className="score-emphasis">{item.diagnosis_score ?? "--"}</strong><span>{item.diagnosis_level || "未记录"}</span></div>
              <p>{formatHistoryGoal(item.learning_goal)}</p>
              <div><strong>{item.interaction_count || 0} 轮问答</strong><span>{formatSessionTime(item.updated_at || item.created_at)}</span></div>
              <button type="button" disabled={loading} onClick={() => onRestore(item.session_id)}>
                <RotateCcw size={15} />恢复
              </button>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}

function formatSessionTime(value) {
  if (!value) return "当前运行会话";
  const normalizedValue = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value) ? value : `${value}Z`;
  const date = new Date(normalizedValue);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", { hour12: false });
}

function formatDuration(milliseconds) {
  const value = Math.max(0, Number(milliseconds) || 0);
  if (value < 1000) return `${Math.round(value)} ms`;
  if (value < 60000) return `${(value / 1000).toFixed(value < 10000 ? 1 : 0)} s`;
  const minutes = Math.floor(value / 60000);
  const seconds = Math.round((value % 60000) / 1000);
  return `${minutes} min ${seconds} s`;
}

function formatHistoryGoal(value) {
  const text = String(value || "").trim();
  const questionMarks = (text.match(/\?/g) || []).length;
  return !text || questionMarks > text.length * 0.6 ? "早期测试记录（文本编码不可用）" : text;
}

function buildAssistantVisibleSummary({ activeView, health, questions, answers, diagnosis, agentRun, resources, report, feedbackResult }) {
  const summaries = {
    home: `首页展示${health?.database_connected ? "MySQL" : "JSON"}数据模式、${health?.es_connected ? "Elasticsearch" : "本地"}检索和${health?.llm_configured ? (health?.llm_resource_generation_enabled ? "LLM 资源生成" : "LLM 问答 + 模板资源") : "Mock 生成"}状态。`,
    knowledge: "知识证据库页面展示来源登记、实验卡、证据 ID、切片统计与适用边界。",
    history: "历史训练会话页面用于搜索和恢复已保存的完整训练记录。",
    profile: "画像输入页面正在设置学习者类型、专业背景、训练方向、自评基础和学习目标。",
    diagnosis: `诊断页面共 ${questions.length} 道题，已选择 ${Object.keys(answers).length} 道${diagnosis ? `；当前得分 ${diagnosis.score}，薄弱点为 ${diagnosis.weak_points.join("、")}` : ""}。`,
    agents: `多智能体页面展示 ${agentRun?.agent_steps?.length || 0} 个已完成步骤，包含检索来源、证据 ID、生成与审核结果。`,
    resources: `资源页面正在展示${resources?.personalized_lecture?.title || "个性化讲义、实操指南、测试题和案例任务"}。`,
    inquiry: "智能训练工作台支持基于当前会话进行证据约束的多轮追问。",
    report: `学情报告页面展示${report?.weak_points?.length || diagnosis?.weak_points?.length || 0} 个知识薄弱点、学习路径、审核意见和训练建议。`,
    feedback: `反馈迭代页面用于提交巩固测试${feedbackResult ? `；当前决策为 ${feedbackResult.next_action}` : "并动态更新下一动作"}。`,
  };
  return summaries[activeView] || "当前处于航空工程材料损伤训练系统。";
}

function Home({ health, evaluationSummary, domains, knowledgeCatalog, onStart, onDemo, onEngineeringDemo, onKnowledge, onAssistant }) {
  const evaluationPassed = (evaluationSummary?.core_cases?.passed || 0)
    + (evaluationSummary?.guided_inquiry?.passed || 0);
  const evaluationTotal = (evaluationSummary?.core_cases?.total || 0)
    + (evaluationSummary?.guided_inquiry?.total || 0);
  return (
    <div className="view home-view">
      <div
        className="hero"
        style={{ "--hero-image": `url("${api.evidenceMediaUrl("RXQ-IMG-D000-S15-SEM-01")}")` }}
      >
        <div className="hero-shade" />
        <div className="hero-content">
          <div className="hero-proof"><FlaskConical size={16} /> 真实实验形貌 · 全链路证据溯源</div>
          <p className="eyebrow">画像构建 · Agent 调度 · 个性化生成 · 反馈决策</p>
          <h2>面向航空工程材料损伤分析的多智能体个性化知识生成与实操训练系统</h2>
          <p>
            系统围绕航空轮胎、航空刹车片和飞机复合材料板三类训练方向，展示学习者画像、
            学情诊断、知识检索、资源生成、专家审核、路径决策和反馈迭代的完整闭环。
          </p>
          <div className="hero-rail" aria-label="系统能力概览">
            <span><strong>6</strong> 个协同 Agent</span>
            <span><strong>3</strong> 类材料方向</span>
            <span><strong>{knowledgeCatalog?.summary?.manifest_total_chunks || "--"}</strong> 条证据切片</span>
          </div>
          <div className="actions">
            <button className="primary" onClick={onDemo}><Play size={17} />加载演示案例</button>
            <button className="hero-secondary" onClick={onEngineeringDemo}><Search size={17} />工程检索案例</button>
            <button className="hero-secondary" onClick={onKnowledge}><Library size={17} />知识证据库</button>
            <button className="hero-secondary" onClick={onStart}><UserPlus size={17} />创建画像</button>
          </div>
        </div>
      </div>
      <div className="status-grid" aria-label="系统运行状态">
        <StatusTile icon={Server} label="后端服务" value={health?.status || "检查中"} active={health?.status === "ok"} />
        <StatusTile icon={Database} label="学习数据" value={health?.database_connected ? "MySQL 已连接" : "JSON fallback"} active={health?.database_connected} />
        <StatusTile icon={Search} label="知识检索" value={health?.es_connected ? "Elasticsearch" : "本地规则"} active={health?.es_connected} />
        <StatusTile icon={Workflow} label="RAG 策略" value={(health?.retrieval_mode || "hybrid").toUpperCase()} active />
        <StatusTile
          icon={Cpu}
          label="生成引擎"
          value={
            health?.llm_configured
              ? (health?.llm_resource_generation_enabled
                ? `LLM ${health?.llm_model || "已配置"}`
                : "LLM 问答 · 模板资源")
              : (health?.llm_enabled ? "LLM 配置不完整" : "Mock 稳定模式")
          }
          active={!health?.llm_enabled || health?.llm_configured}
        />
        <StatusTile icon={FileText} label="知识资产" value={`${knowledgeCatalog?.summary?.manifest_total_chunks || "--"} 切片 · ${health?.experimental_evidence?.asset_count || 0} 实验资产`} active />
        <StatusTile
          icon={CheckCircle2}
          label="自动化评测"
          value={evaluationSummary ? `${evaluationPassed}/${evaluationTotal} 通过` : "读取中"}
          active={evaluationSummary?.status === "passed"}
        />
        <StatusTile
          icon={ShieldCheck}
          label="专家复核"
          value={evaluationSummary?.expert_review?.confirmed ? "通过（电子确认）" : "待复核"}
          active={evaluationSummary?.expert_review?.confirmed}
        />
      </div>
      <section className="assistant-home-band">
        <div className="assistant-home-icon"><Bot size={24} strokeWidth={1.8} /></div>
        <div>
          <p className="eyebrow">CONTEXT-AWARE ASSISTANT</p>
          <h3>不确定下一步怎么做？让智能助手读取当前训练上下文</h3>
          <p>可解释当前页面、引导完整流程，也可结合画像、诊断结果、会话与检索证据回答专业问题。</p>
        </div>
        <button className="secondary" type="button" onClick={onAssistant}>
          <MessageSquare size={17} />打开智能助手
        </button>
      </section>
      <div className="section-heading">
        <div><p className="eyebrow">TRAINING DOMAINS</p><h3>三类航空材料训练方向</h3></div>
        <span>面向课程学习、科研入门与维修训练</span>
      </div>
      <div className="domain-grid">
        {domains.map((item) => {
          const DomainIcon = domainIcons[item.domain] || Wrench;
          return (
            <article className={`card domain-card ${item.domain}`} key={item.domain}>
              <div className="domain-card-head">
                <div className="domain-icon"><DomainIcon size={22} strokeWidth={1.8} /></div>
                <span>{domainLabels[item.domain]}</span>
              </div>
              <h3>{item.title}</h3>
              <p>{item.summary}</p>
            </article>
          );
        })}
      </div>
      <div className="section-heading flow-heading">
        <div><p className="eyebrow">AGENT ORCHESTRATION</p><h3>分析—生成—校验—决策闭环</h3></div>
        <span><CheckCircle2 size={16} /> 6 Agent 协同</span>
      </div>
      <div className="flow">
        {workflowSteps.map(([item, Icon], index) => (
          <div key={item}>
            <Icon size={19} strokeWidth={1.8} />
            <span>{item}</span>
            {index < workflowSteps.length - 1 && <ArrowRight className="flow-arrow" size={14} />}
          </div>
        ))}
      </div>
    </div>
  );
}

function StatusTile({ icon: Icon, label, value, active }) {
  return (
    <div className="status-tile">
      <div className="status-icon"><Icon size={18} strokeWidth={1.8} /></div>
      <div><span>{label}</span><strong>{value}</strong></div>
      <i className={active ? "active" : ""} />
    </div>
  );
}

function ContextAssistant({ open, onOpen, onClose, messages, loading, task, error, context, onSubmit, onCancel, onClear, onNavigate }) {
  const [draft, setDraft] = useState("");
  const [minimized, setMinimized] = useState(false);
  const streamRef = useRef(null);
  const latestAssistant = [...messages].reverse().find((item) => item.role === "assistant");
  const latestUser = [...messages].reverse().find((item) => item.role === "user");

  useEffect(() => {
    if (open && streamRef.current) {
      streamRef.current.scrollTop = streamRef.current.scrollHeight;
    }
  }, [open, messages, task?.progress]);

  function submit(event) {
    event.preventDefault();
    if (draft.trim().length < 2 || loading) return;
    onSubmit(draft);
    setDraft("");
  }

  if (!open) {
    return null;
  }

  return (
    <aside className={`context-assistant ${minimized ? "minimized" : ""}`} aria-label="智能问答助手">
      <header>
        <div className="assistant-avatar"><Bot size={21} /></div>
        <div><strong>航空材料训练助手</strong><span>理解当前页面与训练会话</span></div>
        <div className="assistant-header-actions">
          <button
            type="button"
            onClick={() => setMinimized((current) => !current)}
            aria-label={minimized ? "展开智能问答助手" : "最小化智能问答助手"}
            title={minimized ? "展开助手" : "最小化助手"}
          >
            {minimized ? <Maximize2 size={16} /> : <Minus size={18} />}
          </button>
          <button type="button" onClick={onClear} aria-label="清空问答记录" title="清空问答记录"><Trash2 size={17} /></button>
          <button type="button" onClick={onClose} aria-label="关闭智能问答助手" title="关闭"><X size={19} /></button>
        </div>
      </header>
      <div className="assistant-context-strip">
        <span>{context.active_view_label}</span>
        <span>{domainLabels[context.domain] || context.domain}</span>
        <span>{context.session_id ? "已绑定会话" : "预训练引导"}</span>
      </div>
      <div className="assistant-stream" ref={streamRef} aria-live="polite">
        {messages.map((message) => (
          <article className={`assistant-message ${message.role}`} key={message.id}>
            <div className="assistant-message-role">{message.role === "user" ? "你" : <Bot size={15} />}</div>
            <div>
              <StructuredMarkdown compact>{message.answer}</StructuredMarkdown>
              {message.answer_type && message.answer_type !== "welcome" && (
                <div className="assistant-answer-meta">
                  <span>{formatAssistantMode(message.generation_mode)}</span>
                  <span>{formatKnowledgeSource(message.knowledge_source)}</span>
                </div>
              )}
              {message.evidence_ids?.length > 0 && (
                <div className="assistant-evidence">
                  <span className="assistant-evidence-label"><Search size={13} />证据</span>
                  {message.evidence_ids.slice(0, 4).map((id, index) => (
                    <span className="assistant-evidence-item" key={id}>
                      <code>{id}</code>
                      {message.evidence_titles?.[index] && <small>{message.evidence_titles[index]}</small>}
                    </span>
                  ))}
                </div>
              )}
              {message.boundaries?.length > 0 && (
                <details className="assistant-boundaries">
                  <summary><ShieldCheck size={13} />查看回答边界</summary>
                  <ul>{message.boundaries.map((item) => <li key={item}>{item}</li>)}</ul>
                </details>
              )}
              {message.recommended_view && message.recommended_view !== context.active_view && (
                <button className="assistant-navigate" type="button" onClick={() => onNavigate(message.recommended_view)}>
                  前往{views.find((item) => item.id === message.recommended_view)?.label || message.recommended_view}<ArrowRight size={14} />
                </button>
              )}
            </div>
          </article>
        ))}
        {loading && (
          <div className="assistant-processing">
            <div><RefreshCw className="spin" size={15} /><strong>{task?.message || "正在理解问题"}</strong></div>
            <span>{task?.detail || "结合当前页面与训练上下文组织回答。"}</span>
            <progress value={task?.progress || 8} max="100" />
            <div className="assistant-processing-footer">
              <small>{task?.current_agent || "界面理解 Agent"} · {task?.progress || 8}%</small>
              <button type="button" disabled={task?.status === "cancelling"} onClick={onCancel}>
                <X size={12} />{task?.status === "cancelling" ? "正在停止" : "停止"}
              </button>
            </div>
          </div>
        )}
        {error && (
          <div className="assistant-error">
            <AlertTriangle size={14} />
            <span>{error}</span>
            {latestUser && !loading && (
              <button type="button" onClick={() => onSubmit(latestUser.answer)} title="重试上一个问题">
                <RotateCcw size={13} />重试
              </button>
            )}
          </div>
        )}
      </div>
      {!loading && latestAssistant?.suggested_questions?.length > 0 && (
        <div className="assistant-suggestions">
          {latestAssistant.suggested_questions.slice(0, 3).map((question) => (
            <button type="button" key={question} onClick={() => setDraft(question)}>{question}</button>
          ))}
        </div>
      )}
      <form className="assistant-composer" onSubmit={submit}>
        <textarea
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if ((event.ctrlKey || event.metaKey) && event.key === "Enter" && !loading && draft.trim().length >= 2) {
              event.preventDefault();
              onSubmit(draft);
              setDraft("");
            }
          }}
          placeholder="询问当前页面、学习路径或材料损伤问题"
          rows="2"
          maxLength="800"
        />
        <button type="submit" disabled={loading || draft.trim().length < 2} aria-label="发送问题" title="发送问题"><Send size={18} /></button>
      </form>
    </aside>
  );
}

function formatAssistantMode(mode) {
  return {
    "ui-guide-rules": "界面规则",
    "context-rules": "上下文规则",
    "mock-template": "Mock 生成",
    "mock-template-fallback": "LLM 故障回退",
    "review-template-fallback": "审核驳回后模板重生",
    llm: "真实 LLM",
  }[mode] || mode || "系统生成";
}

function formatKnowledgeSource(source) {
  return {
    "interface-context": "界面上下文",
    "page-context": "页面状态",
    elasticsearch: "Elasticsearch",
    "local-json": "JSON fallback",
  }[source] || source || "系统上下文";
}

function KnowledgeLibrary({ catalog, experiments }) {
  const [domainFilter, setDomainFilter] = useState("all");
  const [query, setQuery] = useState("");
  const [librarySection, setLibrarySection] = useState("experiments");
  const filteredSources = useMemo(() => {
    const keyword = query.trim().toLowerCase();
    return (catalog?.sources || []).filter((source) => {
      if (domainFilter !== "all" && source.domain !== domainFilter) return false;
      if (!keyword) return true;
      const searchable = [
        source.title,
        source.author_or_org,
        source.standard_number,
        source.source_id,
        ...(source.applicable_sections || []),
      ].join(" ").toLowerCase();
      return searchable.includes(keyword);
    });
  }, [catalog, domainFilter, query]);
  const filteredExperiments = useMemo(() => {
    const keyword = query.trim().toLowerCase();
    return (experiments?.records || []).filter((record) => {
      if (domainFilter !== "all" && record.domain !== domainFilter) return false;
      if (!keyword) return true;
      const searchable = [
        record.title,
        record.source_id,
        record.material_or_specimen,
        record.apparatus,
        ...(record.conditions || []),
        ...(record.measurements || []),
      ].join(" ").toLowerCase();
      return searchable.includes(keyword);
    });
  }, [experiments, domainFilter, query]);
  const filteredReviewedExperiments = filteredExperiments.filter((record) => record.reviewed_at).length;

  if (!catalog) return <EmptyState text="正在读取知识来源目录。" />;
  const summary = catalog.summary;
  return (
    <div className="view knowledge-view">
      <header className="page-intro knowledge-page-intro">
        <div>
          <p className="eyebrow">知识库构建与证据溯源</p>
          <h2>航空工程材料知识证据库</h2>
          <p className="muted">公开论文与技术报告、课题组授权轮胎资料及本地训练知识统一登记，每个检索片段均保留来源 ID。</p>
        </div>
        <div className="index-state">
          <strong><CheckCircle2 size={15} />{summary.indexed_in_es ? "ES 索引可用" : "本地清单模式"}</strong>
          <span>{summary.es_index || "aviation_material_knowledge"}</span>
          <span>{summary.authority_counts?.official_primary || 0} 项官方一手来源</span>
        </div>
      </header>

      <div className="corpus-stats">
        <div><Library size={18} /><strong>{summary.source_count}</strong><span>登记来源</span></div>
        <div><FileText size={18} /><strong>{summary.indexed_source_count}</strong><span>已切片来源</span></div>
        <div><Database size={18} /><strong>{summary.manifest_total_chunks}</strong><span>知识切片</span></div>
        <div><Clock3 size={18} /><strong>{summary.registry_updated_at}</strong><span>来源清单更新</span></div>
      </div>

      <div className="knowledge-toolbar" aria-label="知识来源筛选">
        <div className="knowledge-filter-stack">
          <div className="knowledge-view-switch" aria-label="知识库内容类型">
            <button type="button" className={librarySection === "experiments" ? "active" : ""} aria-pressed={librarySection === "experiments"} onClick={() => setLibrarySection("experiments")}><FlaskConical size={15} />实验卡</button>
            <button type="button" className={librarySection === "sources" ? "active" : ""} aria-pressed={librarySection === "sources"} onClick={() => setLibrarySection("sources")}><Library size={15} />来源目录</button>
          </div>
          <div className="segmented-control">
            {[
              ["all", "全部"],
              ["tire", "航空轮胎"],
              ["brake", "航空制动"],
              ["composite", "复合材料"],
            ].map(([value, label]) => (
              <button
                key={value}
                className={domainFilter === value ? "active" : ""}
                aria-pressed={domainFilter === value}
                onClick={() => setDomainFilter(value)}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
        <label className="source-search">
          <span><Search size={14} />筛选来源</span>
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="标题、机构、主题或 source_id" />
        </label>
      </div>

      {librarySection === "experiments" && <section className="literature-evidence" aria-label="公开文献实验卡">
        <div className="evidence-heading">
          <div>
            <p className="eyebrow">论文与官方报告参数提取</p>
            <h3>公开文献实验卡</h3>
          </div>
          <div className="review-summary">
            <span>{filteredExperiments.length} 项文献实验</span>
            <strong>{filteredReviewedExperiments} 项已人工复核</strong>
          </div>
        </div>
        <p className="muted">{experiments?.review_note}</p>
        <div className="literature-grid">
          {filteredExperiments.map((record) => (
            <article className="literature-card" key={record.record_id}>
              <div className="source-title-line">
                <span className={`domain-mark ${record.domain}`}>{domainLabels[record.domain]}</span>
                <h4>{record.title}</h4>
              </div>
              <div className="review-badge">已人工复核 · {record.reviewed_at}</div>
              <p><strong>试样：</strong>{record.material_or_specimen}</p>
              <p><strong>设备：</strong>{record.apparatus}</p>
              <div className="condition-list">
                {record.conditions.map((item) => <span key={item}>{item}</span>)}
              </div>
              <p><strong>观测指标：</strong>{record.measurements.join("、")}</p>
              <ul className="compact-list">
                {record.findings.slice(0, 2).map((item) => <li key={item}>{item}</li>)}
              </ul>
              <details>
                <summary>查看证据定位与适用边界</summary>
                <p><strong>来源：</strong>{record.source_id}</p>
                <p><strong>章节：</strong>{record.source_locators.join("；")}</p>
                <p><strong>证据 ID：</strong>{record.evidence_ids.join("；")}</p>
                <p><strong>限制：</strong>{record.limitations}</p>
                <p><strong>复核范围：</strong>{record.review_scope}</p>
              </details>
            </article>
          ))}
          {filteredExperiments.length === 0 && <p className="muted">当前筛选条件下没有匹配的文献实验卡。</p>}
        </div>
      </section>}

      {librarySection === "sources" && <div className="source-list">
        {filteredSources.map((source) => (
          <article className="source-row" key={source.source_id}>
            <div className="source-main">
              <div className="source-title-line">
                <span className={`domain-mark ${source.domain}`}>{domainLabels[source.domain] || "跨领域"}</span>
                <h3>{source.title}</h3>
              </div>
              <p>{source.author_or_org}{source.year ? ` · ${source.year}` : ""}{source.standard_number ? ` · ${source.standard_number}` : ""}</p>
              <div className="source-topics">
                {(source.applicable_sections || []).slice(0, 6).map((item) => <span key={item}>{item}</span>)}
              </div>
              <details>
                <summary>查看来源边界与授权说明</summary>
                <p><strong>证据 ID：</strong>{source.source_id}</p>
                <p><strong>授权：</strong>{source.license_or_authorization}</p>
                <p><strong>使用边界：</strong>{source.notes || "按来源原始试验条件使用。"}</p>
              </details>
            </div>
            <div className="source-facts">
              <span>{formatDocumentType(source.document_type)}</span>
              <strong>{source.chunk_count} 个切片</strong>
              <span>{source.indexed_in_es ? "已进入 ES" : "仅元数据/待切片"}</span>
              {source.url && <a href={source.url} target="_blank" rel="noreferrer">打开原始来源</a>}
            </div>
          </article>
        ))}
        {filteredSources.length === 0 && <p className="muted">当前筛选条件下没有匹配的知识来源。</p>}
      </div>}
      {librarySection === "sources" && filteredSources.length === 0 && <div className="panel"><p>没有匹配的来源，请调整筛选条件。</p></div>}
    </div>
  );
}

function formatDocumentType(value) {
  const labels = {
    advisory_circular: "适航通告",
    official_maintenance_handbook: "维修手册",
    official_maintenance_handbook_excerpt: "维修手册摘录",
    technical_note: "技术报告",
    technical_paper: "技术论文",
    conference_paper: "会议论文",
    contractor_report: "承包商报告",
    open_access_article: "开放论文",
    open_access_article_xml: "开放论文",
    open_access_dataset_article_xml: "开放数据论文",
    open_dataset_metadata: "开放数据集",
    team_experiment_dataset: "课题组授权资料",
    team_experiment_supplement: "课题组授权资料",
    team_experiment_case_dataset: "课题组授权案例",
    team_experiment_image_dataset: "课题组授权图像",
    team_experiment_matrix_dataset: "课题组授权矩阵",
    standard: "标准元数据",
    standard_metadata: "标准元数据",
  };
  return labels[value] || value || "领域资料";
}

function ProfileForm({ profile, profiles, domains, domain, learningGoal, onPreset, onChange, onDomainChange, onGoalChange, onDemo, onNext }) {
  if (!profile) return <EmptyState text="正在加载学习者画像。" />;
  const requiredFields = [
    ["学习者类型", profile.learner_type],
    ["专业背景", profile.background],
    ["画像特点", profile.characteristics],
    ["当前学习目标", learningGoal],
  ];
  const missingFields = requiredFields.filter(([, value]) => !String(value || "").trim()).map(([label]) => label);
  const profileComplete = missingFields.length === 0;
  return (
    <div className="view profile-view">
      <header className="page-intro">
        <div><p className="eyebrow">学习者画像构建</p><h2>定义训练对象与学习目标</h2><p>画像将直接影响讲解深度、实操约束、测试难度和后续学习路径。</p></div>
        <button className="secondary" onClick={onDemo}><Play size={17} />加载演示案例</button>
      </header>
      <div className="profile-context-bar">
        <div><UserRound size={17} /><span>学习者类型</span><strong>{profile.learner_type}</strong></div>
        <div><Target size={17} /><span>训练方向</span><strong>{domainLabels[domain]}</strong></div>
        <div><CircleGauge size={17} /><span>自评基础</span><strong>{profile.self_level}</strong></div>
      </div>
      <div className="profile-layout">
      <section className="profile-editor">
        <div className="form-grid">
          <label>画像编号<input value={profile.profile_id} disabled /></label>
          <label>学习者类型<input required aria-invalid={!String(profile.learner_type || "").trim()} value={profile.learner_type} onChange={(e) => onChange("learner_type", e.target.value)} /></label>
          <label>专业背景<textarea required aria-invalid={!String(profile.background || "").trim()} value={profile.background} onChange={(e) => onChange("background", e.target.value)} /></label>
          <label>画像特点<textarea required aria-invalid={!String(profile.characteristics || "").trim()} value={profile.characteristics} onChange={(e) => onChange("characteristics", e.target.value)} /></label>
          <label>训练方向
            <select value={domain} onChange={(e) => onDomainChange(e.target.value)}>
              {domains.map((item) => <option value={item.domain} key={item.domain}>{item.title}</option>)}
            </select>
          </label>
          <label>自评基础
            <select value={profile.self_level} onChange={(e) => onChange("self_level", e.target.value)}>
              {["低", "中", "高"].map((level) => <option key={level}>{level}</option>)}
            </select>
          </label>
          <label className="wide-field">当前学习目标
            <textarea required aria-invalid={!String(learningGoal || "").trim()} value={learningGoal} onChange={(e) => onGoalChange(e.target.value)} />
          </label>
        </div>
        {!profileComplete && <p className="profile-validation" role="alert">请完善：{missingFields.join("、")}</p>}
        <div className="actions">
          <button className="primary" disabled={!profileComplete} title={profileComplete ? "进入学情诊断" : `请先完善${missingFields.join("、")}`} onClick={onNext}>进入学情诊断<ArrowRight size={17} /></button>
        </div>
      </section>
      <section className="panel profile-presets">
        <p className="eyebrow">快速选择</p>
        <h3>内置测试画像</h3>
        <p>三类差异化学习者用于验证个性化生成效果。</p>
        {profiles.map((item) => (
          <button className={`preset ${item.profile_id === profile.profile_id ? "selected" : ""}`} key={item.profile_id} onClick={() => onPreset(item.profile_id)}>
            <span className="preset-icon"><UserRound size={17} /></span>
            <strong>{item.name}{item.profile_id === profile.profile_id && <CheckCircle2 size={15} />}</strong>
            <span>{item.characteristics}</span>
          </button>
        ))}
      </section>
      </div>
    </div>
  );
}

function Diagnosis({ health, questions, answers, setAnswers, diagnosis, loading, taskState, hasDemo, demoMessage, onDemo, onSubmit, onCancel }) {
  const answeredCount = questions.filter((question) => answers[question.id] !== undefined).length;
  const diagnosisComplete = questions.length > 0 && answeredCount === questions.length;
  const pipelineProgress = useEstimatedProgress(
    loading,
    pipelineProcessingPhases,
    health?.llm_resource_generation_enabled ? 45 : 9,
  );
  return (
    <div className="view diagnosis-view">
      <header className="page-intro">
        <div>
          <p className="eyebrow">学情诊断</p>
          <h2>建立学习者的知识能力基线</h2>
          <p>完成 {questions.length || 5} 道方向化诊断题，系统将识别强弱项并启动多智能体训练管线。</p>
        </div>
        <div className="diagnosis-submit-area">
          <div className={`diagnosis-completion ${diagnosisComplete ? "complete" : ""}`}>
            <span>诊断进度</span><strong>{answeredCount}/{questions.length || 5}</strong>
            <progress value={answeredCount} max={questions.length || 5} />
          </div>
          <div className="actions">
            {hasDemo && <button className="secondary" onClick={onDemo}><Play size={17} />加载演示答案</button>}
            <button className="primary" disabled={loading || !diagnosisComplete} onClick={onSubmit} title={!diagnosisComplete ? "请先完成全部诊断题" : "提交诊断并启动 Agent"}>
              {loading ? <><Activity className="spin" size={17} />运行 Agent 管线...</> : <><Network size={17} />提交诊断并启动 Agent</>}
            </button>
          </div>
        </div>
      </header>
      {loading && (
        <ProcessingProgress
          title="正在构建个性化训练方案"
          progressState={pipelineProgress}
          phases={pipelineProcessingPhases}
          liveTask={taskState}
          onCancel={onCancel}
        />
      )}
      {demoMessage && <article className="panel"><h3>演示案例诊断表现</h3><p>{demoMessage}</p></article>}
      {diagnosis && (
        <section className="diagnosis-result" aria-label="诊断结果摘要">
          <div className="diagnosis-score"><span>诊断得分</span><strong>{diagnosis.score}</strong><small>/ 100</small></div>
          <div><span>当前水平</span><strong>{diagnosis.level}</strong></div>
          <div><span>重点薄弱项</span><strong>{diagnosis.weak_points?.slice(0, 2).join("、") || "待识别"}</strong></div>
          <p>{diagnosis.diagnosis_summary}</p>
        </section>
      )}
      <div className="question-list">
        {questions.map((question, index) => (
          <article className="card question" key={question.id}>
            <h3>{index + 1}. {question.question}</h3>
            <p className="muted">知识点：{question.knowledge_point}；难度：{question.difficulty}</p>
            <div className="options">
              {question.options.map((option) => (
                <button
                  key={option}
                  className={answers[question.id] === option ? "selected" : ""}
                  aria-pressed={answers[question.id] === option}
                  onClick={() => setAnswers((current) => ({ ...current, [question.id]: option }))}
                >
                  {option}
                </button>
              ))}
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

function Agents({ agentRun, taskState, onNext }) {
  const [activeStepIndex, setActiveStepIndex] = useState(2);
  if (!agentRun) return <EmptyState text="请先完成学情诊断并运行 Agent。" />;
  const timings = taskState?.kind === "agent_run" ? (taskState.step_timings || []) : [];
  const totalDuration = taskState?.elapsed_ms || timings.reduce((sum, item) => sum + (item.duration_ms || 0), 0);
  const retrievalStep = agentRun.agent_steps.find((step) => step.details?.knowledge_source);
  const shortSessionId = agentRun.session_id?.slice(0, 8) || "未生成";
  const safeActiveStepIndex = Math.min(activeStepIndex, Math.max(agentRun.agent_steps.length - 1, 0));
  const activeStep = agentRun.agent_steps[safeActiveStepIndex];
  return (
    <div className="view agents-view">
      <header className="page-intro agent-page-intro">
        <div>
          <p className="eyebrow">多智能体协同调度</p>
          <h2>6 个 Agent 已完成协同闭环</h2>
          <p>会话 <code title={agentRun.session_id}>{shortSessionId}</code> · 每一步均保留输入、结论、证据与审核记录。</p>
        </div>
        <div className="page-proof-stack">
          <span><CheckCircle2 size={15} />{agentRun.agent_steps.length}/6 步完成</span>
          <span><Search size={15} />{retrievalStep?.details?.knowledge_source || "知识库证据"}</span>
          <span><ShieldCheck size={15} />审核后输出</span>
        </div>
      </header>
      <section className="agent-overview" aria-label="六个 Agent 协同总览">
        {agentRun.agent_steps.map((step, index) => (
          <button
            type="button"
            aria-pressed={safeActiveStepIndex === index}
            className={`agent-overview-item stage-${index + 1} ${safeActiveStepIndex === index ? "active" : ""}`}
            aria-label={`${agentOverviewLabels[index] || step.agent_name}：${step.role}`}
            title={step.role}
            onClick={() => setActiveStepIndex(index)}
            key={`overview-${step.agent_name}`}
          >
            <span>{String(index + 1).padStart(2, "0")}</span>
            <div><strong>{agentOverviewLabels[index] || step.agent_name.replace(" Agent", "")}</strong><small>第 {index + 1} 步</small></div>
            <CheckCircle2 size={16} />
          </button>
        ))}
      </section>
      {timings.length > 0 && (
        <section className="execution-summary" aria-label="本次 Agent 执行摘要">
          <div><Clock3 size={17} /><span>管线总耗时</span><strong>{formatDuration(totalDuration)}</strong></div>
          <div><Network size={17} /><span>已完成步骤</span><strong>{timings.length} 个</strong></div>
          <div><Activity size={17} /><span>进度来源</span><strong>后端实时事件</strong></div>
        </section>
      )}
      <section className="agent-focus-bar" aria-label="当前 Agent 详情">
        <div><span>当前查看</span><strong>{activeStep?.agent_name}</strong><small>{safeActiveStepIndex + 1} / {agentRun.agent_steps.length}</small></div>
        <div>
          <button type="button" aria-label="查看上一个 Agent" disabled={safeActiveStepIndex === 0} onClick={() => setActiveStepIndex((current) => Math.max(0, current - 1))}><ChevronLeft size={17} /></button>
          <button type="button" aria-label="查看下一个 Agent" disabled={safeActiveStepIndex === agentRun.agent_steps.length - 1} onClick={() => setActiveStepIndex((current) => Math.min(agentRun.agent_steps.length - 1, current + 1))}><ChevronRight size={17} /></button>
        </div>
      </section>
      <div className="timeline focused-agent-timeline">
        {agentRun.agent_steps.filter((_, index) => index === safeActiveStepIndex).map((step) => {
          const index = safeActiveStepIndex;
          return (
          <article className={`agent-step stage-${index + 1}`} key={`${step.agent_name}-${index}`}>
            <div className="dot">{index + 1}</div>
            <div>
              <header className="agent-step-heading">
                <div><span>STEP {String(index + 1).padStart(2, "0")}</span><h3>{step.agent_name}</h3><p>{step.role}</p></div>
                <strong><CheckCircle2 size={15} />{step.status === "completed" ? "已完成" : step.status}</strong>
              </header>
              <div className="agent-meta">
                <span>状态：{step.status}</span>
                <span>置信度：{Math.round(step.confidence * 100)}%</span>
                <span>依据：{step.evidence_ids.length ? step.evidence_ids.join(", ") : "无"}</span>
                {timings.some((item) => item.step_index === index + 1) && (
                  <span>耗时：{formatDuration(timings
                    .filter((item) => item.step_index === index + 1)
                    .reduce((sum, item) => sum + (item.duration_ms || 0), 0))}</span>
                )}
              </div>
              {step.details?.retrieval_mode && (
                <div className="agent-meta">
                  <span>检索模式：{String(step.details.retrieval_mode).toUpperCase()}</span>
                  <span>实际策略：{step.details.effective_retrieval_mode}</span>
                  <span>知识来源：{step.details.knowledge_source}</span>
                </div>
              )}
              {step.details?.condition_match_strategy && (
                <div className="agent-meta">
                  <span>工况匹配：{formatMatchStrategy(step.details.condition_match_strategy)}</span>
                  <span>解析条件：{formatConditionConstraints(step.details.condition_constraints)}</span>
                </div>
              )}
              {step.details?.evidence_titles?.length > 0 && (
                <ul className="compact-list">
                  {step.details.evidence_titles.map((title, itemIndex) => (
                    <li key={`${step.agent_name}-evidence-${itemIndex}`}>
                      {step.details.evidence_ids?.[itemIndex] || "evidence"}：{title}
                      {step.details.retrieval_scores?.[itemIndex] !== undefined
                        ? `（score ${step.details.retrieval_scores[itemIndex]}）`
                        : ""}
                    </li>
                  ))}
                </ul>
              )}
              {step.details?.experimental_evidence?.length > 0 && (
                <section className="evidence-section" aria-label="实验依据">
                  <div className="evidence-heading">
                    <div>
                      <p className="eyebrow">课题组轮胎多模态证据</p>
                      <h4>实验依据</h4>
                    </div>
                    <span>{step.details.experimental_evidence.length} 项已审核资产</span>
                  </div>
                  <div className="evidence-grid">
                    {step.details.experimental_evidence.map((asset) => (
                      <article className="evidence-card" key={asset.asset_id}>
                        <img
                          src={api.evidenceMediaUrl(asset.asset_id)}
                          alt={asset.title}
                          loading="lazy"
                        />
                        <div className="evidence-body">
                          <div className="evidence-title-row">
                            <h5>{asset.title}</h5>
                            <span className="evidence-status">{asset.review_status}</span>
                          </div>
                          <p>{asset.observation}</p>
                          <div className="evidence-tags">
                            <span>{asset.asset_id}</span>
                            <span>{asset.modality}</span>
                            {asset.severity && <span>{asset.severity}</span>}
                          </div>
                          <details>
                            <summary>查看工况与溯源</summary>
                            <p><strong>工况：</strong>{formatCondition(asset.condition)}</p>
                            <p><strong>来源：</strong>{asset.source_reference}</p>
                            <p><strong>边界：</strong>{asset.limitations}</p>
                          </details>
                        </div>
                      </article>
                    ))}
                  </div>
                </section>
              )}
              {step.agent_name === "专家审核纠偏 Agent" && step.details?.claim_assessments?.length > 0 && (
                <section className="cross-review" aria-label="生成与审核交叉验证">
                  <div className="cross-review-heading">
                    <div>
                      <p className="eyebrow">生成 Agent 提案 · 审核 Agent 核验</p>
                      <h4>结论—证据—边界交叉验证</h4>
                    </div>
                    <span>
                      {step.details.correction_rounds
                        ? `已完成 ${step.details.correction_rounds} 轮纠偏重生`
                        : "结构化核验完成"}
                    </span>
                  </div>
                  <div className="claim-grid">
                    {step.details.claim_assessments.map((claim, claimIndex) => (
                      <article className="claim-card" key={`${claim.category}-${claimIndex}`}>
                        <div>
                          <strong>{claim.category}</strong>
                          <span className={`claim-status ${formatClaimStatusTone(claim.status)}`}>
                            {formatClaimStatus(claim.status)}
                          </span>
                        </div>
                        <p><b>证据：</b>{claim.basis_ids?.length ? claim.basis_ids.slice(0, 3).join("、") : "当前无直接证据"}</p>
                        <p><b>边界：</b>{claim.boundary}</p>
                      </article>
                    ))}
                  </div>
                  {step.details.unsupported_claims?.length > 0 && (
                    <div className="review-warning">
                      <ShieldCheck size={17} />
                      <span>已拦截越界声明：{step.details.unsupported_claims.join("；")}</span>
                    </div>
                  )}
                  <p className="protocol-note">
                    校验规则：引用闭合、工况字段、难度匹配、实操约束或表达边界不满足时，触发一次纠偏重生并再次复核。
                  </p>
                </section>
              )}
              <dl>
                <dt>核心结论</dt><dd className="agent-output-summary">{step.output_summary}</dd>
                <dt>输入摘要</dt><dd>{step.input_summary}</dd>
                <dt>原始详情</dt>
                <dd>
                  <details className="agent-raw-details">
                    <summary>展开结构化输出</summary>
                    <pre>{JSON.stringify(step.details, null, 2)}</pre>
                  </details>
                </dd>
              </dl>
            </div>
          </article>
          );
        })}
      </div>
      <button className="primary" onClick={onNext}>查看个性化资源<ArrowRight size={17} /></button>
    </div>
  );
}

function formatCondition(condition = {}) {
  return Object.entries(condition)
    .filter(([, value]) => value !== null && value !== undefined && value !== "")
    .map(([key, value]) => `${key}=${Array.isArray(value) ? value.join("/") : value}`)
    .join("，");
}

function formatMatchStrategy(strategy) {
  return {
    "exact-condition-group": "精确工况组",
    "exact-condition": "精确单工况",
    "topic-constrained-ranking": "专题约束排序",
    "source-linked-ranking": "来源关联排序",
  }[strategy] || strategy;
}

function formatConditionConstraints(constraints = {}) {
  const fields = [
    ["载荷", constraints.normal_load_N, "N"],
    ["距离", constraints.sliding_distance_m, "m"],
    ["老化时长", constraints.aging_duration_h, "h"],
  ];
  const values = fields
    .filter(([, items]) => Array.isArray(items) && items.length > 0)
    .map(([label, items, unit]) => `${label} ${items.join("/")} ${unit}`);
  return values.join("；") || "未指定数值工况";
}

function formatClaimStatus(status) {
  return {
    "evidence-bound": "证据绑定",
    "knowledge-only": "仅知识依据",
    "verified-fields": "工况字段已核验",
    limited: "证据有限",
    "bounded-inference": "边界内推断",
    "degraded-hypothesis": "已降级为假设",
    "training-only": "仅限训练建议",
  }[status] || status;
}

function formatClaimStatusTone(status) {
  if (["limited", "degraded-hypothesis", "knowledge-only"].includes(status)) return "caution";
  if (status === "training-only") return "neutral";
  return "verified";
}

function Resources({ resources, onInquiry, onNext }) {
  const [activeResource, setActiveResource] = useState("lecture");
  if (!resources) return <EmptyState text="请先运行 Agent 管线。" />;
  const lecture = resources.personalized_lecture;
  return (
    <div className="view resource-view">
      <header className="page-intro">
        <div><p className="eyebrow">领域知识个性化生成</p><h2>{lecture.title}</h2><p>内容已根据画像、诊断薄弱点与检索证据重组，并通过审核 Agent 校验。</p></div>
        <div className="resource-proof"><span><BookOpen size={15} />4 类训练资源</span><span><ShieldCheck size={15} />证据约束生成</span></div>
      </header>
      {resources.personalization && (
        <div className="agent-meta">
          <span>画像策略：{resources.personalization.strategy_label}</span>
          <span>讲解方式：{resources.personalization.explanation_style}</span>
          <span>测评重点：{resources.personalization.assessment_focus}</span>
        </div>
      )}
      <div className="resource-tabs" role="tablist" aria-label="个性化资源类型">
        <button type="button" role="tab" aria-selected={activeResource === "lecture"} className={activeResource === "lecture" ? "active" : ""} onClick={() => setActiveResource("lecture")}><BookOpen size={17} /><strong>定制化讲义</strong><span>{lecture.sections.length} 节</span></button>
        <button type="button" role="tab" aria-selected={activeResource === "guide"} className={activeResource === "guide" ? "active" : ""} onClick={() => setActiveResource("guide")}><ClipboardCheck size={17} /><strong>实操指南</strong><span>{resources.practical_guide.steps.length} 步</span></button>
        <button type="button" role="tab" aria-selected={activeResource === "quiz"} className={activeResource === "quiz" ? "active" : ""} onClick={() => setActiveResource("quiz")}><Target size={17} /><strong>分阶测试</strong><span>{resources.graded_quiz.length} 题</span></button>
        <button type="button" role="tab" aria-selected={activeResource === "case"} className={activeResource === "case" ? "active" : ""} onClick={() => setActiveResource("case")}><ScanSearch size={17} /><strong>案例任务</strong><span>1 项</span></button>
      </div>
      <div className="resource-stage">
        {activeResource === "lecture" && <article className="resource-document lecture-resource">
          <h3><BookOpen size={19} />定制化讲义</h3>
          {lecture.sections.map((section) => (
            <div key={section.heading}>
              <h4>{section.heading}</h4>
              <StructuredMarkdown compact>{section.content}</StructuredMarkdown>
            </div>
          ))}
          <span className="badge">{lecture.difficulty}</span>
        </article>}
        {activeResource === "guide" && <article className="resource-document guide-resource">
          <h3><ClipboardCheck size={19} />实操指南</h3>
          <ol>{resources.practical_guide.steps.map((step) => <li key={step}>{step}</li>)}</ol>
          <p>记录模板：{resources.practical_guide.record_template.join(" / ")}</p>
        </article>}
        {activeResource === "quiz" && <article className="resource-document quiz-resource">
          <h3><Target size={19} />分阶测试题</h3>
          {resources.graded_quiz.map((item) => (
            <p className="quiz-resource-item" key={item.id}><strong>{item.level}</strong>{item.question}</p>
          ))}
        </article>}
        {activeResource === "case" && <article className="resource-document case-resource">
          <h3><ScanSearch size={19} />案例分析任务</h3>
          <div className="case-resource-body">
            <p>{resources.case_task.brief}</p>
            <p><strong>任务输出：</strong>{resources.case_task.expected_output.join("、")}</p>
          </div>
        </article>}
      </div>
      <div className="actions">
        <button className="primary" onClick={onNext}>查看学情报告<ArrowRight size={17} /></button>
        <button className="secondary" onClick={onInquiry}><MessageSquare size={17} />基于当前证据动态追问</button>
      </div>
    </div>
  );
}

const pipelineProcessingPhases = [
  { label: "学情诊断 Agent", detail: "计算得分并定位知识薄弱点", until: 2 },
  { label: "材料路由 Agent", detail: "选择对应航空材料知识域", until: 4 },
  { label: "知识检索 Agent", detail: "从 Elasticsearch 召回证据片段", until: 9 },
  { label: "资源生成 Agent", detail: "生成讲义、指南、测试题与案例", until: 31 },
  { label: "审核纠偏 Agent", detail: "核验概念、引用与适用边界", until: 41 },
  { label: "路径决策 Agent", detail: "规划下一步学习与训练动作", until: 44 },
  { label: "保存会话", detail: "写入 Agent 步骤、资源和报告", until: Number.POSITIVE_INFINITY },
];

const inquiryProcessingPhases = [
  { label: "材料路由 Agent", detail: "识别问题所属航空材料知识域", until: 2 },
  { label: "知识检索 Agent", detail: "从 Elasticsearch 召回并排序证据", until: 5 },
  { label: "启发式讲解 Agent", detail: "依据画像和证据生成分层回答", until: 12 },
  { label: "审核纠偏 Agent", detail: "检查引用闭合、专业边界和风险表达", until: 17 },
  { label: "路径决策 Agent", detail: "生成追问、实操任务和下一步动作", until: 18 },
  { label: "保存会话", detail: "保存回答、证据链和审核记录", until: Number.POSITIVE_INFINITY },
];

function useEstimatedProgress(active, phases, estimatedSeconds) {
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  useEffect(() => {
    if (!active) {
      setElapsedSeconds(0);
      return undefined;
    }
    const startedAt = Date.now();
    setElapsedSeconds(0);
    const timer = window.setInterval(() => {
      setElapsedSeconds((Date.now() - startedAt) / 1000);
    }, 250);
    return () => window.clearInterval(timer);
  }, [active]);

  const phaseIndex = Math.min(
    phases.findIndex((phase) => elapsedSeconds < phase.until),
    phases.length - 1,
  );
  const normalizedPhaseIndex = phaseIndex < 0 ? phases.length - 1 : phaseIndex;
  const progress = Math.min(92, Math.max(4, Math.round((elapsedSeconds / estimatedSeconds) * 86)));
  const remainingSeconds = Math.max(0, Math.ceil(estimatedSeconds - elapsedSeconds));

  return {
    elapsedSeconds,
    phaseIndex: normalizedPhaseIndex,
    phase: phases[normalizedPhaseIndex],
    progress,
    remainingSeconds,
    overtime: elapsedSeconds > estimatedSeconds,
    estimatedSeconds,
  };
}

function ProcessingProgress({ title, progressState, phases, liveTask, onCancel, compact = false }) {
  const {
    elapsedSeconds,
    phaseIndex,
    phase,
    progress,
    estimatedSeconds,
  } = progressState;
  const isLive = Boolean(liveTask?.task_id && ["queued", "running", "cancelling"].includes(liveTask.status));
  const isPersisting = liveTask?.event_type === "persisting" || liveTask?.current_agent === "会话持久化";
  const livePhaseIndex = isPersisting
    ? phases.length - 1
    : Math.max(0, Math.min(phases.length - 1, (liveTask?.step_index || 1) - 1));
  const displayedPhaseIndex = isLive ? livePhaseIndex : phaseIndex;
  const displayedProgress = isLive ? Math.max(2, liveTask.progress || 0) : progress;
  const displayedTitle = isLive ? (liveTask.message || title) : title;
  const displayedDetail = isLive ? (liveTask.detail || phase.detail) : phase.detail;
  const displayedElapsedSeconds = isLive
    ? Math.max(elapsedSeconds, (liveTask.elapsed_ms || 0) / 1000)
    : elapsedSeconds;
  const displayedRemainingSeconds = Math.max(0, Math.ceil(estimatedSeconds - displayedElapsedSeconds));
  const displayedOvertime = displayedElapsedSeconds > estimatedSeconds;
  return (
    <section className={`processing-progress ${compact ? "compact" : ""} ${isLive ? "live" : "estimated"}`} aria-live="polite">
      <div className="processing-summary">
        <div className="processing-icon"><Activity className="spin" size={19} /></div>
        <div>
          <strong>{displayedTitle}</strong>
          <span>{displayedDetail}</span>
        </div>
        <div className="processing-time">
          <strong>{Math.floor(displayedElapsedSeconds)} s</strong>
          <span>{displayedOvertime ? "正在继续处理，请稍候" : `预计还需约 ${displayedRemainingSeconds} 秒`}</span>
          {onCancel && isLive && (
            <button type="button" disabled={liveTask?.status === "cancelling"} onClick={onCancel}>
              <X size={13} />{liveTask?.status === "cancelling" ? "正在停止" : "停止任务"}
            </button>
          )}
        </div>
      </div>
      <div className="processing-bar" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow={displayedProgress}>
        <span style={{ width: `${displayedProgress}%` }} />
      </div>
      <div className="processing-phases">
        {phases.map((item, index) => (
          <div className={index < displayedPhaseIndex ? "done" : index === displayedPhaseIndex ? "active" : "pending"} key={item.label}>
            <i>{index < displayedPhaseIndex ? <CheckCircle2 size={13} /> : index + 1}</i>
            <span>{item.label}</span>
          </div>
        ))}
      </div>
      <small>
        {isLive ? "后端实时事件已连接；" : "实时事件暂不可用，当前使用时间估算；"}
        常见耗时约 {estimatedSeconds} 秒，实际完成时间取决于模型和网络状态。
      </small>
    </section>
  );
}

const guidedQuestionPresets = [
  "为什么在 60 N、160 m 往复摩擦工况下，不能只凭磨损形貌就断定热氧老化是主导机制？",
  "请把热氧老化与滑动磨损的耦合机制讲得更容易理解，并给出证据依据。",
  "如果要验证磨损量变化原因，下一组对照实验应控制哪些变量？",
  "如何区分胎面裂纹、剥落的观察事实、机理推断和维护建议？",
];

function GuidedInquiry({
  sessionId,
  health,
  profile,
  domain,
  learningGoal,
  diagnosis,
  history,
  loading,
  taskState,
  onSubmit,
  onCancel,
  onNext,
}) {
  const [question, setQuestion] = useState(guidedQuestionPresets[0]);
  const [selectedId, setSelectedId] = useState("");
  const [pendingQuestion, setPendingQuestion] = useState("");
  const [showIntelligenceRail, setShowIntelligenceRail] = useState(true);
  const previousHistoryLength = useRef(0);
  const chatStreamRef = useRef(null);
  const llmReady = Boolean(health?.llm_configured);
  const recentLatencyMs = history[history.length - 1]?.generation_audit?.latency_ms;
  const recentTaskDuration = taskState?.status === "completed" && taskState?.created_at && taskState?.updated_at
    ? (new Date(taskState.updated_at).getTime() - new Date(taskState.created_at).getTime()) / 1000
    : 0;
  const activeQuestion = pendingQuestion || taskState?.metadata?.question || "";
  const inquiryEstimateSeconds = recentTaskDuration > 0
    ? Math.max(12, Math.min(90, Math.ceil(recentTaskDuration * 1.15)))
    : recentLatencyMs
    ? Math.max(8, Math.min(45, Math.ceil((recentLatencyMs / 1000) * 1.35)))
    : (llmReady ? 40 : 7);
  const inquiryProgress = useEstimatedProgress(
    Boolean(loading && activeQuestion),
    inquiryProcessingPhases,
    inquiryEstimateSeconds,
  );

  useEffect(() => {
    if (!history.length) {
      setSelectedId("");
      previousHistoryLength.current = 0;
      return;
    }
    if (
      history.length > previousHistoryLength.current
      || !history.some((item) => item.interaction_id === selectedId)
    ) {
      setSelectedId(history[history.length - 1].interaction_id);
      requestAnimationFrame(() => {
        chatStreamRef.current?.scrollTo({
          top: chatStreamRef.current.scrollHeight,
          behavior: "smooth",
        });
      });
    }
    previousHistoryLength.current = history.length;
  }, [history, selectedId]);

  async function handleSubmit(candidate = question) {
    const trimmed = candidate.trim();
    if (loading || trimmed.length < 5) return;
    setPendingQuestion(trimmed);
    const result = await onSubmit(trimmed);
    setPendingQuestion("");
    if (result) setQuestion(result.follow_up_question || "");
  }

  function handleComposerKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSubmit();
    }
  }

  if (!sessionId) return <EmptyState text="请先完成诊断并运行 Agent，系统才能带着画像和证据回答追问。" />;
  const selected = history.find((item) => item.interaction_id === selectedId) || history[history.length - 1];
  const modeLabel = llmReady
    ? `真实 LLM · ${health?.llm_model || "已配置模型"}`
    : (health?.llm_enabled ? "LLM 配置不完整 · 自动兜底" : "Mock 模板兜底");
  const weakPoints = diagnosis?.weak_points || [];
  const presetLabels = ["精确工况判断", "降维解释", "对照实验设计", "损伤判读"];
  const suggestedQuestions = [
    ...(selected?.follow_up_question
      ? [{ label: "沿当前思路继续", value: selected.follow_up_question }]
      : []),
    ...guidedQuestionPresets.map((value, index) => ({ label: presetLabels[index], value })),
  ].slice(0, 4);
  const defaultInquirySteps = [
    { agent_name: "材料领域路由 Agent", role: "识别问题领域" },
    { agent_name: "专业知识检索 Agent", role: "召回可信证据" },
    { agent_name: "启发式讲解 Agent", role: "生成个性化解释" },
    { agent_name: "追问审核纠偏 Agent", role: "核验结论与边界" },
    { agent_name: "追问路径决策 Agent", role: "决定下一训练动作" },
  ];
  const showLiveTrack = Boolean(loading && taskState?.kind === "guided_inquiry");
  const railSteps = showLiveTrack ? defaultInquirySteps : (selected?.agent_steps || defaultInquirySteps);
  const liveTimings = showLiveTrack ? (taskState?.step_timings || []) : [];

  return (
    <div className="view inquiry-view">
      <div className="training-header">
        <div>
          <p className="eyebrow">对话驱动 · RAG 约束 · 审核后输出</p>
          <h2>多智能体智能训练工作台</h2>
          <p>学习者自由提问后，系统调用专业 Agent 完成路由、检索、生成、审核和学习决策。</p>
        </div>
        <div className="training-header-actions">
          <div className={`mode-badge ${llmReady ? "live" : "mock"}`}>
            <Cpu size={16} />{modeLabel}
          </div>
          <button type="button" className="rail-toggle" aria-pressed={showIntelligenceRail} onClick={() => setShowIntelligenceRail((current) => !current)}>
            {showIntelligenceRail ? <PanelRightClose size={16} /> : <PanelRightOpen size={16} />}{showIntelligenceRail ? "收起证据栏" : "展开证据栏"}
          </button>
        </div>
      </div>

      <section className="training-context" aria-label="当前训练上下文">
        <div><UserRound size={17} /><span>学习者</span><strong>{profile?.name || profile?.profile_type || "当前学习者"}</strong></div>
        <div><FlaskConical size={17} /><span>训练方向</span><strong>{domainLabels[domain] || domain}</strong></div>
        <div><CircleGauge size={17} /><span>诊断水平</span><strong>{diagnosis ? `${diagnosis.score} 分 · ${diagnosis.level}` : "待诊断"}</strong></div>
        <div className="context-goal"><Target size={17} /><span>当前目标</span><strong>{learningGoal}</strong></div>
      </section>

      <div className={`training-workbench ${showIntelligenceRail ? "" : "rail-collapsed"}`}>
        <section className="conversation-pane" aria-label="学习对话">
          <header className="conversation-toolbar">
            <div>
              <span className="online-dot" />
              <div><strong>航空材料导学 Agent</strong><small>会话 {sessionId.slice(0, 8)} · 已持久化 {history.length} 轮</small></div>
            </div>
            <button className="text-command" onClick={onNext}>查看报告<ArrowRight size={15} /></button>
          </header>

          <div className="chat-stream" ref={chatStreamRef}>
            {!history.length && !pendingQuestion && (
              <div className="chat-onboarding">
                <div className="tutor-avatar"><Bot size={25} /></div>
                <div>
                  <p className="eyebrow">训练会话已就绪</p>
                  <h3>从真实问题开始，而不是从固定答案开始</h3>
                  <p>我会结合你的画像、诊断薄弱点与航空材料知识证据回答，并把每一步 Agent 决策展示在右侧。</p>
                  {weakPoints.length > 0 && (
                    <div className="focus-points">
                      <span>建议先问</span>
                      {weakPoints.slice(0, 3).map((item) => <button type="button" key={item} onClick={() => setQuestion(`请结合证据解释${item}，并给我一个训练任务。`)}>{item}</button>)}
                    </div>
                  )}
                </div>
              </div>
            )}

            {history.map((item, index) => (
              <article
                className={`conversation-turn ${item.interaction_id === selected?.interaction_id ? "selected" : ""}`}
                key={item.interaction_id}
                onClick={() => setSelectedId(item.interaction_id)}
              >
                <div className="learner-message">
                  <div><UserRound size={16} /></div>
                  <section><span>学习者 · 第 {index + 1} 轮</span><p>{item.question}</p></section>
                </div>
                <div className="tutor-message">
                  <div className="tutor-avatar"><Bot size={18} /></div>
                  <section>
                    <div className="message-meta">
                      <strong>多智能体综合回答</strong>
                      <span>{item.explanation_level}</span>
                    </div>
                    <StructuredMarkdown>{item.answer}</StructuredMarkdown>
                    <div className="answer-proof-strip">
                      <span><Database size={13} />{String(item.retrieval_mode).toUpperCase()} · {item.knowledge_source}</span>
                      <span><FileText size={13} />{item.evidence_ids?.length || 0} 条证据</span>
                      <span><ShieldCheck size={13} />{item.review?.status || "已审核"}</span>
                      <span><Sparkles size={13} />{formatGenerationMode(item.generation_mode)}</span>
                    </div>
                  </section>
                </div>
              </article>
            ))}

            {activeQuestion && loading && (
              <article className="conversation-turn processing">
                <div className="learner-message">
                  <div><UserRound size={16} /></div>
                  <section><span>学习者 · 正在提交</span><p>{activeQuestion}</p></section>
                </div>
                <ProcessingProgress
                  title={`正在处理：${inquiryProgress.phase.label}`}
                  progressState={inquiryProgress}
                  phases={inquiryProcessingPhases}
                  liveTask={taskState}
                  onCancel={onCancel}
                  compact
                />
              </article>
            )}
            <div />
          </div>

          <footer className="workbench-composer">
            <div className="prompt-presets" aria-label="推荐问题">
              <span><Lightbulb size={14} />推荐追问</span>
              {suggestedQuestions.map((item, index) => (
                <button type="button" key={`${item.value}-${index}`} title={item.value} onClick={() => setQuestion(item.value)}>
                  {item.label}
                </button>
              ))}
            </div>
            <div className="composer-input-row">
              <textarea
                id="guided-question"
                value={question}
                maxLength={800}
                rows={3}
                onChange={(event) => setQuestion(event.target.value)}
                onKeyDown={handleComposerKeyDown}
                placeholder="输入你的航空材料损伤分析问题，Enter 发送，Shift + Enter 换行"
              />
              <button
                className="send-button"
                aria-label="发送问题"
                title="发送问题"
                disabled={loading || question.trim().length < 5}
                onClick={() => handleSubmit()}
              >
                {loading ? <Activity className="spin" size={20} /> : <Send size={20} />}
              </button>
            </div>
            <small>回答由检索证据约束并经过审核 Agent 校验，不替代适航或维修放行结论。</small>
          </footer>
        </section>

        {showIntelligenceRail && <aside className="intelligence-rail" aria-label="Agent 协同与证据审核">
          <div className="rail-heading">
            <div><p className="eyebrow">本轮可解释过程</p><h3>Agent 协同轨迹</h3></div>
            <span>{railSteps.length} 步</span>
          </div>

          <div className="rail-agent-list">
            {railSteps.map((step, index) => {
              const timing = liveTimings.find((item) => item.step_index === index + 1);
              const isActiveStep = showLiveTrack && taskState?.current_agent === step.agent_name;
              const isCompleteStep = Boolean(!showLiveTrack && selected) || Boolean(timing);
              return (
                <article className={isCompleteStep ? "complete" : isActiveStep ? "active" : "waiting"} key={`${step.agent_name}-${index}`}>
                  <div>{isCompleteStep ? <CheckCircle2 size={16} /> : isActiveStep ? <Activity className="spin" size={15} /> : <span>{index + 1}</span>}</div>
                  <section>
                    <strong>{step.agent_name}</strong>
                    <p>{step.output_summary || step.role}</p>
                    {!showLiveTrack && selected && <small>置信度 {Math.round((step.confidence || 0) * 100)}%</small>}
                    {timing && <small>真实耗时 {formatDuration(timing.duration_ms)}</small>}
                    {isActiveStep && <small>正在接收后端实时事件</small>}
                  </section>
                </article>
              );
            })}
          </div>

          {selected && !showLiveTrack ? (
            <>
              <section className="rail-section evidence-rail">
                <div className="rail-section-title"><Database size={16} /><strong>检索证据</strong><span>{String(selected.retrieval_mode).toUpperCase()}</span></div>
                {(selected.evidence_snippets || []).map((item) => (
                  <details key={item.evidence_id}>
                    <summary><code>{item.evidence_id}</code><span>{item.title}</span></summary>
                    <p>{item.snippet}</p>
                    {item.source_id && <small>来源：{item.source_id}</small>}
                  </details>
                ))}
              </section>

              <section className={`rail-section review-gate ${selected.review?.approved ? "approved" : "attention"}`}>
                <div className="rail-section-title">
                  {selected.review?.approved ? <ShieldCheck size={16} /> : <AlertTriangle size={16} />}
                  <strong>审核闸门</strong><span>{selected.review?.status || "待审核"}</span>
                </div>
                <dl>
                  <div><dt>候选回答</dt><dd>{selected.review?.candidate_rejected ? "已驳回" : "已通过"}</dd></div>
                  <div><dt>纠偏重生</dt><dd>{selected.review?.revision_applied ? "已应用" : "无需应用"}</dd></div>
                  <div><dt>引用闭合</dt><dd>{selected.review?.evidence_ids?.length || selected.evidence_ids?.length || 0} 条有效</dd></div>
                </dl>
                {(selected.review?.risk_points || []).slice(0, 2).map((item) => <p className="rail-warning" key={item}>{item}</p>)}
                <p className="rail-boundary">{selected.review?.degradation_notice}</p>
              </section>

              <section className="rail-section decision-rail">
                <div className="rail-section-title"><Target size={16} /><strong>学习决策</strong><span>{selected.next_action}</span></div>
                <p>{selected.practice_task}</p>
                <button type="button" onClick={() => setQuestion(selected.follow_up_question)}>
                  <MessageSquare size={14} />采用 Agent 建议追问
                </button>
              </section>

              {selected.generation_audit && Object.keys(selected.generation_audit).length > 0 && (
                <section className="rail-audit">
                  <span>模型 {selected.generation_audit.model || "Mock"}</span>
                  <span>{selected.generation_audit.latency_ms ?? 0} ms</span>
                  <span>{selected.generation_audit.outcome || selected.generation_mode}</span>
                </section>
              )}
            </>
          ) : (
            <section className="rail-placeholder">
              {showLiveTrack ? <Activity className="spin" size={22} /> : <Workflow size={22} />}
              <strong>{showLiveTrack ? "正在构建本轮证据链" : "提交首个问题后显示完整证据链"}</strong>
              <p>{showLiveTrack
                ? "检索依据、审核结论和学习决策将在对应 Agent 完成后统一呈现。"
                : "这里将同步展示每个 Agent 的输入输出、检索依据、审核结论和后续决策。"}</p>
            </section>
          )}
        </aside>}
      </div>
    </div>
  );
}

function formatGenerationMode(mode) {
  return {
    llm: "真实 LLM 生成",
    "mock-template": "模板兜底生成",
    "mock-template-fallback": "LLM 失败，已自动回退",
    "mock-template-stable": "稳定模板生成，LLM 问答可用",
    "review-template-fallback": "LLM 候选被驳回，模板重生",
  }[mode] || mode;
}

function Report({ report, onNext, onExport }) {
  const [activeReportSection, setActiveReportSection] = useState("overview");
  if (!report) return <EmptyState text="请先运行 Agent 管线。" />;
  const mastery = Math.max(report.diagnosis_score, 8);
  const blind = Math.max(100 - report.diagnosis_score, 8);
  const latestFeedback = report.feedback_history?.[report.feedback_history.length - 1];
  const currentAction = latestFeedback?.next_action || report.recommended_action;
  return (
    <div className="view report-view">
      <header className="page-intro report-page-intro">
        <div><p className="eyebrow">学情报告</p><h2>{report.profile.name} 的训练决策报告</h2><p>汇总诊断结果、证据审核、资源难度、反馈表现与下一步训练动作。</p></div>
        <button className="secondary" onClick={onExport}><Download size={17} />导出学情报告</button>
      </header>
      <section className="report-summary" aria-label="学情结论摘要">
        <div className="report-score"><span>诊断得分</span><strong>{report.diagnosis_score}</strong><small>/100</small></div>
        <div><span>知识盲区</span><strong>{report.knowledge_blind_spots.length} 项</strong><small>{report.knowledge_blind_spots.slice(0, 2).join(" · ")}</small></div>
        <div><span>资源难度</span><strong>{report.resource_difficulty_match.resource_difficulty}</strong><small>画像与诊断共同匹配</small></div>
        <div className="report-next-action"><span>下一步动作</span><strong>{currentAction}</strong><small>{latestFeedback ? `反馈 ${latestFeedback.feedback_score} 分后更新` : "等待反馈测试验证"}</small></div>
      </section>
      <div className="decision-flow" aria-label="动态学习决策链">
        <span>诊断 <strong>{report.diagnosis_score}</strong></span><ArrowRight size={16} />
        <span>反馈 <strong>{latestFeedback?.feedback_score ?? "待完成"}</strong></span><ArrowRight size={16} />
        <span>决策 <strong>{currentAction}</strong></span>
      </div>
      <div className="report-tabs" role="tablist" aria-label="报告内容分类">
        <button type="button" role="tab" aria-selected={activeReportSection === "overview"} className={activeReportSection === "overview" ? "active" : ""} onClick={() => setActiveReportSection("overview")}><BarChart3 size={16} /><strong>学习概览</strong><span>掌握度、盲区与路径</span></button>
        <button type="button" role="tab" aria-selected={activeReportSection === "review"} className={activeReportSection === "review" ? "active" : ""} onClick={() => setActiveReportSection("review")}><ShieldCheck size={16} /><strong>审核结论</strong><span>证据充分性与边界</span></button>
        <button type="button" role="tab" aria-selected={activeReportSection === "records"} className={activeReportSection === "records" ? "active" : ""} onClick={() => setActiveReportSection("records")}><History size={16} /><strong>迭代记录</strong><span>{(report.guided_inquiries?.length || 0) + (report.feedback_history?.length || 0)} 条过程记录</span></button>
      </div>
      <div className="report-grid">
        {activeReportSection === "overview" && <>
        <article className="panel">
          <h3>知识掌握</h3>
          <div className="bar"><span style={{ width: `${mastery}%` }}>掌握 {report.diagnosis_score}%</span></div>
          <div className="bar weak"><span style={{ width: `${blind}%` }}>盲区 {100 - report.diagnosis_score}%</span></div>
        </article>
        <article className="panel">
          <h3>知识盲区</h3>
          <div className="chips">{report.knowledge_blind_spots.map((point) => <span key={point}>{point}</span>)}</div>
        </article>
        <article className="panel">
          <h3>资源难度匹配轨迹</h3>
          <DifficultyMatchChart
            score={report.diagnosis_score}
            difficulty={report.resource_difficulty_match.resource_difficulty}
          />
          <p>{report.resource_difficulty_match.reason}</p>
          <p className="metric-note">曲线为系统规则映射示意，正式难度适配准确率以专家复核结果为准。</p>
        </article>
        <article className="panel">
          <h3>推荐学习路径规划图</h3>
          <LearningPathGraph items={report.recommended_learning_path} />
        </article>
        </>}
        {activeReportSection === "review" && <article className="panel wide report-review-panel">
          <h3>专家审核与下一步</h3>
          <p>{report.agent_review.status}</p>
          {report.agent_review.evidence_sufficiency && (
            <p><strong>证据充分性：</strong>{formatEvidenceSufficiency(report.agent_review.evidence_sufficiency)}</p>
          )}
          {report.agent_review.degradation_notice && <p>{report.agent_review.degradation_notice}</p>}
          {report.agent_review.unsupported_claims?.length > 0 && (
            <p><strong>已拦截越界声明：</strong>{report.agent_review.unsupported_claims.join("；")}</p>
          )}
          <p><strong>{report.recommended_action}</strong>：{report.next_training_suggestion}</p>
        </article>}
        {activeReportSection === "records" && report.guided_inquiries?.length > 0 && (
          <article className="panel wide report-inquiries">
            <div className="section-heading compact">
              <div><p className="eyebrow">动态生成证据</p><h3>启发式追问记录</h3></div>
              <span>{report.guided_inquiries.length} 轮</span>
            </div>
            {report.guided_inquiries.slice(-3).map((item) => (
              <div className="report-inquiry-row" key={item.interaction_id}>
                <div className="report-record-main">
                  <strong>{item.question}</strong>
                  <p>{summarizeStructuredText(item.answer)}</p>
                  <details className="report-record-detail">
                    <summary>展开完整回答</summary>
                    <StructuredMarkdown compact>{item.answer}</StructuredMarkdown>
                  </details>
                </div>
                <dl>
                  <div><dt>生成</dt><dd>{formatGenerationMode(item.generation_mode)}</dd></div>
                  <div><dt>检索</dt><dd>{String(item.retrieval_mode || "bm25").toUpperCase()} · {item.knowledge_source}</dd></div>
                  <div><dt>证据</dt><dd>{item.evidence_ids?.join("、") || "无"}</dd></div>
                  <div><dt>审核</dt><dd>{item.review?.status || "未记录"}</dd></div>
                </dl>
              </div>
            ))}
          </article>
        )}
        {activeReportSection === "records" && report.feedback_history?.length > 0 && (
          <article className="panel wide report-inquiries">
            <div className="section-heading compact">
              <div><p className="eyebrow">动态决策留痕</p><h3>反馈迭代记录</h3></div>
              <span>{report.feedback_history.length} 轮</span>
            </div>
            {report.feedback_history.slice(-3).map((item, index) => (
              <div className="report-inquiry-row" key={`${item.created_at || "feedback"}-${index}`}>
                <div className="report-record-main"><strong>反馈得分 {item.feedback_score}%</strong><p>{summarizeStructuredText(item.explanation || item.self_feedback)}</p></div>
                <dl>
                  <div><dt>决策动作</dt><dd>{item.next_action}</dd></div>
                  <div><dt>学习者反馈</dt><dd>{item.self_feedback || "未填写"}</dd></div>
                  <div><dt>更新路径</dt><dd>{item.updated_learning_path?.slice(-2).join(" → ") || "已更新"}</dd></div>
                </dl>
              </div>
            ))}
          </article>
        )}
        {activeReportSection === "records" && !report.guided_inquiries?.length && !report.feedback_history?.length && (
          <div className="report-empty-records"><History size={24} /><strong>暂无迭代记录</strong><span>完成动态追问或反馈测试后，过程记录将出现在这里。</span></div>
        )}
      </div>
      <div className="actions">
        <button className="primary" onClick={onNext}>进入反馈测试<ArrowRight size={17} /></button>
      </div>
    </div>
  );
}

function DifficultyMatchChart({ score, difficulty }) {
  const difficultyValue = {
    降维入门: 45,
    巩固提升: 68,
    进阶挑战: 88,
  }[difficulty] || 65;
  const targetValue = Math.min(96, Math.max(difficultyValue + 10, score + 15));
  const points = [
    { label: "诊断水平", value: Math.max(0, Math.min(100, score)), x: 44 },
    { label: difficulty || "当前资源", value: difficultyValue, x: 170 },
    { label: "下一挑战", value: targetValue, x: 296 },
  ];
  const y = (value) => 118 - value * 0.82;

  return (
    <div className="difficulty-chart">
      <svg viewBox="0 0 340 150" role="img" aria-label="学习者诊断水平、当前资源难度和下一阶段挑战的匹配轨迹">
        {[20, 60, 100].map((value) => (
          <g key={value}>
            <line x1="24" x2="318" y1={y(value)} y2={y(value)} />
            <text x="2" y={y(value) + 4}>{value}</text>
          </g>
        ))}
        <polyline points={points.map((point) => `${point.x},${y(point.value)}`).join(" ")} />
        {points.map((point) => (
          <g key={point.label}>
            <circle cx={point.x} cy={y(point.value)} r="6" />
            <text className="chart-value" x={point.x} y={y(point.value) - 11}>{point.value}</text>
            <text className="chart-label" x={point.x} y="142">{point.label}</text>
          </g>
        ))}
      </svg>
    </div>
  );
}

function LearningPathGraph({ items = [] }) {
  return (
    <div className="learning-path-graph" aria-label="推荐学习路径">
      {items.map((item, index) => (
        <div className="path-node" key={item}>
          <span>{String(index + 1).padStart(2, "0")}</span>
          <div>
            <small>STEP {String(index + 1).padStart(2, "0")}</small>
            <strong>{item}</strong>
          </div>
        </div>
      ))}
    </div>
  );
}

function formatEvidenceSufficiency(value) {
  return {
    sufficient_for_training: "满足训练用途",
    limited: "证据有限，已降级",
    insufficient: "证据不足",
  }[value] || value;
}

function Feedback({ health, resources, answers, setAnswers, result, loading, onSubmit }) {
  const [selfFeedback, setSelfFeedback] = useState("我对热氧老化和滑动磨损耦合关系还不够熟。");
  if (!resources) return <EmptyState text="请先生成个性化资源。" />;
  const answeredCount = resources.graded_quiz.filter((question) => answers[question.id] !== undefined).length;
  return (
    <div className="view feedback-view">
      <header className="page-intro">
        <div><p className="eyebrow">交互反馈与动态决策更新</p><h2>用训练表现更新下一步决策</h2><p>系统根据正确率和学习者反馈决定降维解释、继续巩固、补充案例或进阶挑战。</p></div>
        <div className="feedback-progress"><span>答题进度</span><strong>{answeredCount}/{resources.graded_quiz.length}</strong><progress value={answeredCount} max={resources.graded_quiz.length} /></div>
      </header>
      {result && (
        <>
          {result.restored && (
            <p className="feedback-history-note">
              已恢复最近一次反馈决策。下方得分仅代表上轮结果，本轮答题进度从 0 开始重新计算。
            </p>
          )}
          <section className="feedback-decision" aria-label={result.restored ? "最近一次反馈决策" : "动态决策结果"}>
            <div className={`feedback-score ${result.restored ? "restored" : ""}`}><span>{result.restored ? "上轮反馈得分" : "反馈得分"}</span><strong>{result.feedback_score}</strong><small>/100</small></div>
            <div><span>{result.restored ? "上轮下一动作" : "下一动作"}</span><strong>{result.next_action}</strong><p>{result.explanation}</p></div>
            <div><span>{result.restored ? "上轮更新后的学习路径" : "更新后的学习路径"}</span><ol>{result.updated_learning_path.slice(-3).map((item) => <li key={item}>{item}</li>)}</ol></div>
          </section>
        </>
      )}
      <div className="question-list">
        {resources.graded_quiz.map((question, index) => (
          <article className="card question" key={question.id}>
            <h3>{index + 1}. {question.question}</h3>
            <p className="muted">层级：{question.level}；知识点：{question.knowledge_point}</p>
            <div className="options">
              {question.options.map((option) => (
                <button
                  key={option}
                  className={answers[question.id] === option ? "selected" : ""}
                  aria-pressed={answers[question.id] === option}
                  onClick={() => setAnswers((current) => ({ ...current, [question.id]: option }))}
                >
                  {option}
                </button>
              ))}
            </div>
          </article>
        ))}
      </div>
      <section className="feedback-submit-panel">
        <label>学习者反馈<textarea value={selfFeedback} onChange={(e) => setSelfFeedback(e.target.value)} /></label>
        <div><span>{answeredCount === resources.graded_quiz.length ? "已完成全部题目，可以更新学习路径。" : `还有 ${resources.graded_quiz.length - answeredCount} 道题未作答。`}</span><button className="primary" disabled={loading || answeredCount !== resources.graded_quiz.length} title={answeredCount !== resources.graded_quiz.length ? "请先完成全部反馈题" : "提交反馈并更新路径"} onClick={() => onSubmit(selfFeedback)}>
          {loading ? <><Activity className="spin" size={17} />更新决策中...</> : <><RefreshCw size={17} />提交反馈并更新路径</>}
        </button></div>
        {loading && (
          <p className="muted">
            {health?.llm_resource_generation_enabled
              ? "正在重新检索、调用 LLM 生成资源并执行审核纠偏，通常需要 30-60 秒。"
              : "正在重新检索、更新稳定模板资源并执行审核纠偏，通常数秒内完成。"}
          </p>
        )}
      </section>
    </div>
  );
}

function EmptyState({ text }) {
  return <div className="view empty"><h2>{text}</h2></div>;
}

const rootElement = document.getElementById("root");
const root = globalThis.__aviationTrainingRoot || createRoot(rootElement);
globalThis.__aviationTrainingRoot = root;
root.render(<App />);
