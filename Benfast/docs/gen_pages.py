#!/usr/bin/env python3
"""Generate Benfast research-group documentation template pages.

This script intentionally avoids importing the runtime FastAPI app so MkDocs
builds remain stable in local/offline environments.
"""

from __future__ import annotations

from datetime import datetime
from textwrap import dedent

import mkdocs_gen_files


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _render(text: str) -> str:
    return dedent(text).strip() + "\n"


def _pages() -> dict[str, str]:
    today = _today()
    return {
        "kits/index.md": f"""
        # 模板中心

        下列页面为课题组统一模板，建议复制后放入你自己的文档目录再填写。

        - [课题立项模板](project-charter.md)
        - [周报模板](weekly-report.md)
        - [会议纪要模板](meeting-minutes.md)
        - [实验记录模板](experiment-log.md)
        - [数据集卡片模板](dataset-card.md)

        生成日期：`{today}`
        """,
        "kits/project-charter.md": """
        # 课题立项模板

        ## 1. 基本信息

        - 课题名称：
        - 负责人：
        - 参与成员：
        - 起止时间：
        - 关联基金/项目编号：

        ## 2. 背景与问题定义

        - 背景描述：
        - 核心问题：
        - 现有方法不足：

        ## 3. 目标与评估指标

        - 总目标：
        - 里程碑目标：
        - 量化指标（精度/效率/稳定性）：

        ## 4. 技术路线

        - 方法设计：
        - 数据来源：
        - 实验计划：

        ## 5. 风险与预案

        - 数据风险：
        - 进度风险：
        - 资源风险：

        ## 6. 预期产出

        - 论文/专利：
        - 开源代码/数据：
        - 组内可复用资产：
        """,
        "kits/weekly-report.md": """
        # 周报模板

        - 周次：
        - 填写人：
        - 日期范围：

        ## 本周完成

        1. 
        2. 
        3. 

        ## 数据与实验更新

        - 新增数据：
        - 实验编号与结果：
        - 与上周对比：

        ## 问题与阻塞

        - 阻塞点：
        - 已尝试方案：
        - 需要协助：

        ## 下周计划

        1. 
        2. 
        3. 
        """,
        "kits/meeting-minutes.md": """
        # 会议纪要模板

        - 会议主题：
        - 会议时间：
        - 参会人员：
        - 记录人：

        ## 议题

        1. 
        2. 

        ## 结论

        - 

        ## 行动项

        | 事项 | 负责人 | 截止日期 | 状态 |
        |------|--------|----------|------|
        |      |        |          |      |

        ## 附件与链接

        - 
        """,
        "kits/experiment-log.md": """
        # 实验记录模板

        - 实验编号：
        - 实验名称：
        - 负责人：
        - 日期：
        - 代码分支/Commit：

        ## 实验目标

        - 

        ## 实验设置

        - 数据版本：
        - 主要参数：
        - 运行环境：

        ## 结果

        | 指标 | 本次结果 | 基线结果 | 备注 |
        |------|----------|----------|------|
        |      |          |          |      |

        ## 结论与下一步

        - 结论：
        - 下一步：
        """,
        "kits/dataset-card.md": """
        # 数据集卡片模板

        ## 1. 元信息

        - 数据集名称：
        - 版本号：
        - 维护人：
        - 更新时间：
        - 存储位置：

        ## 2. 数据说明

        - 来源：
        - 样本量：
        - 字段说明：
        - 标签说明：

        ## 3. 合规与权限

        - 是否含敏感数据：
        - 脱敏策略：
        - 使用权限（组内/公开/受限）：

        ## 4. 质量与限制

        - 缺失值情况：
        - 偏差风险：
        - 已知限制：

        ## 5. 使用记录

        - 使用课题：
        - 关联实验编号：
        """,
        "ops/index.md": f"""
        # 系统运维

        本页用于说明 Benfast 文档站在 Ben_cloud 中的运行方式。

        ## 服务角色

        - `Benfast`：课题组文档站主应用（Markdown -> 文档网站）。
        - `Benbot`：统一门户与 SSO 入口。

        ## 登录流

        1. 用户从 Benbot 门户点击 Benfast。
        2. Benbot 跳转 `Benfast /auth/sso?token=...`。
        3. Benfast 校验 token 后建立本地会话。
        4. 成功后跳转到文档站首页 `/kb/`。

        ## 日常运维命令

        ```bash
        cd /Users/ben/Desktop/Ben_cloud/Benfast
        ./benfast.sh init-env
        ./benfast.sh install
        ./benfast.sh start
        ./benfast.sh status
        ./benfast.sh logs
        ```

        生成日期：`{today}`
        """,
        "ops/endpoints.md": """
        # 关键接口清单

        ## 健康检查

        - `GET /health`：服务存活检查。

        ## SSO 入口

        - `GET /auth/sso?token=...`：接收 Benbot 签发 token 并登录。

        ## 门户入口

        - `GET /portal`：登录后跳转到 `/kb/`。

        ## 文档站入口

        - `GET /kb/`：文档首页。
        - `GET /kb/{doc_path}`：文档静态资源与页面。

        ## 认证信息

        - `GET /auth/me`：查看当前会话用户。
        - `POST /auth/logout`：退出当前会话。
        """,
        "api/index.md": """
        # API 与集成说明

        这个页面面向课题组内部维护人员，描述 Benfast 与 Benbot 的集成约定。

        ## SSO 约定

        - Token 签名算法：`HMAC-SHA256`
        - 编码格式：`Base64URL`
        - 共享密钥：`SSO_SECRET`（Benbot 与 Benfast 必须一致）

        ## 本地开发验证

        ```bash
        # 启动文档构建
        cd /Users/ben/Desktop/Ben_cloud/Benfast
        make docs-build

        # 本地预览文档站
        make docs-serve
        ```

        ## 兼容入口（必须保持）

        - `GET /health`
        - `GET /auth/sso?token=...`
        - `GET /portal`
        """,
    }


def main() -> None:
    generated = _pages()
    for path, content in generated.items():
        with mkdocs_gen_files.open(path, "w") as f:
            f.write(_render(content))
        mkdocs_gen_files.set_edit_path(path, "docs/gen_pages.py")

    print(f"generated {len(generated)} docs pages")


if __name__ == "__main__":
    main()
