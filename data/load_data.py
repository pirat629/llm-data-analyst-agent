import json
import logging
from pathlib import Path
from pymilvus import MilvusClient

from app.core.config import settings
from app.services.milvus_service import get_embeddings_model, reset_collection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
DDL_DIR = BASE_DIR / "ddl"
EXAMPLES_FILE = BASE_DIR / "few_shot_examples.json"


def get_raw_documents() -> list[dict]:
    documents = []

    if DDL_DIR.exists() and DDL_DIR.is_dir():
        for sql_file in DDL_DIR.glob("*.sql"):
            with open(sql_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    documents.append({
                        "doc_type": "ddl_table",
                        "text": content
                    })
        logger.info(f"Загружено {len(documents)} DDL-схем из {DDL_DIR}")
    else:
        logger.warning(f"Директория {DDL_DIR} не найдена!")

    if EXAMPLES_FILE.exists():
        with open(EXAMPLES_FILE, "r", encoding="utf-8") as f:
            examples = json.load(f)
            for ex in examples:
                combined_text = f"-- Вопрос: {ex['question']}\n{ex['sql']}"
                documents.append({
                    "doc_type": "few_shot_sql",
                    "text": combined_text
                })
        logger.info(f"Загружено {len(examples)} SQL-примеров из {EXAMPLES_FILE.name}")
    else:
        logger.warning(f"Файл {EXAMPLES_FILE} не найден!")

    return documents


def load_initial_data():
    client = MilvusClient(uri=settings.MILVUS_URI)

    raw_documents = get_raw_documents()

    if not raw_documents:
        logger.error("Нет данных для загрузки. Проверьте папку data/")
        return

    logger.info("Генерация эмбеддингов (это может занять несколько секунд)...")

    texts_to_embed = [doc["text"] for doc in raw_documents]
    vectors = get_embeddings_model().embed_documents(texts_to_embed)
    if not vectors:
        raise RuntimeError("Провайдер эмбеддингов не вернул векторы.")

    reset_collection(client, embedding_dim=len(vectors[0]))

    data_to_insert = []
    for doc, vector in zip(raw_documents, vectors):
        data_to_insert.append({
            "doc_type": doc["doc_type"],
            "text_content": doc["text"],
            "embedding": vector
        })

    logger.info(f"Вставляем {len(data_to_insert)} записей в {settings.COLLECTION_NAME}...")
    insert_result = client.insert(
        collection_name=settings.COLLECTION_NAME,
        data=data_to_insert
    )

    logger.info(f"Успешно вставлено записей: {insert_result['insert_count']}")


if __name__ == "__main__":
    load_initial_data()
