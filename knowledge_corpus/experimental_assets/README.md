# 实验资产目录

本目录保存团队授权实验资料的轻量化、可追溯衍生资产，不保存移动硬盘中的全部原始仪器文件。

## 当前专题

- `service_tire_wear`：10 项实胎偏磨与严重度判读图像。
- `thermal_aging_multimodal`：14 项热氧老化后光学/SEM图像和1项趋势图。
- `uv_aging_wear_morphology`：12 项紫外老化 24 h、504 h、576 h 后的摩擦前表面、磨痕和磨屑代表图像。
- `load_distance_morphology_matrix`：15 项“3 个载荷 × 5 个距离”往复摩擦形貌，以及1项磨损量/硬度趋势图。

共4个专题、53项已审核资产。

## 数据结构

`catalog.json` 中每个资产包含实验编号、样品编号、工况、模态、标签、审核状态、授权状态、源文件 SHA-256、衍生文件 SHA-256、关联 RAG 来源和使用边界。

项目对外只返回脱敏的 `source_reference`，不会通过 API 暴露移动硬盘绝对路径。

## 第二批证据边界

- 紫外老化专题已确认 UVA-340、295-365 nm、0.6 W/m² 和老化时长；摩擦载荷、速度与行程尚不能从当前图像目录唯一核对，因此保持 `pending_source_confirmation`。
- 往复摩擦专题完整绑定 40/50/60 N、20/40/80/120/160 m、接触压力、磨损量、硬度和代表性光学形貌。
- 温升记录只覆盖部分载荷组，不生成或插补15个矩阵单元的温升值。
- 所有图像均为代表视野，不能替代重复试验、多视野统计或维修放行判据。

## 重新生成

连接授权实验数据硬盘并确认路径仍为 `E:\梁永琦` 和 `H:\任孝琴` 后执行：

```powershell
cd D:\agents\backend
.\.venv\Scripts\Activate.ps1
python -m app.rag.import_experimental_assets
python -m app.rag.pipeline
```

运行中的系统只读取本目录生成结果，不需要移动硬盘持续连接。
