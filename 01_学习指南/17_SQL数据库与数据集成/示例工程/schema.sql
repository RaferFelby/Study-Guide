BEGIN;
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    name TEXT NOT NULL,
    UNIQUE(user_id, tenant_id)
);
CREATE TABLE products (
    product_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);
CREATE TABLE tickets (
    ticket_id INTEGER PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    external_id TEXT NOT NULL,
    source_version INTEGER NOT NULL CHECK(source_version >= 1),
    payload_hash TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    product_id INTEGER,
    status TEXT NOT NULL CHECK(status IN ('open', 'resolved')),
    priority INTEGER NOT NULL CHECK(priority BETWEEN 1 AND 3),
    amount_cents INTEGER CHECK(amount_cents >= 0),
    created_at TEXT NOT NULL,
    UNIQUE(tenant_id, source_id, external_id),
    FOREIGN KEY(user_id, tenant_id) REFERENCES users(user_id, tenant_id),
    FOREIGN KEY(product_id) REFERENCES products(product_id)
);
CREATE TABLE events (
    event_id INTEGER PRIMARY KEY,
    ticket_id INTEGER NOT NULL REFERENCES tickets(ticket_id),
    event_type TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX idx_tickets_tenant_status_created
    ON tickets(tenant_id, status, created_at DESC, ticket_id DESC);
CREATE INDEX idx_events_ticket ON events(ticket_id);
PRAGMA user_version = 1;
COMMIT;
