"""文献 PDF 下载服务

支持多种文献下载源：
1. Sci-Hub (通过多个镜像)
2. Unpaywall (开放获取)
3. CrossRef (元数据)
4. 机构知识库
"""
from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class PublicationDownloader:
    """文献 PDF 下载器"""

    def __init__(self, download_dir: str | None = None):
        """
        Args:
            download_dir: PDF 保存目录，默认为 Benlab 的 uploads 目录
        """
        if download_dir:
            self.download_dir = Path(download_dir)
        else:
            # 默认使用 Benlab 的 uploads/publications 目录
            base_dir = Path(__file__).parent.parent.parent.parent.parent
            self.download_dir = base_dir / "data" / "uploads" / "publications"

        self.download_dir.mkdir(parents=True, exist_ok=True)

        # 配置 HTTP 会话
        self.session = self._create_session()

        # Sci-Hub 镜像列表（会动态更新）
        self.scihub_mirrors = [
            "https://sci-hub.se",
            "https://sci-hub.st",
            "https://sci-hub.ru",
            "https://sci-hub.wf",
        ]

        # Unpaywall API (免费开放获取)
        self.unpaywall_email = "your_email@example.com"  # 建议替换为真实邮箱

    def _create_session(self) -> requests.Session:
        """创建带重试机制的 HTTP 会话"""
        session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        })
        return session

    def download_by_doi(self, doi: str, publication_id: int) -> dict[str, Any]:
        """
        通过 DOI 下载 PDF

        Args:
            doi: 文献 DOI 号
            publication_id: 文献 ID（用于生成文件名）

        Returns:
            dict: {
                "success": bool,
                "pdf_path": str | None,
                "source": str | None,  # 下载来源
                "error": str | None
            }
        """
        doi = doi.strip().lower()
        if not doi.startswith("10."):
            return {
                "success": False,
                "pdf_path": None,
                "source": None,
                "error": f"无效的 DOI 格式：{doi}"
            }

        # 尝试多种下载源
        strategies = [
            ("unpaywall", self._try_unpaywall),
            ("sci-hub", self._try_scihub),
        ]

        for source_name, strategy_func in strategies:
            try:
                result = strategy_func(doi)
                if result and result.get("pdf_url"):
                    pdf_path = self._download_file(result["pdf_url"], doi, publication_id)
                    if pdf_path:
                        return {
                            "success": True,
                            "pdf_path": str(pdf_path),
                            "source": source_name,
                            "error": None,
                        }
            except Exception as e:
                # 继续尝试下一个源
                print(f"[{source_name}] 下载失败：{e}")
                continue

        return {
            "success": False,
            "pdf_path": None,
            "source": None,
            "error": "所有下载源均失败"
        }

    def _try_unpaywall(self, doi: str) -> dict[str, Any] | None:
        """
        尝试从 Unpaywall 获取开放获取 PDF

        Unpaywall API: https://unpaywall.org/products/api
        免费，无需 API key，但建议提供邮箱
        """
        url = f"https://api.unpaywall.org/v2/{doi}"
        params = {"email": self.unpaywall_email}

        try:
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code != 200:
                return None

            data = response.json()

            # 检查是否有 OA PDF
            if data.get("is_oa") and data.get("best_oa_location"):
                best_location = data["best_oa_location"]
                if best_location.get("host_type") == "repository":
                    pdf_url = best_location.get("url_for_pdf") or best_location.get("url")
                    if pdf_url:
                        return {"pdf_url": pdf_url, "source": "unpaywall"}

            # 检查所有 OA locations
            for location in data.get("oa_locations", []):
                if location.get("is_best") and location.get("url_for_pdf"):
                    return {"pdf_url": location["url_for_pdf"], "source": "unpaywall"}

        except Exception as e:
            print(f"Unpaywall 请求失败：{e}")

        return None

    def _try_scihub(self, doi: str) -> dict[str, Any] | None:
        """
        尝试从 Sci-Hub 下载 PDF

        注意：Sci-Hub 的可用性因地区和网络而异
        """
        for mirror in self.scihub_mirrors:
            try:
                # 方法 1: 直接访问 DOI 链接
                sci_url = f"{mirror}/sci-hub.php/{doi}"
                response = self.session.get(sci_url, timeout=15, allow_redirects=True)

                if response.status_code == 200:
                    # 检查是否是 PDF
                    content_type = response.headers.get("Content-Type", "")
                    if "application/pdf" in content_type:
                        return {"pdf_url": sci_url, "source": "sci-hub"}

                    # 尝试从页面提取 PDF 下载链接
                    pdf_url = self._extract_scihub_pdf_url(response.text, mirror)
                    if pdf_url:
                        return {"pdf_url": pdf_url, "source": "sci-hub"}

                # 方法 2: 通过表单提交
                # (某些 Sci-Hub 镜像需要 POST 请求)
                time.sleep(1)  # 避免请求过快

            except Exception as e:
                print(f"Sci-Hub 镜像 {mirror} 失败：{e}")
                continue

        return None

    def _extract_scihub_pdf_url(self, html: str, mirror: str) -> str | None:
        """从 Sci-Hub 页面提取 PDF 下载链接"""
        # 常见的 PDF 链接模式
        patterns = [
            r'data-pdf-url="([^"]+)"',
            r'href="([^"]+\.pdf[^"]*)"',
            r'src="([^"]+\.pdf[^"]*)"',
            r'/downloads/([^"]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                url = match.group(1)
                if not url.startswith("http"):
                    url = f"{mirror}{url}"
                return url

        return None

    def _download_file(self, url: str, doi: str, publication_id: int) -> Path | None:
        """
        下载文件到本地

        Args:
            url: PDF URL
            doi: DOI 号（用于生成文件名）
            publication_id: 文献 ID

        Returns:
            Path: 保存的文件路径，失败返回 None
        """
        # 生成安全的文件名
        safe_doi = re.sub(r"[^a-zA-Z0-9._-]", "_", doi)
        filename = f"pub_{publication_id}_{safe_doi}.pdf"
        filepath = self.download_dir / filename

        try:
            response = self.session.get(url, timeout=30, stream=True)
            response.raise_for_status()

            # 验证是否是 PDF
            content_type = response.headers.get("Content-Type", "")
            if "application/pdf" not in content_type and not url.endswith(".pdf"):
                # 尝试读取文件头判断
                first_bytes = response.content[:4]
                if first_bytes != b"%PDF":
                    print(f"警告：下载的文件可能不是 PDF (Content-Type: {content_type})")

            # 保存文件
            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # 验证文件大小
            if filepath.stat().st_size < 1024:  # 小于 1KB 可能是错误页面
                filepath.unlink()
                return None

            return filepath

        except Exception as e:
            print(f"下载文件失败：{e}")
            if filepath.exists():
                filepath.unlink()
            return None

    def search_by_doi(self, doi: str) -> dict[str, Any] | None:
        """
        通过 DOI 搜索文献元数据（CrossRef API）

        Returns:
            dict: 文献元数据 {title, authors, journal, year, abstract, ...}
        """
        url = f"https://api.crossref.org/works/{doi}"

        try:
            response = self.session.get(url, timeout=10)
            if response.status_code != 200:
                return None

            data = response.json()
            if data.get("status") != "ok":
                return None

            message = data.get("message", {})

            # 提取元数据
            title = message.get("title", [""])[0] if message.get("title") else ""
            authors = message.get("author", [])
            author_names = []
            for author in authors:
                given = author.get("given", "")
                family = author.get("family", "")
                if given and family:
                    author_names.append(f"{given} {family}")
                elif family:
                    author_names.append(family)

            container = message.get("container-title", [""])[0] if message.get("container-title") else ""
            published = message.get("published", {})
            year = published.get("date-parts", [[None]])[0][0] if published.get("date-parts") else None

            abstract = message.get("abstract", "")
            # CrossRef 的 abstract 通常是 Base64 编码的 HTML
            if abstract:
                import base64
                try:
                    abstract = base64.b64decode(abstract).decode("utf-8")
                    # 移除 HTML 标签
                    abstract = re.sub(r"<[^>]+>", "", abstract)
                except Exception:
                    pass

            return {
                "doi": doi,
                "title": title,
                "authors": ", ".join(author_names),
                "journal": container,
                "publication_year": year,
                "abstract": abstract,
                "publisher": message.get("publisher", ""),
                "type": message.get("type", ""),
            }

        except Exception as e:
            print(f"CrossRef 搜索失败：{e}")
            return None

    def fetch_metadata(self, doi: str) -> dict[str, Any] | None:
        """
        获取文献元数据（优先使用 CrossRef，失败则返回 None）

        这是 search_by_doi 的别名，提供更清晰的 API
        """
        return self.search_by_doi(doi)


# 工具函数
def validate_doi(doi: str) -> bool:
    """验证 DOI 格式"""
    doi = doi.strip()
    return bool(re.match(r"^10\.\d{4,9}/[-._;()/:A-Z0-9]+$", doi, re.IGNORECASE))


def normalize_doi(doi: str) -> str:
    """标准化 DOI 格式"""
    doi = doi.strip()
    # 移除 URL 前缀
    doi = re.sub(r"^https?://doi\.org/", "", doi)
    doi = re.sub(r"^doi:", "", doi, flags=re.IGNORECASE)
    return doi.lower()
