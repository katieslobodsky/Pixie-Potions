-- capacity table
CREATE TABLE capacity (
    capacity_id BIGSERIAL PRIMARY KEY NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    potion_capacity INT DEFAULT 1 NOT NULL,
    ml_capacity INT DEFAULT 1 NOT NULL
);

INSERT INTO capacity (potion_capacity, ml_capacity) 
VALUES (1, 1);

-- carts table
CREATE TABLE carts (
    cart_id BIGSERIAL PRIMARY KEY NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    checked_out BOOLEAN DEFAULT FALSE,
    customer_name TEXT NOT NULL,
    character_class TEXT NOT NULL,
    level INT NOT NULL CHECK (level > 0)
);

-- cart_items table
CREATE TABLE cart_items (
    item_id BIGSERIAL PRIMARY KEY NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    cart_id INT NOT NULL REFERENCES carts (cart_id) ON DELETE CASCADE,
    item_sku TEXT NOT NULL,
    quantity INT NOT NULL CHECK (quantity > 0),
    item_price INT CHECK (item_price >= 0),
    item_total INT CHECK (item_total >= 0)
);

-- gold_transactions table
CREATE TABLE gold_transactions (
    id BIGSERIAL PRIMARY KEY NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    gold INT NOT NULL CHECK (gold >= 0),
    message TEXT
);

INSERT INTO gold_transactions (gold) 
VALUES (100);

-- ml table
CREATE TABLE ml (
    id BIGSERIAL PRIMARY KEY NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    num_red_ml INT NOT NULL DEFAULT 0 CHECK (num_red_ml >= 0),
    num_green_ml INT NOT NULL DEFAULT 0 CHECK (num_green_ml >= 0),
    num_blue_ml INT NOT NULL DEFAULT 0 CHECK (num_blue_ml >= 0),
    num_dark_ml INT NOT NULL DEFAULT 0 CHECK (num_dark_ml >= 0),
    message TEXT
);

INSERT INTO ml (num_red_ml, num_green_ml, num_blue_ml, num_dark_ml) 
VALUES (0, 0, 0, 0);

-- potions table
CREATE TABLE potions (
    potion_id BIGSERIAL PRIMARY KEY NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    potion_name TEXT NOT NULL,
    red_percent INT CHECK (red_percent BETWEEN 0 AND 100),
    green_percent INT CHECK (green_percent BETWEEN 0 AND 100),
    blue_percent INT CHECK (blue_percent BETWEEN 0 AND 100),
    dark_percent INT CHECK (dark_percent BETWEEN 0 AND 100),
    price INT NOT NULL CHECK (price > 0),
    inventory INT NOT NULL DEFAULT 0
);

INSERT INTO potions (potion_name, red_percent, green_percent, blue_percent, dark_percent, price, inventory) VALUES
('Enchanted Emerald', 0, 50, 50, 0, 25, 0),
('Bubbly Boysenberry', 40, 0, 40, 20, 75, 0),
('Ocean Odyssey', 5, 10, 85, 0, 25, 0),
('Fiery Fizz', 90, 0, 0, 10, 60, 0),
('Goldenbrew', 50, 50, 0, 0, 25, 0),
('Ravenous Red', 100, 0, 0, 0, 60, 0),
('Glowing Green', 0, 100, 0, 0, 75, 0),
('Bewitched Blue', 0, 0, 100, 0, 40, 0),
('Dark Devil', 0, 0, 0, 100, 50, 0),
('Amethyst', 50, 0, 50, 0, 50, 0);

-- potions_ledger table
CREATE TABLE potions_ledger (
    id BIGSERIAL PRIMARY KEY NOT NULL,
    potion_id INT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    red_percent INT CHECK (red_percent BETWEEN 0 AND 100),
    green_percent INT CHECK (green_percent BETWEEN 0 AND 100),
    blue_percent INT CHECK (blue_percent BETWEEN 0 AND 100),
    dark_percent INT CHECK (dark_percent BETWEEN 0 AND 100),
    price INT NOT NULL CHECK (price > 0),
    potion_name TEXT NOT NULL
);

-- visits table
CREATE TABLE visits (
    visit_id BIGSERIAL PRIMARY KEY NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    customer_name TEXT NOT NULL,
    character_class TEXT NOT NULL,
    level INT NOT NULL CHECK (level > 0)
);