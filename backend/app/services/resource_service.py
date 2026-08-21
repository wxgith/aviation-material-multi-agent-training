import re
from difflib import SequenceMatcher

from app.models.schemas import DiagnosisResult, TrainingDomain
from app.llm.client import maybe_generate_resources_with_llm
from app.services.data_loader import get_knowledge_domain, get_questions_by_domain


PERSONALIZATION_STRATEGIES = {
    "undergraduate": {
        "label": "现象引导型",
        "explanation_style": "从可观察现象和基础术语开始，逐步连接工况、材料变化与证据。",
        "practice_focus": "识别、测量和规范描述典型损伤，不要求直接给出确定性机理。",
        "assessment_focus": "基础概念、图像观察和证据链顺序",
        "headings": (
            "1. 从可观察损伤现象开始",
            "2. 用三步法建立基础机理链",
            "3. 按证据顺序完成判读表达",
        ),
        "record_template": ["工况参数", "损伤位置", "可见形貌", "测量尺度", "可能原因", "待补检测"],
        "extra_step": "先对照示例图识别裂纹、剥落或磨痕，再填写观察记录，暂不跳到确定性机理结论。",
        "extra_constraint": "首次训练只要求完成现象识别和基础证据链，不以复杂机理术语数量评分。",
        "case_outputs": ["损伤类型判断", "三项可见证据", "基础机理链", "补充表征建议"],
        "quiz_levels": ["基础", "基础", "提升", "提升", "进阶"],
    },
    "graduate": {
        "label": "科研证据链型",
        "explanation_style": "围绕变量控制、定量指标、多源表征和不确定性建立可复核机理链。",
        "practice_focus": "形成实验变量表、对照组、重复性要求和观察事实与机理假设的分层表达。",
        "assessment_focus": "机理推断、实验设计、定量交叉验证和外推边界",
        "headings": (
            "1. 定义研究问题、变量与边界",
            "2. 建立可证伪的损伤机理链",
            "3. 用定量记录和多源表征交叉验证",
        ),
        "record_template": ["自变量与水平", "控制变量", "重复次数", "定量指标", "形貌证据", "机理假设", "不确定性"],
        "extra_step": "建立自变量、控制变量和重复试验表，分别记录观察事实、定量结果与待验证机理假设。",
        "extra_constraint": "趋势结论必须限定在已测工况范围内，并报告重复性、异常值和证据缺口。",
        "case_outputs": ["变量与对照设计", "定量趋势", "多源证据链", "竞争机理", "不确定性与外推边界"],
        "quiz_levels": ["基础", "提升", "提升", "进阶", "进阶"],
    },
    "maintenance": {
        "label": "检查决策型",
        "explanation_style": "以检查流程、标准化记录、风险分级和升级报告边界组织知识。",
        "practice_focus": "完成可追溯检查记录和后续检测建议，不越权替代适航放行。",
        "assessment_focus": "损伤判读、检查遗漏、记录规范和处置边界",
        "headings": (
            "1. 明确检查任务与风险边界",
            "2. 从损伤征象定位可能影响因素",
            "3. 形成可复核记录与升级建议",
        ),
        "record_template": ["部件与区域", "服役信息", "损伤征象", "尺寸与位置", "图像尺度参照", "图像编号", "复检项目", "升级报告"],
        "extra_step": "按照检查单记录部件区域、尺寸、图像编号和异常等级；证据不足时提交复检或升级报告。",
        "extra_constraint": "所有处置内容均为训练建议，真实维修必须执行适用手册、工卡和授权放行流程。",
        "case_outputs": ["损伤征象描述", "检查记录", "风险提示", "复检项目", "升级报告建议"],
        "quiz_levels": ["基础", "基础", "提升", "情景决策", "情景决策"],
    },
}


