-- 1 (import users.csv)
CREATE TABLE users (
    id             INTEGER       NOT NULL PRIMARY KEY,
    created_at     TIMESTAMP     NOT NULL,
    email          VARCHAR(100)  NOT NULL UNIQUE,
    first_name     VARCHAR(50)   NOT NULL,
    last_name      VARCHAR(50)   NOT NULL,
    password_hash  VARCHAR(100)  NOT NULL,
    phone          VARCHAR(20)   NOT NULL,
    updated_at     TIMESTAMP     NOT NULL
);
 
-- 2 (import products.csv)
CREATE TABLE products (
    id                INTEGER        NOT NULL PRIMARY KEY,
    brand_id          INTEGER        NOT NULL,
    category_id       INTEGER        NOT NULL,
    compare_at_price  NUMERIC(10,2),
    created_at        TIMESTAMP      NOT NULL,
    description       VARCHAR(100)   NOT NULL,
    is_active         BOOLEAN        NOT NULL,
    name              VARCHAR(100)   NOT NULL,
    price             NUMERIC(10,2)  NOT NULL,
    sku               VARCHAR(30)    NOT NULL UNIQUE,
    slug              VARCHAR(30)    NOT NULL UNIQUE
);
 
-- 3 (import return_reasons.csv)
CREATE TABLE return_reasons (
    id           INTEGER      NOT NULL PRIMARY KEY,
    reason_text  VARCHAR(50)  NOT NULL
);
 
-- 4 (import order_statuses.csv)
CREATE TABLE order_statuses (
    id           INTEGER      NOT NULL PRIMARY KEY,
    description  VARCHAR(50)  NOT NULL,
    status_name  VARCHAR(30)  NOT NULL
);
 
-- 5 (import orders.csv)
CREATE TABLE orders (
    id                   INTEGER        NOT NULL PRIMARY KEY,
    billing_address_id   INTEGER        NOT NULL,
    coupon_id            INTEGER,
    created_at           TIMESTAMP      NOT NULL,
    discount_amount      NUMERIC(10,2)  NOT NULL,
    order_status_id      INTEGER        NOT NULL REFERENCES order_statuses(id),
    shipping_address_id  INTEGER        NOT NULL,
    shipping_cost        NUMERIC(10,2)  NOT NULL,
    shipping_method_id   INTEGER        NOT NULL,
    subtotal             NUMERIC(10,2)  NOT NULL,
    tax_amount           NUMERIC(10,2)  NOT NULL,
    total                NUMERIC(10,2)  NOT NULL,
    user_id              INTEGER        NOT NULL REFERENCES users(id)
);
 
-- 6 (import order_items.csv)
CREATE TABLE order_items (
    id               INTEGER        NOT NULL PRIMARY KEY,
    discount_amount  NUMERIC(10,2)  NOT NULL,
    order_id         INTEGER        NOT NULL REFERENCES orders(id),
    product_id       INTEGER        NOT NULL REFERENCES products(id),
    quantity         INTEGER        NOT NULL,
    tax_amount       NUMERIC(10,2)  NOT NULL,
    unit_price       NUMERIC(10,2)  NOT NULL
);
 
-- 7 (import order_returns.csv)
CREATE TABLE order_returns (
    id             INTEGER      NOT NULL PRIMARY KEY,
    order_item_id  INTEGER      NOT NULL REFERENCES order_items(id),
    processed_at   TIMESTAMP    NOT NULL,
    quantity       INTEGER      NOT NULL,
    reason_id      INTEGER      NOT NULL REFERENCES return_reasons(id),
    requested_at   TIMESTAMP    NOT NULL,
    status         VARCHAR(20)  NOT NULL
);
 
-- 8 (import shipments.csv)
CREATE TABLE shipments (
    id               INTEGER      NOT NULL PRIMARY KEY,
    delivered_at     TIMESTAMP    NOT NULL,
    order_id         INTEGER      NOT NULL REFERENCES orders(id),
    shipped_at       TIMESTAMP    NOT NULL,
    tracking_number  VARCHAR(30)  NOT NULL UNIQUE
);
 
-- 9 (import payments.csv)
CREATE TABLE payments (
    id                     INTEGER        NOT NULL PRIMARY KEY,
    amount                 NUMERIC(10,2)  NOT NULL,
    order_id               INTEGER        NOT NULL REFERENCES orders(id),
    payment_method_id      INTEGER        NOT NULL,
    processed_at           TIMESTAMP      NOT NULL,
    status                 VARCHAR(20)    NOT NULL,
    transaction_reference  VARCHAR(30)    NOT NULL UNIQUE
);
 
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;

SELECT 'users' AS tbl, COUNT(*) FROM users
UNION ALL SELECT 'products', COUNT(*) FROM products
UNION ALL SELECT 'return_reasons', COUNT(*) FROM return_reasons
UNION ALL SELECT 'order_statuses', COUNT(*) FROM order_statuses
UNION ALL SELECT 'orders', COUNT(*) FROM orders
UNION ALL SELECT 'order_items', COUNT(*) FROM order_items
UNION ALL SELECT 'order_returns', COUNT(*) FROM order_returns
UNION ALL SELECT 'shipments', COUNT(*) FROM shipments
UNION ALL SELECT 'payments', COUNT(*) FROM payments;