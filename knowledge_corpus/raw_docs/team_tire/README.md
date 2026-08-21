# 团队航空轮胎实验资料包

本目录用于保存团队自有或已获得授权的航空轮胎胎面橡胶实验资料。第三批建设重点是把实验条件、原始测量、损伤图像、案例结论和授权信息组织成可复核的数据集，再进入 Markdown 解析、知识切片和 Elasticsearch 入库流程。

## 目录

```text
team_tire/
├─ README.md
├─ 实验说明模板.md
├─ 数据脱敏与命名规范.md
├─ dataset_manifest.template.json
├─ data/
│  ├─ 航空轮胎热氧老化与滑动磨损实验记录模板.xlsx
│  └─ 损伤图像与案例标注模板.xlsx
├─ images/
│  ├─ SEM/
│  ├─ optical/
│  └─ damage_cases/
└─ attachments/
```

## 使用顺序

1. 复制 `dataset_manifest.template.json` 为 `dataset_manifest.json`，填写数据集编号、负责人代码、授权和实验范围。
2. 在实验记录工作簿中填写样品、老化工况和摩擦磨损原始记录，不覆盖仪器原始文件。
3. 图片按照命名规范放入对应目录，并在图像标注工作簿中逐张登记。
4. 用代码或匿名编号替代姓名、学号、手机号和设备资产责任人信息。
5. 检查文件路径、单位、重复试验编号和证据关联关系。
6. 运行校验命令：

```powershell
cd D:\agents\backend
.\.venv\Scripts\Activate.ps1
python -m app.rag.team_dataset_validator
```

在尚未录入真实数据时，可运行安全预演：

```powershell
python -m app.rag.team_dataset_pipeline --dry-run-template
```

该命令仅生成 `D:\agents\.tmp\team_tire_pipeline_preview.md`，不会注册知识源或写入 ES。真实数据通过授权和专业审核后，使用 `python -m app.rag.team_dataset_pipeline --ingest --index` 完成 Markdown 转换、来源登记、切片和索引。

7. 校验通过并完成导师/数据负责人确认后，再生成团队资料 Markdown 和知识切片。

## 重要边界

- 只存放团队自有、公开或已授权资料。
- 不存储真实姓名、学号、手机号、身份证号等个人敏感信息。
- 原始测量值不得直接覆盖；修订值放在单独字段并说明原因。
- 真实维护放行必须以有效 AMM、CMM、适航指令和单位批准程序为准。
- 示例行均以 `DEMO-` 开头，正式录入前可删除或替换。