def generate_resources(
    profile: dict,
    domain: TrainingDomain,
    diagnosis: DiagnosisResult,
    retrieved_chunks: list[dict],
    learning_goal: str,
    feedback_action: str | None = None,
    correction_guidance: list[str] | None = None,
) -> dict:
    knowledge = get_knowledge_domain(domain)
    difficulty = _resource_difficulty(profile["self_level"], diagnosis.score)
    evidence_ids = [chunk["id"] for chunk in retrieved_chunks]
    strategy_id, strategy = _personalization_strategy(profile)

    lecture = {
        "title": f"{knowledge['title']}个性化讲义",
        "difficulty": difficulty,
        "target": learning_goal,
        "sections": [
            {
                "heading": strategy["headings"][0],
                "content": _lecture_intro(profile, diagnosis, strategy_id),
                "evidence_ids": evidence_ids[:2],
            },
            {
                "heading": strategy["headings"][1],
                "content": (
                    f"{_join_chunk_contents(retrieved_chunks[:3])} "
                    f"本画像训练要求：{strategy['explanation_style']}"
                ),
                "evidence_ids": evidence_ids[:3],
            },
            {
                "heading": strategy["headings"][2],
                "content": _evidence_expression(strategy_id),
                "evidence_ids": evidence_ids,
            },
        ],
    }

    practical_guide = {
        "title": _practice_title(domain),
        "steps": [strategy["extra_step"]] + _practice_steps(domain),
        "record_template": strategy["record_template"],
        "constraints": [
            "必须说明实验或检查边界条件。",
            "训练建议不能替代真实适航放行结论。",
            "形貌判断需尽量结合多源表征。",
            strategy["extra_constraint"],
        ],
        "evidence_ids": evidence_ids,
    }

    graded_quiz = _build_graded_quiz(
        domain, diagnosis.weak_points, strategy["quiz_levels"], strategy["assessment_focus"]
    )
    case_task = _build_case_task(
        domain, diagnosis.weak_points, retrieved_chunks, strategy["case_outputs"]
    )

    base_resources = {
        "personalized_lecture": lecture,
        "practical_guide": practical_guide,
        "graded_quiz": graded_quiz,
        "case_task": case_task,
        "difficulty_match": {
            "diagnosis_level": diagnosis.level,
            "resource_difficulty": difficulty,
            "reason": f"{profile['learner_type']}当前得分 {diagnosis.score}，资源优先覆盖 {'、'.join(diagnosis.weak_points)}。",
        },
        "personalization": {
            "strategy_id": strategy_id,
            "strategy_label": strategy["label"],
            "learner_type": profile["learner_type"],
            "explanation_style": strategy["explanation_style"],
            "practice_focus": strategy["practice_focus"],
            "assessment_focus": strategy["assessment_focus"],
        },
        "evidence_boundary": {
            "observation": "可直接引用已检索片段和已审核实验资产中的观察记录。",
            "parameter_fact": "仅使用资产工况字段或检索片段中明确记录的数值，不补齐缺失参数。",
            "mechanism_inference": "机理只能表述为受证据支持的解释或待验证假设，不能由单张图像直接确定。",
            "maintenance_decision": "仅提供训练性检查建议，不替代维修手册、工卡、适航或授权放行。",
        },
    }
    _apply_iteration_guidance(
        base_resources,
        feedback_action=feedback_action,
        correction_guidance=correction_guidance or [],
    )
    return maybe_generate_resources_with_llm(
        profile=profile,
        domain=domain,
        diagnosis=diagnosis,
        retrieved_chunks=retrieved_chunks,
        learning_goal=learning_goal,
        base_resources=base_resources,
    )


def _apply_iteration_guidance(
    resources: dict,
    feedback_action: str | None,
    correction_guidance: list[str],
) -> None:
    if feedback_action == "降维解释":
        resources["difficulty_match"]["resource_difficulty"] = "降维入门"
        resources["personalized_lecture"]["difficulty"] = "降维入门"
        resources["personalized_lecture"]["sections"].insert(
            0,
            {
                "heading": "反馈补充：直观概念重建",
                "content": "先从可观察的裂纹、剥落、磨耗现象出发，再连接环境作用、材料变化和表征证据。",
                "evidence_ids": resources["case_task"].get("evidence_ids", [])[:2],
            },
        )
    elif feedback_action == "补充案例":
        resources["case_task"]["brief"] += " 请再对比一个工况相近但损伤形貌不同的样例，说明判读差异。"
        resources["case_task"]["expected_output"].append("对比案例差异表")
    elif feedback_action == "继续巩固":
        resources["case_task"]["expected_output"].append("完整证据链复盘")
    elif feedback_action == "进阶挑战":
        resources["difficulty_match"]["resource_difficulty"] = "进阶挑战"
        resources["personalized_lecture"]["difficulty"] = "进阶挑战"
        resources["case_task"]["brief"] += " 进一步讨论多因素耦合、边界条件变化和结论不确定性。"

    if correction_guidance:
        resources["review_correction_applied"] = correction_guidance


