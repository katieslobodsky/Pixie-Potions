-- gold_transactions table
CREATE TABLE gold_transactions (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    gold INT NOT NULL CHECK (gold >= 0) 
);

-- initial gold value
INSERT INTO gold_transactions (gold) VALUES (100);

-- custom_potions table
CREATE TABLE custom_potions (
    potion_id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    potion_name TEXT NOT NULL,
    red_percent INT CHECK (red_percent BETWEEN 0 AND 100),
    green_percent INT CHECK (green_percent BETWEEN 0 AND 100),
    blue_percent INT CHECK (blue_percent BETWEEN 0 AND 100),
    dark_percent INT CHECK (dark_percent BETWEEN 0 AND 100),
    price INT NOT NULL CHECK (price > 0), 
    inventory INT NOT NULL DEFAULT 0 
);

-- initial potion values
INSERT INTO custom_potions (potion_name, red_percent, green_percent, blue_percent, dark_percent, price, inventory) VALUES
('Enchanted Emerald', 0, 50, 50, 0, 50, 0),
('Bubbly Boysenberry', 40, 0, 40, 20, 75, 0),
('Ocean Odyssey', 5, 10, 85, 0, 100, 0),
('Silver Sonic', 10, 0, 20, 70, 125, 0),
('Fiery Fizz', 90, 0, 0, 10, 150, 0),
('Nightfall Nymph', 5, 65, 5, 25, 175, 0),
('Goldenbrew', 50, 50, 0, 0, 200, 0),
('Ravenous Red', 100, 0, 0, 0, 50, 0),
('Glowing Green', 0, 100, 0, 0, 75, 0),
('Bewitched Blue', 0, 0, 100, 0, 100, 0),
('Dark Devil', 0, 0, 0, 100, 125, 0),
('Amethyst', 50, 0, 50, 0, 50, 0);

-- carts table
CREATE TABLE carts (
    cart_id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    checked_out BOOLEAN DEFAULT FALSE,
    customer_name TEXT NOT NULL,
    character_class TEXT NOT NULL,
    level INT NOT NULL CHECK (level > 0)
);

-- cart_items table
CREATE TABLE cart_items (
    item_id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    cart_id INT REFERENCES carts (cart_id) ON DELETE CASCADE,
    item_sku TEXT NOT NULL,
    quantity INT NOT NULL CHECK (quantity > 0), 
    item_price INT CHECK (item_price >= 0),
    item_total INT CHECK (item_total >= 0) 
);

-- ml table
CREATE TABLE ml (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    num_red_ml INT DEFAULT 0 NOT NULL CHECK (num_red_ml >= 0),
    num_green_ml INT DEFAULT 0 NOT NULL CHECK (num_green_ml >= 0), 
    num_blue_ml INT DEFAULT 0 NOT NULL CHECK (num_blue_ml >= 0), 
    num_dark_ml INT DEFAULT 0 NOT NULL CHECK (num_dark_ml >= 0) 
);

-- initial ml values
INSERT INTO ml (num_red_ml, num_green_ml, num_blue_ml, num_dark_ml) 
VALUES (0, 0, 0, 0);