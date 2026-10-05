import uuid
import random
import logging
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_URI = settings.DATABASE_ADMIN_URI


def generate_mock_data():
    random.seed(42)
    users, payments, events, tickets = [], [], [], []

    countries = ["USA", "Germany", "France", "Spain", "UK", "Kazakhstan"]
    plans = ["free", "basic", "premium"]
    statuses = ["success", "success", "success", "success", "failed", "refunded"]
    event_types = ["login", "view_item", "view_item", "add_to_cart", "checkout"]
    platforms = ["ios", "android", "web"]
    ticket_categories = ["billing", "technical", "general"]

    start_date = datetime(2026, 1, 1)
    end_date = datetime(2026, 12, 31)

    for _ in range(100):
        user_id = str(uuid.uuid4())
        reg_date = start_date + timedelta(days=random.randint(0, 300))

        users.append({
            "user_id": user_id,
            "registration_date": reg_date.strftime("%Y-%m-%d"),
            "country": random.choice(countries),
            "subscription_plan": random.choice(plans)
        })

        for _ in range(random.randint(1, 5)):
            pay_date = min(reg_date + timedelta(days=random.randint(1, 60)), end_date)
            payments.append({
                "payment_id": str(uuid.uuid4()),
                "user_id": user_id,
                "payment_date": pay_date.strftime("%Y-%m-%d %H:%M:%S"),
                "amount": round(random.uniform(5.0, 99.99), 2),
                "status": random.choice(statuses)
            })

        user_platform = random.choice(platforms)
        for _ in range(random.randint(10, 50)):
            event_date = min(reg_date + timedelta(days=random.randint(0, 100)), end_date)
            events.append({
                "event_id": str(uuid.uuid4()),
                "user_id": user_id,
                "event_time": event_date.strftime("%Y-%m-%d %H:%M:%S"),
                "event_type": random.choice(event_types),
                "platform": user_platform
            })

        for _ in range(random.randint(0, 3)):
            created_at = min(reg_date + timedelta(days=random.randint(5, 120)), end_date)

            is_resolved = random.random() < 0.8
            resolved_at = None
            score = None

            if is_resolved:
                resolved_at = min(created_at + timedelta(hours=random.randint(1, 72)), end_date)
                score = random.randint(1, 5)
                resolved_at = resolved_at.strftime("%Y-%m-%d %H:%M:%S")

            tickets.append({
                "ticket_id": str(uuid.uuid4()),
                "user_id": user_id,
                "created_at": created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "resolved_at": resolved_at,
                "category": random.choice(ticket_categories),
                "satisfaction_score": score
            })

    return users, payments, events, tickets


def seed_database():
    engine = create_engine(DB_URI)

    create_tables_sql = """
    CREATE TABLE IF NOT EXISTS users (
        user_id UUID PRIMARY KEY,
        registration_date DATE NOT NULL,
        country VARCHAR(50),
        subscription_plan VARCHAR(20)
    );

    CREATE TABLE IF NOT EXISTS payments (
        payment_id UUID PRIMARY KEY,
        user_id UUID REFERENCES users(user_id),
        payment_date TIMESTAMP NOT NULL,
        amount DECIMAL(10, 2) NOT NULL,
        status VARCHAR(20)
    );
    
    CREATE TABLE IF NOT EXISTS app_events (
        event_id UUID PRIMARY KEY,
        user_id UUID REFERENCES users(user_id),
        event_time TIMESTAMP NOT NULL,
        event_type VARCHAR(50) NOT NULL,
        platform VARCHAR(20)
    );
    
    CREATE TABLE IF NOT EXISTS support_tickets (
        ticket_id UUID PRIMARY KEY,
        user_id UUID REFERENCES users(user_id),
        created_at TIMESTAMP NOT NULL,
        resolved_at TIMESTAMP,
        category VARCHAR(50),
        satisfaction_score INT CHECK (satisfaction_score BETWEEN 1 AND 5)
    );
    """

    logger.info("Подключение к PostgreSQL...")

    with engine.connect() as conn:
        with conn.begin():
            logger.info("Удаление старых данных...")

            conn.execute(text("DROP TABLE IF EXISTS support_tickets;"))
            conn.execute(text("DROP TABLE IF EXISTS app_events;"))
            conn.execute(text("DROP TABLE IF EXISTS payments;"))
            conn.execute(text("DROP TABLE IF EXISTS users;"))

            logger.info("Создание 4-х таблиц...")
            conn.execute(text(create_tables_sql))

            users, payments, events, tickets = generate_mock_data()

            logger.info(f"Вставка {len(users)} пользователей...")
            conn.execute(
                text(
                    "INSERT INTO users (user_id, registration_date, country, subscription_plan) VALUES (:user_id, :registration_date, :country, :subscription_plan)"),
                users
            )

            logger.info(f"Вставка {len(payments)} платежей...")
            conn.execute(
                text(
                    "INSERT INTO payments (payment_id, user_id, payment_date, amount, status) VALUES (:payment_id, :user_id, :payment_date, :amount, :status)"),
                payments
            )

            logger.info(f"Вставка {len(events)} событий аналитики...")
            conn.execute(
                text(
                    "INSERT INTO app_events (event_id, user_id, event_time, event_type, platform) VALUES (:event_id, :user_id, :event_time, :event_type, :platform)"),
                events
            )

            logger.info(f"Вставка {len(tickets)} тикетов поддержки...")
            conn.execute(
                text(
                    "INSERT INTO support_tickets (ticket_id, user_id, created_at, resolved_at, category, satisfaction_score) VALUES (:ticket_id, :user_id, :created_at, :resolved_at, :category, :satisfaction_score)"),
                tickets
            )

    logger.info("Успех! База данных заполнена.")


if __name__ == "__main__":
    seed_database()
