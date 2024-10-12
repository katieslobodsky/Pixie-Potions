import sqlalchemy
from src import database as db

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
from enum import Enum

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
    """ """
    global carts
    global cart_counter

    cart_id = cart_counter
    cart_counter += 1

    carts[cart_id] = {
        "customer": new_cart.customer_name,
        "items": []  
    }

    return {"cart_id": cart_id, "message": f"Cart created for {new_cart.customer_name}"}


class CartItem(BaseModel):
    quantity: int


@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):

    global carts  

    if cart_id not in carts:
        return {"error": "Cart not found"}  

    carts[cart_id]["items"].append({
        "potion_sku": item_sku,
        "quantity": cart_item.quantity
    })

    print(f"item sku: {item_sku}")
    print(f"quantity: {cart_item.quantity}")

    return {"message": f"Added {cart_item.quantity} of {item_sku} to cart {cart_id}"}


class CartCheckout(BaseModel):
    payment: str


@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    global carts 

    if cart_id not in carts:
        return {"error": "Cart not found"} 

    total_cost = 0
    with db.engine.begin() as connection:
        inventory = connection.execute(sqlalchemy.text("""
            SELECT num_green_potions, num_red_potions, num_blue_potions, gold 
            FROM global_inventory
            FOR UPDATE
        """)).fetchone()

        current_green_potions = inventory.num_green_potions
        current_red_potions = inventory.num_red_potions
        current_blue_potions = inventory.num_blue_potions
        current_gold = inventory.gold

        for item in carts[cart_id]["items"]:
            potion_sku = item["potion_sku"]
            potion_quantity = item["quantity"]

            potion_cost = 0  

            if potion_sku == "RED_POTION_0":
                potion_cost = 50
                if current_red_potions < potion_quantity:
                    return {"error": f"Not enough red potions in stock"}
                current_red_potions -= potion_quantity 

            elif potion_sku == "GREEN_POTION_0":
                potion_cost = 75
                if current_green_potions < potion_quantity:
                    return {"error": f"Not enough green potions in stock"}
                current_green_potions -= potion_quantity  

            elif potion_sku == "BLUE_POTION_0":
                potion_cost = 100
                if current_blue_potions < potion_quantity:
                    return {"error": f"Not enough blue potions in stock"}
                current_blue_potions -= potion_quantity  

            total_cost += potion_quantity * potion_cost

        new_gold_amount = current_gold + total_cost

        connection.execute(sqlalchemy.text(f"""
            UPDATE global_inventory 
            SET gold = {new_gold_amount}, 
                num_green_potions = {current_green_potions}, 
                num_red_potions = {current_red_potions}, 
                num_blue_potions = {current_blue_potions}
        """))

    carts.pop(cart_id)

    return {
        "message": f"Checkout successful for cart {cart_id}",
        "total_cost": total_cost,
        "new_gold_balance": new_gold_amount
    }

