import json

import httpx

from packages.config_core.loader import VectorDBConfig
from packages.rag_core.schemas import IndexedChunk
from packages.rag_core.vector_store import QdrantVectorStore, build_vector_store


def test_json_chunk_store_can_prune_missing_managed_sources(tmp_path) -> None:
    from packages.rag_core.store import JsonChunkStore

    existing = tmp_path / "existing.md"
    existing.write_text("managed", encoding="utf-8")
    chunks = [
        IndexedChunk(
            chunk_id="existing",
            source_path=str(existing),
            chunk_text="managed",
            hash="a",
            embedding=[1.0],
        ),
        IndexedChunk(
            chunk_id="missing",
            source_path=str(tmp_path / "missing.md"),
            chunk_text="stale",
            hash="b",
            embedding=[1.0],
        ),
    ]
    path = tmp_path / "index.json"
    JsonChunkStore(path).save(chunks)

    loaded = JsonChunkStore(path, prune_missing_sources=True).load()

    assert [chunk.chunk_id for chunk in loaded] == ["existing"]


def test_qdrant_vector_store_replace_and_search() -> None:
    state = {
        "collection_exists": False,
        "points": {},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        method = request.method

        if method == "GET" and path == "/collections/local_docs":
            if state["collection_exists"]:
                return httpx.Response(200, json={"result": {"status": "green"}})
            return httpx.Response(404, json={"status": "not found"})

        if method == "PUT" and path == "/collections/local_docs":
            state["collection_exists"] = True
            return httpx.Response(200, json={"result": True})

        if method == "POST" and path == "/collections/local_docs/points/scroll":
            points = []
            for point_id, point in state["points"].items():
                points.append({"id": point_id, "payload": point["payload"]})
            return httpx.Response(200, json={"result": {"points": points, "next_page_offset": None}})

        if method == "POST" and path == "/collections/local_docs/points/delete":
            return httpx.Response(200, json={"result": {"status": "acknowledged"}})

        if method == "PUT" and path == "/collections/local_docs/points":
            data = json.loads(request.content.decode("utf-8"))
            for point in data["points"]:
                state["points"][str(point["id"])] = point
            return httpx.Response(200, json={"result": {"status": "acknowledged"}})

        if method == "POST" and path == "/collections/local_docs/points/count":
            return httpx.Response(200, json={"result": {"count": len(state["points"])}})

        if method == "POST" and path == "/collections/local_docs/points/query":
            results = []
            for point_id, point in state["points"].items():
                payload = point["payload"]
                if payload.get("project") == "lab":
                    results.append({"id": point_id, "score": 0.9, "payload": payload})
            return httpx.Response(200, json={"result": {"points": results}})

        raise AssertionError(f"Unexpected request: {method} {path}")

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport, base_url="http://testserver")
    store = QdrantVectorStore(
        config=VectorDBConfig(provider="qdrant", url="http://testserver", collection="local_docs"),
        client=client,
    )

    chunk = IndexedChunk(
        chunk_id="chunk-1",
        source_path="/tmp/docs/meeting.md",
        heading_path=["Meeting"],
        project="lab",
        tags=["npo"],
        chunk_text="employee roster confirmed",
        hash="abc",
        embedding=[0.1, 0.2, 0.3],
    )

    count = store.replace_for_paths(paths={"/tmp/docs"}, chunks=[chunk], vector_size=3)
    results = store.search(query_vector=[0.1, 0.2, 0.3], project="lab", source_path=None, tags=[], top_k=3)

    assert count == 1
    assert results
    assert results[0].source_path == "/tmp/docs/meeting.md"


def test_local_json_vector_store_search_can_filter_by_source_path(tmp_path) -> None:
    from packages.rag_core.store import JsonChunkStore
    from packages.rag_core.vector_store import LocalJsonVectorStore

    store = LocalJsonVectorStore(store=JsonChunkStore(tmp_path / "index.json"))
    chunk_a = IndexedChunk(
        chunk_id="chunk-a",
        source_path="/tmp/docs/a.md",
        heading_path=["A"],
        project="lab",
        tags=[],
        chunk_text="employee roster confirmed",
        hash="a",
        embedding=[0.1, 0.2],
    )
    chunk_b = IndexedChunk(
        chunk_id="chunk-b",
        source_path="/tmp/docs/b.md",
        heading_path=["B"],
        project="lab",
        tags=[],
        chunk_text="different content",
        hash="b",
        embedding=[0.1, 0.2],
    )
    store.replace_for_paths(paths={"/tmp/docs"}, chunks=[chunk_a, chunk_b], vector_size=2)

    results = store.search(query_vector=[0.1, 0.2], project="lab", source_path="/tmp/docs/a.md", tags=[], top_k=5)

    assert len(results) == 1
    assert results[0].source_path == "/tmp/docs/a.md"


