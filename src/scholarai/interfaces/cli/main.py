"""``scholarai`` CLI entry point.

Commands::

    scholarai status                                   -- print configuration wiring
    scholarai scholarships                             -- list available scholarship presets
    scholarai submit -s merit_scholarship -f a.pdf      -- create an application
    scholarai evaluate --application APP-XXXXXXXX       -- run the Supervisor workflow
    scholarai decide --application APP-XXXXXXXX -a approve  -- record a human decision
    scholarai applications                              -- list in-flight applications
    scholarai memory STUDENT-001                        -- recall prior evaluations
    scholarai knowledge search "minimum GPA"             -- search the policy knowledge base
    scholarai demo                                      -- run a full synthetic evaluation end to end
    scholarai serve                                      -- start the HTTP API
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from scholarai import __version__
from scholarai.application.use_cases.apply_human_decision import apply_human_decision
from scholarai.application.use_cases.get_memory import get_student_history
from scholarai.application.use_cases.knowledge_base import search_knowledge_base
from scholarai.application.use_cases.run_evaluation import run_evaluation
from scholarai.application.use_cases.submit_application import create_application
from scholarai.composition import Container, bootstrap, build_container, build_workflow_graph
from scholarai.domain.errors import ScholarAIError
from scholarai.domain.models.human import HumanAction, HumanDecision
from scholarai.domain.scholarship_presets import PRESETS


def _print_json(payload: object) -> None:
    print(json.dumps(payload, indent=2, default=str))


async def _built_container() -> Container:
    container = build_container()
    await bootstrap(container)
    return container


def cmd_status(_args: argparse.Namespace) -> None:
    async def run() -> None:
        container = await _built_container()
        print(f"ScholarAI Workforce v{__version__}")
        print(f"  environment       : {container.settings.environment.value}")
        print(f"  llm provider      : {container.llm.provider_name}")
        print(f"  database          : {container.settings.database.url}")
        vector_store_url = container.settings.vectorstore.url
        vector_store_desc = f"qdrant @ {vector_store_url}" if vector_store_url else "in-memory qdrant"
        print(f"  vector store      : {vector_store_desc}")
        web_search_desc = "enabled" if container.web_search else "disabled (no TAVILY_API_KEY)"
        print(f"  web search        : {web_search_desc}")
        print(f"  scholarships      : {', '.join(PRESETS)}")

    asyncio.run(run())


def cmd_scholarships(_args: argparse.Namespace) -> None:
    for preset in PRESETS.values():
        print(f"{preset.code:>24} | {preset.name} - {preset.description}")


def cmd_submit(args: argparse.Namespace) -> None:
    async def run() -> None:
        container = await _built_container()
        files = []
        for path_str in args.file:
            path = Path(path_str)
            files.append((path.name, path.read_bytes()))
        application = create_application(
            container.application_store, container.document_reader, args.scholarship, files
        )
        _print_json(application.model_dump(mode="json"))

    asyncio.run(run())


def cmd_evaluate(args: argparse.Namespace) -> None:
    async def run() -> None:
        container = await _built_container()
        graph = build_workflow_graph(container)
        final_state = await run_evaluation(container.application_store, graph, args.application)
        print(f"status: {final_state['status']}")
        print(f"critic revisions: {final_state['critic_revisions']}")
        _print_json(final_state.get("evaluation"))

    asyncio.run(run())


def cmd_decide(args: argparse.Namespace) -> None:
    async def run() -> None:
        container = await _built_container()
        decision = HumanDecision(
            application_id=args.application, action=HumanAction(args.action), reviewer=args.reviewer, notes=args.notes
        )
        state = await apply_human_decision(
            container.application_store,
            container.episode_repository,
            container.semantic_memory,
            args.application,
            decision,
        )
        _print_json(state.get("final_recommendation"))

    asyncio.run(run())


def cmd_applications(_args: argparse.Namespace) -> None:
    async def run() -> None:
        container = await _built_container()
        for state in container.application_store.all():
            print(f"{state['application_id']:>12} | {state['scholarship_code']:<24} | {state['status']}")

    asyncio.run(run())


def cmd_memory(args: argparse.Namespace) -> None:
    async def run() -> None:
        container = await _built_container()
        episodes = await get_student_history(container.episode_repository, args.student_id)
        _print_json(episodes)

    asyncio.run(run())


def cmd_knowledge_search(args: argparse.Namespace) -> None:
    async def run() -> None:
        container = await _built_container()
        results = await search_knowledge_base(container.retriever, args.query)
        _print_json(results)

    asyncio.run(run())


def cmd_demo(_args: argparse.Namespace) -> None:
    from scholarai.interfaces.cli.demo import run_demo

    asyncio.run(run_demo())


def cmd_serve(args: argparse.Namespace) -> None:
    import uvicorn

    uvicorn.run("scholarai.interfaces.api.app:app", host=args.host, port=args.port, reload=args.reload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="scholarai", description="ScholarAI Workforce CLI")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status", help="show configuration wiring").set_defaults(func=cmd_status)
    subparsers.add_parser("scholarships", help="list scholarship presets").set_defaults(func=cmd_scholarships)

    submit = subparsers.add_parser("submit", help="create an application from local files")
    submit.add_argument("-s", "--scholarship", required=True, choices=list(PRESETS))
    submit.add_argument("-f", "--file", action="append", default=[], help="document path (repeatable)")
    submit.set_defaults(func=cmd_submit)

    evaluate = subparsers.add_parser("evaluate", help="run the Supervisor workflow")
    evaluate.add_argument("--application", required=True)
    evaluate.set_defaults(func=cmd_evaluate)

    decide = subparsers.add_parser("decide", help="record a human decision")
    decide.add_argument("--application", required=True)
    decide.add_argument("-a", "--action", required=True, choices=[a.value for a in HumanAction])
    decide.add_argument("--reviewer", default="reviewer")
    decide.add_argument("--notes", default="")
    decide.set_defaults(func=cmd_decide)

    subparsers.add_parser("applications", help="list in-flight applications").set_defaults(func=cmd_applications)

    memory = subparsers.add_parser("memory", help="recall an student's prior evaluations")
    memory.add_argument("student_id")
    memory.set_defaults(func=cmd_memory)

    knowledge = subparsers.add_parser("knowledge", help="policy knowledge base operations")
    knowledge_sub = knowledge.add_subparsers(dest="knowledge_command", required=True)
    knowledge_search = knowledge_sub.add_parser("search", help="search the policy knowledge base")
    knowledge_search.add_argument("query")
    knowledge_search.set_defaults(func=cmd_knowledge_search)

    subparsers.add_parser("demo", help="run a full synthetic evaluation end to end").set_defaults(func=cmd_demo)

    serve = subparsers.add_parser("serve", help="start the HTTP API")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--reload", action="store_true")
    serve.set_defaults(func=cmd_serve)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except ScholarAIError as exc:
        print(f"error: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
