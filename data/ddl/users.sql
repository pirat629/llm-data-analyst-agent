CREATE TABLE users (
    user_id UUID PRIMARY KEY,
    registration_date DATE NOT NULL,
    country VARCHAR(50),
    subscription_plan VARCHAR(20)
);
