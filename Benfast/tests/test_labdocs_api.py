"""多书协作文档 API 测试。"""

from __future__ import annotations

import uuid

from httpx import AsyncClient

from settings import settings


class TestLabDocsAPI:
    async def test_book_workspace_and_publish_flow(
        self,
        async_client: AsyncClient,
        admin_token: str,
    ) -> None:
        headers = {"Authorization": f"Bearer {admin_token}"}
        suffix = uuid.uuid4().hex[:8]

        create_book_resp = await async_client.post(
            "/api/v1/labdocs/books",
            json={
                "title": "课题组手册",
                "slug": f"lab-handbook-{suffix}",
                "description": "整合规章、模板与 SOP",
                "summary": "课题组的正式协作手册",
                "keywords": ["手册", "SOP"],
            },
            headers=headers,
        )
        assert create_book_resp.status_code == 200
        book = create_book_resp.json()["data"]
        assert book["title"] == "课题组手册"
        assert book["keywords"] == ["手册", "SOP"]
        assert book["root_page_id"]
        assert book["tree"][0]["id"] == book["root_page_id"]
        assert book["tree"][0]["kind"] == "root"
        assert book["tree"][0]["is_root"] is True
        assert book["tree"][0]["kind_label"] == "文档首页"

        root_page_id = book["root_page_id"]
        book_id = book["id"]

        chapter_resp = await async_client.post(
            f"/api/v1/labdocs/books/{book_id}/pages",
            json={
                "parent_id": root_page_id,
                "title": "新人入组指南",
                "slug": "getting-started",
                "kind": "chapter",
                "order": 20,
                "content": "# 新人入组指南\n\n- 先读完课题组手册\n- 配置账号与环境",
            },
            headers=headers,
        )
        assert chapter_resp.status_code == 200
        chapter = chapter_resp.json()["data"]
        assert chapter["parent_id"] == root_page_id
        assert chapter["version"] == 1

        page_resp = await async_client.post(
            f"/api/v1/labdocs/books/{book_id}/pages",
            json={
                "parent_id": chapter["id"],
                "title": "实验 SOP",
                "slug": "experiment-sop",
                "kind": "page",
                "order": 10,
                "content": "# 实验 SOP\n\n## 安全要求\n\n- 记录实验编号",
            },
            headers=headers,
        )
        assert page_resp.status_code == 200
        page = page_resp.json()["data"]
        assert page["title"] == "实验 SOP"

        root_update_resp = await async_client.put(
            f"/api/v1/labdocs/pages/{root_page_id}",
            json={
                "expected_version": 1,
                "title": "课题组手册",
                "slug": "index",
                "content": (
                    "# 课题组手册\n\n"
                    "请先阅读 [[getting-started/experiment-sop]]。\n\n"
                    "重点章节 [[getting-started/experiment-sop#安全要求]]。\n\n"
                    "标签入口 [[标签:试剂安全]]。\n"
                ),
                "change_note": "补充引用示例",
            },
            headers=headers,
        )
        assert root_update_resp.status_code == 200

        invalid_child_resp = await async_client.post(
            f"/api/v1/labdocs/books/{book_id}/pages",
            json={
                "parent_id": page["id"],
                "title": "错误挂载",
                "slug": "invalid-under-page",
                "kind": "page",
                "order": 30,
                "content": "# 不应成功",
            },
            headers=headers,
        )
        assert invalid_child_resp.status_code == 400
        assert "包含子节点" in invalid_child_resp.json()["msg"]

        tree_resp = await async_client.get(
            f"/api/v1/labdocs/books/{book_id}/tree",
            headers=headers,
        )
        assert tree_resp.status_code == 200
        tree = tree_resp.json()["data"]
        assert tree[0]["children"][0]["title"] == "新人入组指南"
        assert tree[0]["children"][0]["children"][0]["title"] == "实验 SOP"

        update_page_resp = await async_client.put(
            f"/api/v1/labdocs/pages/{page['id']}",
            json={
                "expected_version": 1,
                "title": "实验 SOP（更新）",
                "slug": "experiment-sop",
                "content": (
                    "# 实验 SOP\n\n"
                    "当前锚点 [[#安全要求]]。\n\n"
                    "## 安全要求\n\n"
                    "- 记录实验编号\n"
                    "- 补充对照组说明\n"
                    "- 常用标签 #试剂安全 #新人培训"
                ),
                "change_note": "补充对照组说明",
            },
            headers=headers,
        )
        assert update_page_resp.status_code == 200
        updated_page = update_page_resp.json()["data"]
        assert updated_page["title"] == "实验 SOP（更新）"
        assert updated_page["version"] == 2
        assert updated_page["headings"][0]["title"] == "实验 SOP"
        assert updated_page["headings"][1]["anchor"] == "安全要求"
        assert updated_page["inline_tags"] == ["试剂安全", "新人培训"]

        comment_resp = await async_client.post(
            f"/api/v1/labdocs/pages/{page['id']}/comments",
            json={"content": "建议补充仪器校准步骤", "anchor": "安全要求"},
            headers=headers,
        )
        assert comment_resp.status_code == 200
        comment = comment_resp.json()["data"]
        assert comment["anchor"] == "安全要求"

        revisions_resp = await async_client.get(
            f"/api/v1/labdocs/pages/{page['id']}/revisions",
            headers=headers,
        )
        assert revisions_resp.status_code == 200
        revisions = revisions_resp.json()["data"]
        assert revisions[0]["version"] == 2

        references_resp = await async_client.get(
            f"/api/v1/labdocs/books/{book_id}/references",
            params={"page_id": root_page_id},
            headers=headers,
        )
        assert references_resp.status_code == 200
        references = references_resp.json()["data"]
        assert references["book"]["id"] == book_id
        assert references["current_page_id"] == root_page_id
        assert any(item["token"] == "getting-started/experiment-sop" for item in references["references"]["outgoing"])
        assert any(item["token"] == "getting-started/experiment-sop#安全要求" for item in references["references"]["outgoing"])
        assert any(item["token"] == "标签:试剂安全" for item in references["references"]["outgoing"])
        assert any(item["tag"] == "试剂安全" for item in references["tags"])

        filtered_references_resp = await async_client.get(
            f"/api/v1/labdocs/books/{book_id}/references",
            params={"page_id": page["id"], "q": "安全"},
            headers=headers,
        )
        assert filtered_references_resp.status_code == 200
        filtered_references = filtered_references_resp.json()["data"]
        assert all("安全" in item["tag"] for item in filtered_references["tags"])
        assert any(item["heading"] == "安全要求" for item in filtered_references["references"]["incoming"])

        publish_resp = await async_client.post(
            f"/api/v1/labdocs/books/{book_id}/publish",
            json={"message": "发布第一版课题组手册"},
            headers=headers,
        )
        assert publish_resp.status_code == 200
        publish = publish_resp.json()["data"]
        assert publish["published_url"] == f"/kb/books/lab-handbook-{suffix}/"

        async_client.cookies.set(settings.SSO_TOKEN_COOKIE_NAME, admin_token)
        published_root_resp = await async_client.get(publish["published_url"])
        assert published_root_resp.status_code == 200
        assert "本页目录" in published_root_resp.text
        assert 'href="getting-started/"' in published_root_resp.text
        assert 'href="getting-started/experiment-sop/"' in published_root_resp.text
        assert "重点章节" in published_root_resp.text
        assert f'href="/kb/books/lab-handbook-{suffix}/getting-started/experiment-sop/"' in published_root_resp.text
        assert f'href="/kb/books/lab-handbook-{suffix}/getting-started/experiment-sop/#安全要求"' in published_root_resp.text
        assert 'href="/kb/tags/试剂安全/"' in published_root_resp.text

        published_page_resp = await async_client.get(
            f"/kb/books/lab-handbook-{suffix}/getting-started/experiment-sop/"
        )
        assert published_page_resp.status_code == 200
        assert "安全要求" in published_page_resp.text
        assert 'href="../"' in published_page_resp.text
        assert "上一页" in published_page_resp.text
        assert f'href="#安全要求"' in published_page_resp.text
        assert 'href="/kb/tags/试剂安全/"' in published_page_resp.text

        tag_page_resp = await async_client.get("/kb/tags/试剂安全/")
        assert tag_page_resp.status_code == 200
        assert "标签：#试剂安全" in tag_page_resp.text
        assert "实验 SOP（更新）" in tag_page_resp.text

        publishes_resp = await async_client.get(
            f"/api/v1/labdocs/books/{book_id}/publishes",
            headers=headers,
        )
        assert publishes_resp.status_code == 200
        publishes = publishes_resp.json()["data"]
        assert publishes[0]["message"] == "发布第一版课题组手册"

    async def test_page_lock_conflict_and_version_conflict(
        self,
        async_client: AsyncClient,
        admin_token: str,
        normal_user_token: str,
    ) -> None:
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        user_headers = {"Authorization": f"Bearer {normal_user_token}"}
        suffix = uuid.uuid4().hex[:8]

        create_book_resp = await async_client.post(
            "/api/v1/labdocs/books",
            json={
                "title": "实验 SOP",
                "slug": f"experiment-sop-{suffix}",
                "summary": "实验过程规范",
            },
            headers=admin_headers,
        )
        assert create_book_resp.status_code == 200
        book = create_book_resp.json()["data"]

        create_page_resp = await async_client.post(
            f"/api/v1/labdocs/books/{book['id']}/pages",
            json={
                "parent_id": book["root_page_id"],
                "title": "试剂准备",
                "slug": "reagent-prep",
                "content": "v1",
            },
            headers=admin_headers,
        )
        assert create_page_resp.status_code == 200
        page = create_page_resp.json()["data"]

        admin_lock_resp = await async_client.post(
            f"/api/v1/labdocs/pages/{page['id']}/lock/acquire",
            json={"ttl_minutes": 10},
            headers=admin_headers,
        )
        assert admin_lock_resp.status_code == 200

        user_lock_resp = await async_client.post(
            f"/api/v1/labdocs/pages/{page['id']}/lock/acquire",
            json={"ttl_minutes": 10},
            headers=user_headers,
        )
        assert user_lock_resp.status_code == 409

        locked_update_resp = await async_client.put(
            f"/api/v1/labdocs/pages/{page['id']}",
            json={
                "expected_version": 1,
                "content": "v2",
                "change_note": "user update while locked",
            },
            headers=user_headers,
        )
        assert locked_update_resp.status_code == 409

        admin_update_resp = await async_client.put(
            f"/api/v1/labdocs/pages/{page['id']}",
            json={
                "expected_version": 1,
                "content": "v2",
                "change_note": "admin update",
            },
            headers=admin_headers,
        )
        assert admin_update_resp.status_code == 200

        stale_update_resp = await async_client.put(
            f"/api/v1/labdocs/pages/{page['id']}",
            json={
                "expected_version": 1,
                "content": "v3",
                "change_note": "stale version",
            },
            headers=admin_headers,
        )
        assert stale_update_resp.status_code == 409
        assert stale_update_resp.json()["current_version"] == 2

        release_resp = await async_client.post(
            f"/api/v1/labdocs/pages/{page['id']}/lock/release",
            headers=admin_headers,
        )
        assert release_resp.status_code == 200
        assert release_resp.json()["data"]["released"] is True

    async def test_book_assets_upload_and_media_delivery(
        self,
        async_client: AsyncClient,
        admin_token: str,
    ) -> None:
        headers = {"Authorization": f"Bearer {admin_token}"}
        suffix = uuid.uuid4().hex[:8]

        create_book_resp = await async_client.post(
            "/api/v1/labdocs/books",
            json={
                "title": "图像记录手册",
                "slug": f"image-playbook-{suffix}",
                "summary": "验证附件上传与引用",
            },
            headers=headers,
        )
        assert create_book_resp.status_code == 200
        book = create_book_resp.json()["data"]
        book_id = book["id"]

        image_bytes = (
            b"\x89PNG\r\n\x1a\n"
            b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
            b"\x1f\x15\xc4\x89\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe"
            b"\xa7^\xab\x89\x00\x00\x00\x00IEND\xaeB`\x82"
        )

        upload_resp = await async_client.post(
            f"/api/v1/labdocs/books/{book_id}/assets",
            files={"file": ("cover.png", image_bytes, "image/png")},
            headers=headers,
        )
        assert upload_resp.status_code == 200
        asset = upload_resp.json()["data"]
        assert asset["id"]
        assert asset["original_name"] == "cover.png"
        assert asset["url"].startswith(f"/kb/media/{book_id}/")
        assert asset["markdown"].startswith("![cover](")

        assets_resp = await async_client.get(
            f"/api/v1/labdocs/books/{book_id}/assets",
            headers=headers,
        )
        assert assets_resp.status_code == 200
        assets = assets_resp.json()["data"]
        assert assets[0]["id"] == asset["id"]

        async_client.cookies.set(settings.SSO_TOKEN_COOKIE_NAME, admin_token)
        media_resp = await async_client.get(asset["url"])
        assert media_resp.status_code == 200
        assert media_resp.content == image_bytes
        assert media_resp.headers["content-type"].startswith("image/png")
        assert 'inline; filename="cover.png"' in media_resp.headers["content-disposition"]
