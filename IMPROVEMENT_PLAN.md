# 完善目标与冻结计划

## 1. 当前版本定位

当前推荐版本为“真实工程证据增强冻结版”：

- 前端：React + Vite；
- 后端：FastAPI；
- 学习过程持久化：MySQL；
- 知识检索：Elasticsearch；
- 生成模式：Qwen OpenAI-compatible 真实调用可选，mock/template 自动兜底；
- 兜底模式：本地 JSON fallback；
- 答辩文件：`submission_materials/03_答辩PPT材料/航空工程材料多智能体训练系统_答辩PPT_最终冻结版.pptx`。

正式演示推荐 SQL + Elasticsearch，并在智能训练工作台演示一次已验证的 Qwen 动态追问；现场网络或模型异常时保持 SQL + ES 并自动回退 mock/template，必要时再切换完整 JSON 本地兜底。

## 2. 当前验收基线

| 维度 | 当前结果 |
| --- | --- |
| 业务闭环 | 诊断 -> 6 Agent -> ES 检索 -> 资源 -> 报告 -> 导出 -> 反馈可运行 |
| 工程组件 | MySQL、Elasticsearch、健康检查与 JSON fallback 已接入 |
| 知识库 | ES 索引 `aviation_material_knowledge` 共 1,766 条 |
| 团队实验资产 | 4 个轮胎专题、53 项已审核资产 |
| 公开文献实验卡 | 5/5 已人工复核，不宣称团队实测 |
| 自动测评 | 核心 50 条、第二批 20 条、文献专项 10 条均通过 |
| 后端测试 | 86 passed |
| 前端构建 | production build passed |
| PPT | 10 页冻结版，模板一致性与溢出检查通过 |
| 提交包 | 186 个文件完成 SHA-256 登记与校验 |

最新机器可读验收结果：

- `outputs/acceptance/acceptance_latest.json`；
- `submission_materials/07_接口测试与单元测试/最终自动验收报告.json`；
- `submission_materials/SUBMISSION_MANIFEST.json`。

## 3. 第一批与第二批交互补强

1. FastAPI 异步任务通过 SSE 推送真实 Agent 开始、完成、纠偏和保存事件，SSE 异常时前端自动轮询同一任务。
2. 支持合作式停止、失败重试和模型异常模板回退，不重复执行已经创建的任务。
3. 浏览器刷新后自动续接原任务；仅保存任务 ID 和类型，成功恢复后清除，30 分钟自动过期。
4. 任务响应新增管线总耗时和逐 Agent 耗时，协同页与动态问答右侧轨迹展示真实执行状态。
5. 历史训练会话支持关键词、会话 ID 和训练方向筛选，并能完整恢复画像、资源、报告和问答。
6. 关键状态使用检索蓝、成功绿、审核橙和异常红，桌面与 390px 移动端均完成布局检查。
7. 保持现有 API、数据库结构、演示案例、SQL + ES 工程模式和 JSON/mock fallback 行为不变。

## 4. 仍需人工完成

以下事项无法由代码自动替代：

1. 在正式 PPT 中核对学校、团队名称、答辩人、指导教师和比赛名称。
2. 由领域专家完成 50 条测评抽检评分并签字，正式给出专业正确率、幻觉率和难度适配准确率。
3. 按 `DEMO_SCRIPT.md` 录制 10 分钟以内演示视频，并检查声音、分辨率和鼠标操作节奏。
4. 填写比赛报名表，核对提交邮箱、截止时间和官方压缩包命名。
5. 将报名表、演示视频和专家签字材料放入提交包后，重新生成并验证 SHA-256 清单。
6. 在另一台电脑或干净目录完成一次解压、启动和演示检查。

## 5. 比赛前不建议继续加入

- 无评测约束地更换主模型或提示词；
- 在线 BGE 模型下载或强依赖向量服务；
- ES kNN 索引迁移；
- Alembic 数据库迁移改造；
- 用户权限、教师后台和长期课程管理；
- 内置 PDF 报告引擎。

这些能力有长期价值，但会增加网络、模型、迁移和部署风险，不适合进入当前比赛冻结版。

## 6. 比赛后建议路线

1. 在独立分支验证本地 BGE embedding 和向量/混合检索质量。
2. 扩大真实 LLM 专项评测样本，并在独立分支验证 token 级流式输出。
3. 引入 Alembic、用户权限、审计日志和数据匿名化工具。
4. 扩充航空制动材料与复合材料的授权实验数据。
5. 增加教师端课程编排、班级统计和长期学习轨迹。
6. 在保持 Markdown 导出的同时提供可选 PDF 报告。

## 7. 最终操作命令

```powershell
cd D:\agents
.\scripts\check_environment.ps1
.\scripts\run_acceptance.ps1
.\scripts\generate_submission_manifest.ps1
.\scripts\verify_submission_manifest.ps1
```

四个命令全部通过后，可以冻结源码和提交材料；若之后加入或修改任何提交文件，只需重新运行后两个清单命令。
