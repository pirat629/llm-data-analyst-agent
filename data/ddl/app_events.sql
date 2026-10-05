CREATE TABLE app_events (
    event_id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(user_id),
    event_time TIMESTAMP NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    platform VARCHAR(20)
);