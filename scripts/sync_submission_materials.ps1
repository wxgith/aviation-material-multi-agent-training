param()

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

$copies = @(
    @("SYSTEM_DESIGN.md", "submission_materials/01_作品设计实现方案/SYSTEM_DESIGN.md"),
    @("docs/专家复核执行指南.md", "submission_materials/01_作品设计实现方案/专家复核执行指南.md"),
    @("docs/幻觉防控与知识溯源方案.md", "submission_materials/01_作品设计实现方案/幻觉防控与知识溯源方案.md"),
    @("docs/数据合规与隐私保护说明.md", "submission_materials/01_作品设计实现方案/数据合规与隐私保护说明.md"),
    @("docs/比赛方案逐项对照与补强记录.md", "submission_materials/01_作品设计实现方案/比赛方案逐项对照与补强记录.md"),
    @("docs/比赛验收证据索引.md", "submission_materials/01_作品设计实现方案/比赛验收证据索引.md"),
    @("docs/测试方案与评价指标.md", "submission_materials/01_作品设计实现方案/测试方案与评价指标.md"),
    @("docs/真实LLM接入与验收.md", "submission_materials/01_作品设计实现方案/真实LLM接入与验收.md"),
    @("docs/知识库构建与RAG检索方案.md", "submission_materials/01_作品设计实现方案/知识库构建与RAG检索方案.md"),
    @("docs/作品简介.md", "submission_materials/02_作品简介与创新点/作品简介.md"),
    @("docs/创新点与应用价值.md", "submission_materials/02_作品简介与创新点/创新点与应用价值.md"),
    @("PPT_OUTLINE.md", "submission_materials/03_答辩PPT材料/PPT_OUTLINE.md"),
    @("SCREENSHOT_GUIDE.md", "submission_materials/03_答辩PPT材料/SCREENSHOT_GUIDE.md"),
    @("docs/答辩PPT文案.md", "submission_materials/03_答辩PPT材料/答辩PPT文案.md"),
    @("docs/最终截图与录屏验收清单.md", "submission_materials/03_答辩PPT材料/最终截图与录屏验收清单.md"),
    @("DEMO_SCRIPT.md", "submission_materials/04_演示视频材料/DEMO_SCRIPT.md"),
    @("docs/演示视频讲稿.md", "submission_materials/04_演示视频材料/演示视频讲稿.md"),
    @("docs/录屏彩排清单.md", "submission_materials/04_演示视频材料/录屏彩排清单.md"),
    @("docs/录屏运行手册.md", "submission_materials/04_演示视频材料/录屏运行手册.md"),
    @("README.md", "submission_materials/05_系统运行与部署说明/README.md"),
    @("backend/README.md", "submission_materials/05_系统运行与部署说明/backend_README.md"),
    @("frontend/README.md", "submission_materials/05_系统运行与部署说明/frontend_README.md"),
    @("FINAL_RELEASE.md", "submission_materials/05_系统运行与部署说明/FINAL_RELEASE.md"),
    @("IMPROVEMENT_PLAN.md", "submission_materials/05_系统运行与部署说明/IMPROVEMENT_PLAN.md"),
    @("COMPETITION_DELIVERY_GUIDE.md", "submission_materials/05_系统运行与部署说明/COMPETITION_DELIVERY_GUIDE.md"),
    @("DEPLOYMENT_GUIDE.md", "submission_materials/05_系统运行与部署说明/DEPLOYMENT_GUIDE.md"),
    @("DEPLOYMENT_VALIDATION.md", "submission_materials/05_系统运行与部署说明/DEPLOYMENT_VALIDATION.md"),
    @("docs/DBeaver数据库查看说明.md", "submission_materials/05_系统运行与部署说明/DBeaver数据库查看说明.md"),
    @("docs/最终人工审核指南.md", "submission_materials/05_系统运行与部署说明/最终人工审核指南.md"),
    @("docs/现场演示故障切换手册.md", "submission_materials/05_系统运行与部署说明/现场演示故障切换手册.md"),
    @("docs/真实LLM接入与验收.md", "submission_materials/05_系统运行与部署说明/真实LLM接入与验收.md"),
    @("docs/知识库构建与RAG检索方案.md", "submission_materials/06_测试数据与知识库/知识库构建与RAG检索方案.md"),
    @("API_TEST.md", "submission_materials/07_接口测试与单元测试/API_TEST.md"),
    @("competition_baseline.json", "submission_materials/07_接口测试与单元测试/competition_baseline.json"),
    @("CURRENT_ACCEPTANCE_SUMMARY.md", "submission_materials/07_接口测试与单元测试/当前验收摘要.md"),
    @("docs/比赛提交口径基线.md", "submission_materials/07_接口测试与单元测试/比赛提交口径基线.md"),
    @("docs/测试方案与评价指标.md", "submission_materials/07_接口测试与单元测试/测试方案与评价指标.md"),
    @("evaluation/问答助手综合覆盖测试报告.md", "submission_materials/07_接口测试与单元测试/问答助手综合覆盖测试报告.md"),
    @("outputs/demo/demo_preflight_latest.json", "submission_materials/07_接口测试与单元测试/demo_preflight_latest.json"),
    @("FINAL_FUNCTIONAL_AUDIT.md", "submission_materials/08_源码说明/FINAL_FUNCTIONAL_AUDIT.md"),
    @("RELEASE_PACKAGE_README.md", "submission_materials/08_源码说明/RELEASE_PACKAGE_README.md"),
    @("SUBMISSION_CHECKLIST.md", "submission_materials/SUBMISSION_CHECKLIST.md")
)

foreach ($mapping in $copies) {
    $source = Join-Path $root $mapping[0]
    $destination = Join-Path $root $mapping[1]
    if (-not (Test-Path -LiteralPath $source)) {
        throw "Submission source is missing: $($mapping[0])"
    }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
    Copy-Item -LiteralPath $source -Destination $destination -Force
}

Write-Host "Submission materials synchronized: $($copies.Count) files." -ForegroundColor Green

