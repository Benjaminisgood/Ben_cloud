"""协作工作台与发布站点路由测试。"""

from __future__ import annotations

import uuid

from httpx import AsyncClient

from settings import settings


class TestCollabAppRoutes:
    async def test_app_requires_cookie_session(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/app/")
        assert response.status_code == 401

    async def test_app_serves_index_with_valid_cookie(
        self,
        async_client: AsyncClient,
        admin_token: str,
    ) -> None:
        async_client.cookies.set(settings.SSO_TOKEN_COOKIE_NAME, admin_token)
        response = await async_client.get("/app/")
        assert response.status_code == 200
        assert "文档库" in response.text
        assert "新建文档" in response.text

    async def test_book_overview_deep_link_uses_virtual_page(
        self,
        async_client: AsyncClient,
        admin_token: str,
    ) -> None:
        async_client.cookies.set(settings.SSO_TOKEN_COOKIE_NAME, admin_token)
        response = await async_client.get("/app/books/demo-book-id/")
        assert response.status_code == 200
        assert "文档设置" in response.text
        assert "关键词（逗号分隔）" in response.text
        assert 'id="bookTitleHeading"' in response.text
        assert 'id="documentCrumbLink"' in response.text

    async def test_document_outline_deep_link_uses_virtual_page(
        self,
        async_client: AsyncClient,
        admin_token: str,
    ) -> None:
        async_client.cookies.set(settings.SSO_TOKEN_COOKIE_NAME, admin_token)
        response = await async_client.get("/app/books/demo-book-id/outline/")
        assert response.status_code == 200
        assert "目录管理" in response.text
        assert 'id="bookTitleHeading"' in response.text
        assert 'id="documentCrumbLink"' in response.text

    async def test_page_editor_deep_link_uses_virtual_page(
        self,
        async_client: AsyncClient,
        admin_token: str,
    ) -> None:
        async_client.cookies.set(settings.SSO_TOKEN_COOKIE_NAME, admin_token)
        response = await async_client.get("/app/books/demo-book-id/pages/demo-page-id/")
        assert response.status_code == 200
        assert "文档写作" in response.text
        assert "开始编辑" in response.text
        assert "正文写作" in response.text
        assert "[[getting-started]]" in response.text
        assert 'id="pageTitleHeading"' in response.text
        assert 'id="documentCrumbLink"' in response.text

    async def test_page_preview_deep_link_uses_virtual_page(
        self,
        async_client: AsyncClient,
        admin_token: str,
    ) -> None:
        async_client.cookies.set(settings.SSO_TOKEN_COOKIE_NAME, admin_token)
        response = await async_client.get("/app/books/demo-book-id/pages/demo-page-id/preview/")
        assert response.status_code == 200
        assert "文档预览" in response.text
        assert "评论协作" in response.text
        assert 'id="pageTitleHeading"' in response.text
        assert 'id="documentCrumbLink"' in response.text

    async def test_publish_deep_link_uses_virtual_page(
        self,
        async_client: AsyncClient,
        admin_token: str,
    ) -> None:
        async_client.cookies.set(settings.SSO_TOKEN_COOKIE_NAME, admin_token)
        response = await async_client.get("/app/books/demo-book-id/publish/")
        assert response.status_code == 200
        assert "文档发布" in response.text
        assert 'id="publishBookTitle"' in response.text
        assert 'id="publishBookMeta"' in response.text
        assert 'id="documentCrumbLink"' in response.text

    async def test_workspace_shortcut_redirects_to_app(
        self,
        async_client: AsyncClient,
        admin_token: str,
    ) -> None:
        async_client.cookies.set(settings.SSO_TOKEN_COOKIE_NAME, admin_token)
        response = await async_client.get("/workspace", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == "/app/"

    async def test_published_book_is_served_under_kb(
        self,
        async_client: AsyncClient,
        admin_token: str,
    ) -> None:
        headers = {"Authorization": f"Bearer {admin_token}"}
        suffix = uuid.uuid4().hex[:8]

        create_book_resp = await async_client.post(
            "/api/v1/labdocs/books",
            json={
                "title": "新人入组指南",
                "slug": f"onboarding-{suffix}",
                "summary": "新成员需要先阅读的手册",
            },
            headers=headers,
        )
        assert create_book_resp.status_code == 200
        book = create_book_resp.json()["data"]

        chapter_resp = await async_client.post(
            f"/api/v1/labdocs/books/{book['id']}/pages",
            json={
                "parent_id": book["root_page_id"],
                "title": "实验准备",
                "slug": "prep",
                "kind": "chapter",
                "content": "# 实验准备\n\n本章用于组织准备步骤。",
            },
            headers=headers,
        )
        assert chapter_resp.status_code == 200
        chapter = chapter_resp.json()["data"]

        page_resp = await async_client.post(
            f"/api/v1/labdocs/books/{book['id']}/pages",
            json={
                "parent_id": chapter["id"],
                "title": "试剂清单",
                "slug": "reagents",
                "kind": "page",
                "content": "# 试剂清单\n\n## 入场检查\n\n- 核对批号",
            },
            headers=headers,
        )
        assert page_resp.status_code == 200

        publish_resp = await async_client.post(
            f"/api/v1/labdocs/books/{book['id']}/publish",
            json={"message": "发布新人指南"},
            headers=headers,
        )
        assert publish_resp.status_code == 200

        async_client.cookies.set(settings.SSO_TOKEN_COOKIE_NAME, admin_token)
        home_response = await async_client.get("/kb/")
        assert home_response.status_code == 200
        assert "Benfast 实验室文档站" in home_response.text
        assert "重点文档" in home_response.text
        assert "阅读方式" in home_response.text
        assert 'class="hero-panel hero-panel--portal"' in home_response.text

        response = await async_client.get(f"/kb/books/onboarding-{suffix}/")
        assert response.status_code == 200
        assert "新人入组指南" in response.text
        assert "OUTLINE" in response.text
        assert 'href="prep/"' in response.text

        page_response = await async_client.get(
            f"/kb/books/onboarding-{suffix}/prep/reagents/"
        )
        assert page_response.status_code == 200
        assert "本页目录" in page_response.text
        assert "入场检查" in page_response.text
