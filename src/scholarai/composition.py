"""The composition root: the one place every concrete adapter is chosen and wired.

Nothing outside this module imports a concrete infrastructure class directly
by name (aside from the small factory functions each infrastructure package
exposes) — ``application`` code only ever sees ports. Swapping OpenAI for
Ollama, or the SQLite dev database for Postgres, is a change to
``.env``, not to this file.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from scholarai.application.agents.deps import AgentDeps
from scholarai.application.orchestration.runtime import WorkflowRunManager
from scholarai.application.use_cases.application_store import ApplicationStore
from scholarai.domain.ports.llm import LLMClient
from scholarai.domain.ports.vectorstore import Embedder, VectorStore
from scholarai.domain.ports.web_search import WebSearchClient
from scholarai.infrastructure.config.settings import Settings, get_settings
from scholarai.infrastructure.database.engine import build_engine, create_all, get_sessionmaker
from scholarai.infrastructure.documents.composite import CompositeDocumentReader
from scholarai.infrastructure.embeddings import build_embedder
from scholarai.infrastructure.llm.factory import build_llm_client
from scholarai.infrastructure.memory.semantic_memory import EpisodicSemanticMemory
from scholarai.infrastructure.memory.sql_episode_repository import SqlEpisodeRepository
from scholarai.infrastructure.observability import configure_logging, get_logger
from scholarai.infrastructure.rag.ingestion import ingest_knowledge_base
from scholarai.infrastructure.rag.retriever import PolicyRetriever
from scholarai.infrastructure.vectorstore.qdrant_store import build_vector_store
from scholarai.infrastructure.web_search.tavily_client import build_web_search_client

log = get_logger(__name__)


@dataclass
class Container:
    settings: Settings
    llm: LLMClient
    embedder: Embedder
    vector_store: VectorStore
    retriever: PolicyRetriever
    document_reader: CompositeDocumentReader
    web_search: WebSearchClient | None
    engine: AsyncEngine
    sessionmaker: async_sessionmaker[AsyncSession]
    episode_repository: SqlEpisodeRepository
    semantic_memory: EpisodicSemanticMemory
    application_store: ApplicationStore
    run_manager: WorkflowRunManager

    @property
    def agent_deps(self) -> AgentDeps:
        return AgentDeps(
            llm=self.llm,
            retriever=self.retriever,
            document_reader=self.document_reader,
            web_search=self.web_search,
        )


def build_container(settings: Settings | None = None) -> Container:
    settings = settings or get_settings()
    configure_logging(settings.log_level, json_output=settings.environment.value == "production")

    llm = build_llm_client(settings.llm)
    embedder = build_embedder(settings.llm)
    vector_store = build_vector_store(settings.vectorstore.url)
    retriever = PolicyRetriever(vector_store, embedder)
    document_reader = CompositeDocumentReader()
    web_search = build_web_search_client(settings.websearch)

    engine = build_engine(settings.database.url, echo=settings.database.echo)
    sessionmaker = get_sessionmaker(engine)
    episode_repository = SqlEpisodeRepository(sessionmaker)
    semantic_memory = EpisodicSemanticMemory(vector_store, embedder)
    application_store = ApplicationStore()
    run_manager = WorkflowRunManager()

    log.info(
        "composition.container_built",
        llm_provider=llm.provider_name,
        environment=settings.environment.value,
        database=settings.database.url.split("://")[0],
    )

    return Container(
        settings=settings,
        llm=llm,
        embedder=embedder,
        vector_store=vector_store,
        retriever=retriever,
        document_reader=document_reader,
        web_search=web_search,
        engine=engine,
        sessionmaker=sessionmaker,
        episode_repository=episode_repository,
        semantic_memory=semantic_memory,
        application_store=application_store,
        run_manager=run_manager,
    )


async def bootstrap(container: Container) -> None:
    """One-time startup work: create tables, ingest the policy knowledge base."""
    await create_all(container.engine)
    chunk_count = await ingest_knowledge_base(
        container.settings.knowledge_base_dir, container.vector_store, container.embedder
    )
    log.info("composition.bootstrap_complete", policy_chunks=chunk_count)


def knowledge_base_dir(container: Container) -> Path:
    return container.settings.knowledge_base_dir


def build_workflow_graph(container: Container):
    """Compile the Supervisor LangGraph workflow from this container's dependencies.

    Imported lazily inside the function (rather than at module top-level) to
    keep ``composition.py`` importable even in contexts — like a lightweight
    CLI subcommand — that don't need LangGraph at all.
    """
    from scholarai.application.orchestration.graph import build_graph

    return build_graph(container.agent_deps, max_critic_revisions=container.settings.review.max_critic_revisions)