def _resource_difficulty(self_level: str, score: int) -> str:
    if score < 60 or self_level == "低":
        return "降维入门"
    if score < 85:
        return "巩固提升"
    return "进阶挑战"


def _personalization_strategy(profile: dict) -> tuple[str, dict]:
    learner_type = profile.get("learner_type", "")
    profile_id = profile.get("profile_id", "")
    if profile_id == "grad_materials" or "研究生" in learner_type:
        strategy_id = "graduate"
    elif profile_id == "maintenance_new" or "机务" in learner_type or "维修" in learner_type:
        strategy_id = "maintenance"
    else:
        strategy_id = "undergraduate"
    return strategy_id, PERSONALIZATION_STRATEGIES[strategy_id]


def _lecture_intro(
    profile: dict, diagnosis: DiagnosisResult, strategy_id: str
) -> str:
    if strategy_id == "undergraduate":
        return (
            "先不急着背复杂术语，把损伤看成“材料状态变化 + 外部工况作用 + 可观察证据”。"
            f"本次重点补齐 {'、'.join(diagnosis.weak_points)}。"
        )
    if strategy_id == "graduate":
        return (
            f"围绕 {'、'.join(diagnosis.weak_points)} 明确研究问题、自变量、控制变量和响应指标，"
            "再区分实验观察、定量结果、机理假设与外推边界。"
        )
    return (
        f"围绕 {'、'.join(diagnosis.weak_points)} 建立检查清单，先记录部件区域、尺寸和图像证据，"
        "再提出复检与升级报告建议，避免越权形成放行结论。"
    )


def _evidence_expression(strategy_id: str) -> str:
    expressions = {
        "undergraduate": "按“工况 - 看到了什么 - 如何测量 - 可能原因 - 还需什么证据”完成回答，先保证观察和推断不混淆。",
        "graduate": "按“变量设计 - 定量结果 - 形貌证据 - 竞争机理 - 不确定性 - 外推边界”形成可复核科研表达。",
        "maintenance": "按“部件区域 - 损伤征象 - 尺寸位置 - 证据编号 - 风险提示 - 复检或升级报告”形成规范记录。",
    }
    return expressions[strategy_id]


def _join_chunk_contents(chunks: list[dict]) -> str:
    excerpts: list[tuple[str, str, str]] = []
    for chunk in chunks:
        excerpt = _chunk_excerpt(chunk)
        normalized = re.sub(r"[^\w\u4e00-\u9fff]", "", excerpt).lower()
        if not normalized:
            continue
        if any(
            SequenceMatcher(None, normalized, existing).ratio() >= 0.78
            for _, _, existing in excerpts
        ):
            continue
        excerpts.append((str(chunk.get("id", "未编号片段")), excerpt, normalized))

    return " ".join(
        f"证据{index}（{chunk_id}）：{excerpt}"
        for index, (chunk_id, excerpt, _) in enumerate(excerpts, start=1)
    )


