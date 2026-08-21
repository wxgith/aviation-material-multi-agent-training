# Frontend

React + Vite 前端负责展示比赛演示流程：画像输入、学情诊断、Agent 时间线、资源生成、学情报告和反馈迭代。

## 启动

```powershell
cd D:\agents\frontend
npm install
npm run dev
```

默认访问：

```text
http://localhost:5173
```

## API 配置

复制 `.env.example` 为 `.env` 后可修改：

```text
VITE_API_BASE=http://localhost:8000/api
```

## 页面结构

- 首页：系统定位、LLM 模式、知识库状态、多智能体闭环
- 画像输入：选择内置画像或调整学习目标
- 加载演示案例：自动填充本科低年级学生、航空轮胎方向、学习目标和诊断答案
- 学情诊断：从后端获取方向化诊断题并提交评分
- 多智能体协同：展示 6 个 Agent 的输入、输出、置信度和依据片段
- 资源生成：展示讲义、实操指南、分阶测试题和案例任务
- 学情报告：展示得分、盲区、难度匹配、学习路径和审核意见，并支持导出 Markdown 报告
- 反馈迭代：提交反馈测试并展示动态决策结果

## 构建验证

```powershell
cd D:\agents\frontend
npm run build
```
