import logging
from functools import lru_cache
from threading import Lock

from pymilvus import MilvusClient, DataType
from langchain_openai import OpenAIEmbeddings
from app.core.config import settings

logger = logging.getLogger(__name__)

_client: MilvusClient | None = None
_client_lock = Lock()


@lru_cache(maxsize=1)
def get_embeddings_model() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        api_key=settings.OPENROUTER_API_KEY,
        base_url=settings.OPENROUTER_BASE_URL,
        default_headers={
            "HTTP-Referer": settings.APP_URL,
            "X-Title": settings.APP_NAME,
        },
    )


def create_collection(client: MilvusClient, embedding_dim: int) -> None:
    schema = client.create_schema(
        auto_id=True,
        enable_dynamic_field=False,
        description="Хранилище DDL и SQL примеров для RAG",
    )

    schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
    schema.add_field(field_name="doc_type", datatype=DataType.VARCHAR, max_length=50)
    schema.add_field(field_name="text_content", datatype=DataType.VARCHAR, max_length=4000)
    schema.add_field(field_name="embedding", datatype=DataType.FLOAT_VECTOR, dim=embedding_dim)

    index_params = client.prepare_index_params()
    index_params.add_index(
        field_name="embedding",
        metric_type="COSINE",
        index_type="HNSW",
        index_name="vector_index",
        params={"M": 8, "efConstruction": 64},
    )

    client.create_collection(
        collection_name=settings.COLLECTION_NAME,
        schema=schema,
        index_params=index_params,
    )
    logger.info("Создана коллекция %s и индекс HNSW.", settings.COLLECTION_NAME)


def get_milvus_client() -> MilvusClient:
    global _client
    if _client is not None:
        return _client

    with _client_lock:
        if _client is None:
            client = MilvusClient(uri=settings.MILVUS_URI)
            if not client.has_collection(collection_name=settings.COLLECTION_NAME):
                client.close()
                raise RuntimeError(
                    "RAG-коллекция не инициализирована. Выполните `python -m data.load_data`."
                )
            client.load_collection(collection_name=settings.COLLECTION_NAME)
            _client = client
            logger.info("Коллекция %s загружена.", settings.COLLECTION_NAME)

    return _client


def close_milvus_client() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


def reset_collection(client: MilvusClient, embedding_dim: int) -> None:
    if client.has_collection(collection_name=settings.COLLECTION_NAME):
        client.drop_collection(collection_name=settings.COLLECTION_NAME)
    create_collection(client, embedding_dim)
    client.load_collection(collection_name=settings.COLLECTION_NAME)


def search_ddl_and_examples(question: str, top_k: int = 3) -> str:
    try:
        client = get_milvus_client()
        query_vector = get_embeddings_model().embed_query(question)

        search_params = {
            "metric_type": "COSINE",
            "params": {"ef": 64}
        }

        common_search_args = {
            "collection_name": settings.COLLECTION_NAME,
            "data": [query_vector],
            "search_params": search_params,
            "output_fields": ["doc_type", "text_content"],
        }
        ddl_results = client.search(
            **common_search_args,
            filter='doc_type == "ddl_table"',
            limit=len(settings.sql_allowed_tables),
        )
        example_results = client.search(
            **common_search_args,
            filter='doc_type == "few_shot_sql"',
            limit=top_k,
        )

        context_parts = []
        for hits in [*ddl_results, *example_results]:
            for hit in hits:
                entity = hit.get("entity", {})
                doc_type = entity.get("doc_type")
                text = entity.get("text_content")

                if doc_type == "ddl_table":
                    context_parts.append(f"[СХЕМА ТАБЛИЦЫ]\n{text}")
                elif doc_type == "few_shot_sql":
                    context_parts.append(f"[ПРИМЕР ЗАПРОСА]\n{text}")
                else:
                    context_parts.append(text)

        return "\n\n".join(context_parts)

    except Exception:
        logger.exception("Ошибка при поиске в Milvus")
        raise