def _chunk_excerpt(chunk: dict, max_chars: int = 220) -> str:
    content = str(chunk.get("content", "")).strip()
    title = str(chunk.get("title", "知识片段")).strip()
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    table_lines = [line for line in lines if line.startswith("|") and line.endswith("|")]

    if table_lines:
        fields = [
            field.strip()
            for field in table_lines[0].strip("|").split("|")
            if field.strip()
        ]
        field_labels = {
            "aging_condition_id": "老化条件编号",
            "set_temperature_C": "设定温度",
            "duration_h": "持续时长",
            "atmosphere": "环境气氛",
            "qc_flag": "质控状态",
            "record_id": "记录编号",
            "sample_id": "样品编号",
            "normal_load_N": "法向载荷",
            "sliding_speed_m_s": "滑动速度",
            "friction_coefficient": "摩擦系数",
            "mass_loss_mg": "质量损失",
            "wear_rate_mg_per_Nm": "磨损率",
        }
        readable_fields = [field_labels.get(field, field) for field in fields[:6]]
        return f"《{title}》记录了{'、'.join(readable_fields)}等结构化字段，可用于工况与结果对照。"

    plain_text = re.sub(r"[`*_#>]", "", " ".join(lines))
    plain_text = re.sub(r"\s+", " ", plain_text).strip()
    if len(plain_text) <= max_chars:
        return plain_text
    shortened = plain_text[:max_chars].rsplit("。", 1)[0].strip()
    if len(shortened) < max_chars // 2:
        shortened = plain_text[:max_chars].rstrip("，；：,. ")
    return f"{shortened}……"


def _practice_title(domain: TrainingDomain) -> str:
    titles = {
        "tire": "胎面损伤检查实操指南",
        "brake": "刹车片摩擦磨损检查实操指南",
        "composite": "复合材料板冲击损伤判读实操指南",
    }
    return titles[domain]


def _practice_steps(domain: TrainingDomain) -> list[str]:
    steps = {
        "tire": [
            "读取样品或部件背景，记录起降次数、热暴露或老化条件。",
            "观察胎面裂纹、剥落、磨耗和局部撕裂区域，标注图像尺度。",
            "测量裂纹长度、剥落面积和磨耗深度，形成损伤证据表。",
            "结合热氧老化和滑动磨损知识片段，写出可能机理和补充检测建议。",
        ],
        "brake": [
            "读取制动能量、温度峰值和摩擦系数曲线。",
            "标注稳定段、衰退段和异常波动区间。",
            "观察沟槽、剥落坑、热裂纹和氧化膜残留。",
            "形成工况、界面变化、性能变化和风险判断的证据链。",
        ],
        "composite": [
            "记录冲击能量、冲击位置和外观凹坑区域。",
            "读取无损检测图像，圈定疑似分层或内部异常范围。",
            "比较外观损伤与内部损伤范围差异。",
            "写出损伤类型、扩展风险和后续检测建议。",
        ],
    }
    return steps[domain]


def _build_graded_quiz(
    domain: TrainingDomain,
    weak_points: list[str],
    levels: list[str],
    assessment_focus: str,
) -> list[dict]:
    questions = get_questions_by_domain(domain)
    weak_first = sorted(
        questions,
        key=lambda item: 0 if item["knowledge_point"] in weak_points else 1,
    )
    quiz = []
    for index, question in enumerate(weak_first[:5]):
        quiz.append(
            {
                "id": f"feedback-{question['id']}",
                "level": levels[index],
                "question": question["question"],
                "options": question["options"],
                "answer": question["answer"],
                "knowledge_point": question["knowledge_point"],
                "explanation": question["explanation"],
                "training_focus": assessment_focus,
            }
        )
    return quiz


def _build_case_task(
    domain: TrainingDomain,
    weak_points: list[str],
    chunks: list[dict],
    expected_output: list[str],
) -> dict:
    cases = {
        "tire": "某航空轮胎胎面经历热氧老化后进行滑动磨损试验，局部出现沿滑动方向裂纹和片状剥落。请判断损伤类型、主导证据和可能机理。",
        "brake": "某航空刹车片在高能制动后摩擦系数下降，表面出现热裂纹和氧化膜残留。请分析失效机理链条。",
        "composite": "某复合材料板低速冲击后表面仅轻微凹陷，但超声 C 扫出现椭圆异常区域。请判断损伤类型和检测建议。",
    }
    return {
        "title": "案例分析任务",
        "brief": cases[domain],
        "focus_points": weak_points,
        "expected_output": expected_output,
        "evidence_ids": [chunk["id"] for chunk in chunks[:3]],
    }
