# 评委从这里开始

本项目有两种运行方式。第一次检查建议使用 **便携演示模式**，它不需要 Docker、MySQL、Elasticsearch、DBeaver 或模型密钥。

## 最简单的运行方法

### 第一步：安装两个基础软件

请安装：

1. Python 3.11
2. Node.js 20 LTS

安装后重新打开 PowerShell，运行：

```powershell
python --version
node --version
```

能看到版本号即可。

### 第二步：解压项目

将压缩包完整解压到一个较短的目录，例如：

```text
C:\agents-demo
```

不要直接在压缩包预览窗口中运行。

### 第三步：执行一条命令

在解压目录空白处按住 Shift 并单击鼠标右键，选择“在此处打开 PowerShell”，然后执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_mock_demo.ps1
```

第一次运行会联网下载 Python 和前端依赖，通常需要几分钟。完成后浏览器会打开：

- 系统界面：<http://127.0.0.1:5173>
- 后端状态：<http://127.0.0.1:8000/api/health>

## 推荐检查顺序

1. 点击“加载演示案例”。
2. 提交学情诊断。
3. 查看 6 个 Agent 的协同过程和证据 ID。
4. 查看讲义、实操指南、分阶测试题和案例任务。
5. 查看专家审核纠偏意见。
6. 打开学情报告并导出 Markdown 报告。
7. 完成反馈测试，查看动态学习决策。
8. 使用智能助手提出一个页面操作问题或专业问题。

## 没有 Docker 是否影响

不影响核心检查。系统会使用内置 JSON 知识库和 mock/template 生成，仍然可以完整运行诊断、Agent、资源、报告和反馈闭环。

没有 Docker 时无法现场查看 MySQL 数据表和 Elasticsearch 索引，但相关工程代码、自动测试、验收结果和部署说明都在项目中。需要进一步验证时，再阅读 [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)。

## 常见问题

### PowerShell 提示禁止运行脚本

请使用上面的完整命令，其中已经包含 `-ExecutionPolicy Bypass`，只对本次 PowerShell 运行生效。

### 提示找不到 Python

请安装 Python 3.11，并在安装界面勾选“Add Python to PATH”。

### 提示找不到 npm

请安装 Node.js 20 LTS，然后关闭并重新打开 PowerShell。

### 端口被占用

关闭旧的 Python、Uvicorn 或 Vite 窗口后重新执行；也可以按照 [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) 使用其他端口。

### 如何停止系统

```powershell
.\scripts\stop_project.ps1
```

## 自动验证

系统启动不是必须条件，也可直接运行无 Docker 验收：

```powershell
.\scripts\reviewer_verify.ps1 -Mode mock
```

该命令会验证画像、诊断、6 Agent、四类资源、学情报告导出和反馈决策。
