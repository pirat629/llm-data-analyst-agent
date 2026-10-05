CREATE TABLE payments (
    payment_id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(user_id),
    payment_date TIMESTAMP NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(20)
);