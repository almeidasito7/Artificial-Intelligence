from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.config import get_settings
from src.core.router_factory import build_router
from src.rag.document_loader import load_documents
from src.rag.chunker import chunk_documents
from src.rag.embeddings import generate_embeddings
from src.rag.vector_store import upsert_embeddings
from src.rag.retriever import retrieve_chunks
from src.utils.logger import get_logger
from src.mcp.registry import MCPRegistry


app = FastAPI(title="Conversational BI Assistant")
logger = get_logger(__name__)

_router = None
_mcp_registry = None


def _get_router():
    global _router
    if _router is None:
        _router = build_router()
    return _router


def _get_mcp_registry():
    global _mcp_registry
    if _mcp_registry is None:
        settings = get_settings()
        _mcp_registry = MCPRegistry(tools_json=settings.MCP_TOOLS_JSON)
    return _mcp_registry


settings = get_settings()
cors_origins = [o.strip() for o in (settings.CORS_ORIGINS or "").split(",") if o.strip()]

if settings.is_dev:
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Request Schema
class QueryRequest(BaseModel):
    question: str
    user_id: str = "carol.chen"


# Response Schema
class QueryResponse(BaseModel):
    answer: str
    cache_hit: bool
    engine_used: str | None
    sources: list[str]


# Health check
@app.get("/")
def root():
    return {"status": "ok"}


# Main Query Endpoint — powered by Router (Orchestrator)
@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    settings = get_settings()

    try:
        result = _get_router().handle(
            question=request.question,
            user_id=request.user_id,
        )

        return {
            "answer": result["answer"],
            "cache_hit": bool(result.get("cache_hit", False)),
            "engine_used": result.get("engine_used"),
            "sources": list(result.get("sources", [])),
        }

    except Exception as e:
        logger.error(f"Router error: {e}")

        return {
            "answer": "Something went wrong. Please try again in a few minutes.",
            "cache_hit": False,
            "engine_used": None,
            "sources": [],
        }


# Index Documents Endpoint
@app.post("/rag/index")
def index_documents():
    documents = load_documents()
    chunks = chunk_documents(documents)
    embedded_chunks = generate_embeddings(chunks)

    upsert_embeddings(embedded_chunks)

    return {
        "documents": len(documents),
        "chunks": len(chunks),
        "indexed": len(embedded_chunks)
    }


# Test Endpoints
@app.get("/rag/load-docs")
def test_load_docs():
    docs = load_documents()
    return {
        "total": len(docs),
        "sample": docs[:2]
    }


@app.get("/rag/chunks")
def test_chunks():
    docs = load_documents()
    chunks = chunk_documents(docs)

    return {
        "total_chunks": len(chunks),
        "sample": chunks[:2]
    }


@app.get("/rag/embeddings")
def test_embeddings():
    documents = load_documents()
    chunks = chunk_documents(documents)
    embedded_chunks = generate_embeddings(chunks)

    sample = embedded_chunks[:2]

    return {
        "total_documents": len(documents),
        "total_chunks": len(chunks),
        "total_embeddings": len(embedded_chunks),
        "sample": [
            {
                "content_preview": item["content"][:200],
                "embedding_dimension": len(item["embedding"]),
                "metadata": item["metadata"]
            }
            for item in sample
        ]
    }


@app.get("/rag/retrieve")
def test_retriever(query: str):
    results = retrieve_chunks(query)

    return {
        "query": query,
        "results": results
    }


@app.get("/rag/debug/chunks")
def debug_chunks():
    from src.rag.vector_store import get_collection
    collection = get_collection()

    return {
        "count": collection.count()
    }


class MCPCallRequest(BaseModel):
    tool_name: str
    input: dict


@app.get("/mcp/tools")
def list_mcp_tools():
    return {"tools": _get_mcp_registry().list_tools()}


@app.post("/mcp/call")
def call_mcp_tool(request: MCPCallRequest):
    output = _get_mcp_registry().call_tool(request.tool_name, request.input)
    return {"tool_name": request.tool_name, "output": output}
