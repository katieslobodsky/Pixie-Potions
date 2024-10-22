import sqlalchemy
from src import database as db

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
from enum import Enum
from fastapi import HTTPException

carts = {}
cart_counter = 0

router = APIRouter(
    prefix="/carts",
    tags=["cart"],
    dependencies=[Depends(auth.get_api_key)],
)

class search_sort_options(str, Enum):
    customer_name = "customer_name"
    item_sku = "item_sku"
    line_item_total = "line_item_total"
    timestamp = "timestamp"

class search_sort_order(str, Enum):
    asc = "asc"
    desc = "desc"   


@router.get("/search/", tags=["search"])
def search_orders(
    customer_name: str = "",
    potion_sku: str = "",
    search_page: str = "",
    sort_col: search_sort_options = search_sort_options.timestamp,
    sort_order: search_sort_order = search_sort_order.desc,
):
    """
    Search for cart line items by customer name and/or potion sku.

    Customer name and potion sku filter to orders that contain the 
    string (case insensitive). If the filters aren't provided, no
    filtering occurs on the respective search term.

    Search page is a cursor for pagination. The response to this
    search endpoint will return previous or next if there is a
    previous or next page of results available. The token passed
    in that search response can be passed in the next search request
    as search page to get that page of results.

    Sort col is which column to sort by and sort order is the direction
    of the search. They default to searching by timestamp of the order
    in descending order.

    The response itself contains a previous and next page token (if
    such pages exist) and the results as an array of line items. Each
    line item contains the line item id (must be unique), item sku, 
    customer name, line item total (in gold), and timestamp of the order.
    Your results must be paginated, the max results you can return at any
    time is 5 total line items.
    """

    return {
        "previous": "",
        "next": "",
        "results": [
            {
                "line_item_id": 1,
                "item_sku": "1 oblivion potion",
                "customer_name": "Scaramouche",
                "line_item_total": 50,
                "timestamp": "2021-01-01T00:00:00Z",
            }
        ],
    }


class Customer(BaseModel):
    customer_name: str
    character_class: str
    level: int


@router.post("/visits/{visit_id}")
def post_visits(visit_id: int, customers: list[Customer]):
    """
    Which customers visited the shop today?
    """
    print(customers)

    return "OK"

@router.post("/")
def create_cart(new_cart: Customer):

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("""
            INSERT INTO carts (customer_name, character_class, level, checked_out)
            VALUES (:customer_name, :character_class, :level, false)
            RETURNING cart_id
        """), {
            "customer_name": new_cart.customer_name,
            "character_class": new_cart.character_class,
            "level": new_cart.level
        }).fetchone()
        
        cart_id = result.cart_id

    return {"cart_id": cart_id, "message": f"Cart created for {new_cart.customer_name}"}


class CartItem(BaseModel):
    quantity: int


@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):

    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text("SELECT 1 FROM carts WHERE cart_id = :cart_id"), {"cart_id": cart_id}).fetchone()

        connection.execute(sqlalchemy.text("""
            INSERT INTO cart_items (cart_id, item_sku, quantity)
            VALUES (:cart_id, :item_sku, :quantity)
        """), {
            "cart_id": cart_id,
            "item_sku": item_sku,
            "quantity": cart_item.quantity
        })

    return {"message": f"Added {cart_item.quantity} of {item_sku} to cart {cart_id}"}


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    total_cost = 0

    with db.engine.begin() as connection:

        current_gold = connection.execute(sqlalchemy.text("SELECT gold FROM gold_transactions ORDER BY id DESC LIMIT 1")).scalar()

        cart_items = connection.execute(sqlalchemy.text("SELECT item_sku, quantity FROM cart_items WHERE cart_id = :cart_id"), {"cart_id": cart_id}).fetchall()

        for item in cart_items:
            potion_sku = item.item_sku
            potion_quantity = item.quantity
            
            potion_id = int(potion_sku.replace("POTION_", ""))

            potion = connection.execute(sqlalchemy.text("SELECT potion_id, inventory, price FROM custom_potions WHERE potion_id = :potion_id"), {"potion_id": potion_id}).fetchone()

            potion_inventory = potion.inventory
            potion_cost = potion.price

            if potion_inventory < potion_quantity:
                return {
                    "error": f"not enough stock for potion {potion_sku}. requested: {potion_quantity}, available: {potion_inventory}"
                }

            # Updating potion inventory
            new_inventory = potion_inventory - potion_quantity
            print(f"new inventory: {new_inventory}")
            connection.execute(sqlalchemy.text("UPDATE custom_potions SET inventory = :new_inventory WHERE potion_id = :potion_id"), {
                "new_inventory": new_inventory,
                "potion_id": potion_id
            })

            item_total = potion_quantity * potion_cost
            total_cost += item_total

            # Updating the cart item with item_price and item_total
            connection.execute(sqlalchemy.text("UPDATE cart_items SET item_price = :item_price, item_total = :item_total WHERE cart_id = :cart_id AND item_sku = :item_sku"), {
                "item_price": potion_cost,
                "item_total": item_total,
                "cart_id": cart_id,
                "item_sku": potion_sku
            })

        # Updating the gold balance
        new_gold_amount = current_gold + total_cost
        connection.execute(
            sqlalchemy.text(
                "INSERT INTO gold_transactions (gold) VALUES (:gold)"
            ),
            {"gold": new_gold_amount},
        )

        connection.execute(sqlalchemy.text("UPDATE carts SET checked_out = TRUE WHERE cart_id = :cart_id"), {"cart_id": cart_id})

    return {
        "message": f"Checkout successful for cart {cart_id}",
        "total_cost": total_cost,
        "new_gold_balance": new_gold_amount
    }

