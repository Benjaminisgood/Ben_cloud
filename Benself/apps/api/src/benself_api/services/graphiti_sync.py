from __future__ import annotations

from dataclasses import dataclass

from benself_api.core.config import Settings
from benself_api.schemas.graph import GraphSearchResponse, GraphSearchResult
from benself_api.services.self_context import build_context_bundle


class GraphitiUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class GraphSyncOutcome:
    status: str
    raw_episode_count: int
    confirmed_episode_count: int
    backend: str
    message: str


def _ensure_graphiti_ready(settings: Settings) -> object:
    if not settings.GRAPHITI_ENABLED:
        raise GraphitiUnavailableError("Graphiti 已关闭。")
    try:
        from graphiti_core import Graphiti
        from graphiti_core.driver.kuzu_driver import KuzuDriver
    except ImportError as exc:
        raise GraphitiUnavailableError("Graphiti 依赖未安装，请先执行 `make install`。") from exc

    import os

    if not os.environ.get("OPENAI_API_KEY"):
        raise GraphitiUnavailableError("缺少 OPENAI_API_KEY，暂时只能生成 agent context 预览。")

    driver = KuzuDriver(db=str(settings.GRAPHITI_KUZU_DB_PATH))
    return Graphiti(graph_driver=driver)


async def run_graph_sync(settings: Settings, *, mode: str) -> GraphSyncOutcome:
    bundle = build_context_bundle(settings)
    raw_count = len(bundle.raw_episodes)
    confirmed_count = len(bundle.confirmed_episodes)

    if mode == "preview":
        return GraphSyncOutcome(
            status="preview",
            raw_episode_count=raw_count,
            confirmed_episode_count=confirmed_count,
            backend="preview",
            message="已生成 Graphiti 同步预览，尚未写入图数据库。",
        )

    try:
        graphiti = _ensure_graphiti_ready(settings)
    except GraphitiUnavailableError as exc:
        return GraphSyncOutcome(
            status="skipped",
            raw_episode_count=raw_count,
            confirmed_episode_count=confirmed_count,
            backend="graphiti+kuzu",
            message=str(exc),
        )

    from graphiti_core.nodes import EpisodeType

    try:
        await graphiti.build_indices_and_constraints()
        for episode in bundle.raw_episodes:
            await graphiti.add_episode(
                name=episode.name,
                episode_body=episode.body,
                source_description=episode.source_description,
                reference_time=episode.reference_time,
                source=EpisodeType.text,
                group_id=settings.GRAPHITI_GROUP_ID,
                custom_extraction_instructions=(
                    "Treat this as a raw subjective journal. Keep dates attached and do not convert feelings into permanent facts."
                ),
            )
        for episode in bundle.confirmed_episodes:
            await graphiti.add_episode(
                name=episode.name,
                episode_body=episode.body,
                source_description=episode.source_description,
                reference_time=episode.reference_time,
                source=EpisodeType.text,
                group_id=settings.GRAPHITI_GROUP_ID,
                custom_extraction_instructions=(
                    "Treat this as a confirmed personal fact. Prefer it over subjective journal content when conflicts appear."
                ),
            )
        return GraphSyncOutcome(
            status="completed",
            raw_episode_count=raw_count,
            confirmed_episode_count=confirmed_count,
            backend="graphiti+kuzu",
            message="已把 raw journals 和 confirmed facts 写入 Graphiti。",
        )
    except Exception as exc:
        return GraphSyncOutcome(
            status="failed",
            raw_episode_count=raw_count,
            confirmed_episode_count=confirmed_count,
            backend="graphiti+kuzu",
            message=f"Graphiti 同步失败: {exc}",
        )
    finally:
        await graphiti.close()


async def search_graphiti(settings: Settings, *, query: str, limit: int) -> GraphSearchResponse:
    graphiti = _ensure_graphiti_ready(settings)
    try:
        edges = await graphiti.search(query=query, group_ids=[settings.GRAPHITI_GROUP_ID], num_results=limit)
        return GraphSearchResponse(
            query=query,
            results=[
                GraphSearchResult(
                    name=edge.name,
                    fact=edge.fact,
                    valid_at=edge.valid_at.isoformat() if edge.valid_at else None,
                    invalid_at=edge.invalid_at.isoformat() if edge.invalid_at else None,
                    episodes=edge.episodes,
                )
                for edge in edges
            ],
        )
    finally:
        await graphiti.close()
