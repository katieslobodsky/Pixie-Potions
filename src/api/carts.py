import sqlalchemy
from src import database as db

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
from enum import Enum
from fastapi import HTTPException

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
    with db.engine.begin() as connection:
        for customer in customers:
            connection.execute(sqlalchemy.text("""
                INSERT INTO visits (customer_name, character_class, level)
                VALUES (:customer_name, :character_class, :level)
            """), {
                "customer_name": customer.customer_name,
                "character_class": customer.character_class,
                "level": customer.level
            })
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

    return {"cart_id": cart_id}


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

    return {"message": f"added {cart_item.quantity} of {item_sku} to cart {cart_id}"}


class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    total_cost = 0
    total_potions_bought = 0  

    with db.engine.begin() as connection:
        cart_items = connection.execute(sqlalchemy.text("SELECT item_sku, quantity FROM cart_items WHERE cart_id = :cart_id"), {"cart_id": cart_id}).fetchall()

        for item in cart_items:
            potion_sku = item.item_sku
            potion_quantity = item.quantity
            potion_id = int(potion_sku.replace("POTION_", ""))
            
            # Selecting the total quantity available in potions_ledger for the specific potion
            potion_inventory = connection.execute(sqlalchemy.text("""
                SELECT SUM(quantity) 
                FROM potions_ledger 
                WHERE potion_id = :potion_id
            """), {"potion_id": potion_id}).scalar() or 0

            potion_details = connection.execute(sqlalchemy.text("""
                SELECT price, red_percent, green_percent, blue_percent, dark_percent, potion_name 
                FROM potions 
                WHERE potion_id = :potion_id
            """), {"potion_id": potion_id}).fetchone()

            if not potion_details:
                return {"error": f"Potion {potion_sku} not found"}

            potion_cost = potion_details.price
            red_percent = potion_details.red_percent
            green_percent = potion_details.green_percent
            blue_percent = potion_details.blue_percent
            dark_percent = potion_details.dark_percent
            potion_name = potion_details.potion_name

            if potion_inventory < potion_quantity:
                return {
                    "error": f"Not enough stock for potion {potion_sku}. Requested: {potion_quantity}, available: {potion_inventory}"
                }
            
            message = f"Sold {potion_quantity} potions of {potion_name} (SKU: {potion_sku})"

            # Inserting a new row in potions_ledger with all potion details
            quantity_change = -potion_quantity
            connection.execute(sqlalchemy.text("""
                INSERT INTO potions_ledger (potion_id, quantity, red_percent, green_percent, blue_percent, dark_percent, price, potion_name, message)
                VALUES (:potion_id, :quantity_change, :red_percent, :green_percent, :blue_percent, :dark_percent, :price, :potion_name, :message)
            """), {
                "potion_id": potion_id,
                "quantity_change": quantity_change,
                "red_percent": red_percent,
                "green_percent": green_percent,
                "blue_percent": blue_percent,
                "dark_percent": dark_percent,
                "price": potion_cost,
                "potion_name": potion_name,
                "message": message
            })

            item_total = potion_quantity * potion_cost
            total_cost += item_total
            total_potions_bought += potion_quantity

            # Updating the cart item with item price and item total
            connection.execute(sqlalchemy.text("""
                UPDATE cart_items 
                SET item_price = :item_price, item_total = :item_total 
                WHERE cart_id = :cart_id AND item_sku = :item_sku
            """), {
                "item_price": potion_cost,
                "item_total": item_total,
                "cart_id": cart_id,
                "item_sku": potion_sku
            })

        # Inserting a row for change in gold after selling a potion
        gold_change = total_cost
        gold_message = f"Added {gold_change} gold for selling {total_potions_bought} potions of {potion_name} (SKU: {potion_sku})"

        connection.execute(sqlalchemy.text("""
            INSERT INTO gold_transactions (gold, message) VALUES (:gold_change, :message)
        """), {
            "gold_change": gold_change,
            "message": gold_message
        })

        # Updating cart as checked out
        connection.execute(sqlalchemy.text("UPDATE carts SET checked_out = TRUE WHERE cart_id = :cart_id"), {"cart_id": cart_id})

    return {
        "total_potions_bought": total_potions_bought,
        "total_gold_paid": total_cost,
    }





