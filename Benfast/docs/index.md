# Benfast 课题组文档站

Benfast 是课题组的正式文档站：用于沉淀研究计划、实验记录、会议纪要、数据规范与阶段成果。

## 你应该在哪里编辑文档

可直接编辑这些源文件（最常用）：

- `docs/index.md`：首页与入口说明
- `docs/group/overview.md`：组内方向、组织与规则
- `docs/group/roadmap.md`：研究路线图与排期
- `docs/group/experiments.md`：实验记录规范与目录
- `docs/group/meetings.md`：会议制度与纪要目录
- `docs/group/data-governance.md`：数据治理规范
- `docs/group/reproducibility.md`：可复现规范
- `docs/group/milestones.md`：里程碑与成果

模板页（周报、会议纪要、实验记录等）在 `docs/kits/`，可直接编辑或复制后复用。

## 本地预览

```bash
cd /Users/ben/Desktop/Ben_cloud/Benfast
make docs-serve
```

浏览器打开：`http://127.0.0.1:8800`