def test_local_json_vector_store_search_can_filter_by_tags(tmp_path) -> None:
    from packages.rag_core.store import JsonChunkStore
    from packages.rag_core.vector_store import LocalJsonVectorStore

    store = LocalJsonVectorStore(store=JsonChunkStore(tmp_path / "index.json"))
    chunk_a = IndexedChunk(
        chunk_id="chunk-a",
        source_path="/tmp/docs/a.md",
        heading_path=["A"],
        project="lab",
        tags=["research", "vector"],
        chunk_text="employee roster confirmed",
        hash="a",
        embedding=[0.1, 0.2],
    )
    chunk_b = IndexedChunk(
        chunk_id="chunk-b",
        source_path="/tmp/docs/b.md",
        heading_path=["B"],
        project="lab",
        tags=["npo"],
        chunk_text="different content",
        hash="b",
        embedding=[0.1, 0.2],
    )
    store.replace_for_paths(paths={"/tmp/docs"}, chunks=[chunk_a, chunk_b], vector_size=2)

    results = store.search(query_vector=[0.1, 0.2], project="lab", source_path=None, tags=["research"], top_k=5)

    assert len(results) == 1
    assert results[0].source_path == "/tmp/docs/a.md"


def test_qdrant_vector_store_load_chunks() -> None:
    state = {
        "points": {
            "chunk-1": {
                "payload": {
                    "chunk_id": "chunk-1",
                    "source_path": "/tmp/docs/meeting.md",
                    "heading_path": ["Meeting"],
                    "project": "lab",
                    "tags": ["npo"],
                    "chunk_text": "employee roster confirmed",
                    "hash": "abc",
                }
            }
        },
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/collections/local_docs/points/scroll":
            return httpx.Response(200, json={"result": {"points": [{"id": "chunk-1", "payload": state["points"]["chunk-1"]["payload"]}], "next_page_offset": None}})
        raise AssertionError(f"Unexpected request: {request.method} {request.url.path}")

    store = QdrantVectorStore(
        config=VectorDBConfig(provider="qdrant", url="http://testserver", collection="local_docs"),
        client=httpx.Client(transport=httpx.MockTransport(handler), base_url="http://testserver"),
    )

    chunks = store.load_chunks(project="lab")

    assert len(chunks) == 1
    assert chunks[0].chunk_id == "chunk-1"
    assert chunks[0].embedding is None


def test_qdrant_vector_store_search_includes_tag_filters() -> None:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/collections/local_docs/points/query":
            captured["body"] = json.loads(request.content.decode("utf-8"))
            return httpx.Response(200, json={"result": []})
        raise AssertionError(f"Unexpected request: {request.method} {request.url.path}")

    store = QdrantVectorStore(
        config=VectorDBConfig(provider="qdrant", url="http://testserver", collection="local_docs"),
        client=httpx.Client(transport=httpx.MockTransport(handler), base_url="http://testserver"),
    )

    store.search(query_vector=[0.1, 0.2], project="lab", source_path="/tmp/docs/a.md", tags=["research", "vector"], top_k=5)

    assert captured["body"]["filter"]["must"] == [
        {"key": "project", "match": {"value": "lab"}},
        {"key": "source_path", "match": {"value": "/tmp/docs/a.md"}},
        {"key": "tags", "match": {"value": "research"}},
        {"key": "tags", "match": {"value": "vector"}},
    ]


def test_resilient_vector_store_falls_back_to_local_json_when_qdrant_is_unavailable(tmp_path) -> None:
    config = VectorDBConfig(
        provider="qdrant",
        url="http://127.0.0.1:9",
        collection="local_docs",
        store_path=str(tmp_path / "index.json"),
    )
    store = build_vector_store(config=config, client=httpx.Client(transport=httpx.MockTransport(lambda request: (_ for _ in ()).throw(httpx.ConnectError("down")))))

    chunk = IndexedChunk(
        chunk_id="chunk-1",
        source_path="/tmp/docs/meeting.md",
        heading_path=["Meeting"],
        project="lab",
        tags=["npo"],
        chunk_text="employee roster confirmed",
        hash="abc",
        embedding=[0.1, 0.2, 0.3],
    )

    count = store.replace_for_paths(paths={"/tmp/docs"}, chunks=[chunk], vector_size=3)
    results = store.search(query_vector=[0.1, 0.2, 0.3], project="lab", source_path=None, tags=[], top_k=3)
    chunks = store.load_chunks(project="lab")

    assert count == 1
    assert results
    assert results[0].source_path == "/tmp/docs/meeting.md"
    assert len(chunks) == 1
    assert chunks[0].chunk_id == "chunk-1"
