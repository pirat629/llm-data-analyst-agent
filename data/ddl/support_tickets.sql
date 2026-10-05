CREATE TABLE support_tickets (
    ticket_id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(user_id),
    created_at TIMESTAMP NOT NULL,
    resolved_at TIMESTAMP,
    category VARCHAR(50),
    satisfaction_score INT CHECK (satisfaction_score BETWEEN 1 AND 5)
);