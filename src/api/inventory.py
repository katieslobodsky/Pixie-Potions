import sqlalchemy
from src import database as db

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import math

router = APIRouter(
    prefix="/inventory",
    tags=["inventory"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.get("/audit")
def get_inventory():
    with db.engine.begin() as connection:
        # Get total potions and ml from the custom_potions and ml tables
        result = connection.execute(sqlalchemy.text("""
            SELECT (SELECT COALESCE(SUM(inventory), 0) FROM custom_potions) AS total_potions,
                   (SELECT COALESCE(SUM(ml_amount), 0) FROM ml) AS total_ml
        """)).fetchone()

        # Get the most recent gold amount from the gold_transactions table
        gold_result = connection.execute(sqlalchemy.text("""
            SELECT gold FROM gold_transactions ORDER BY id DESC LIMIT 1
        """)).scalar()

        return {
            "number_of_potions": result.total_potions,
            "ml_in_barrels": result.total_ml,
            "gold": gold_result
        }

# old get capacity plan
'''# Gets called once a day
@router.post("/plan")
def get_capacity_plan():
    """ 
    Calculate the capacity for potions and ml based on the current inventory levels.
    """
    with db.engine.begin() as connection:
        # Get the total number of potions and ml from the potions and ml tables
        result = connection.execute(sqlalchemy.text("""
            SELECT (SELECT COALESCE(SUM(num_green_potions), 0) FROM potions) AS num_green_potions,
                   (SELECT COALESCE(SUM(num_red_potions), 0) FROM potions) AS num_red_potions,
                   (SELECT COALESCE(SUM(num_blue_potions), 0) FROM potions) AS num_blue_potions,
                   (SELECT COALESCE(SUM(num_green_ml), 0) FROM ml) AS num_green_ml,
                   (SELECT COALESCE(SUM(num_red_ml), 0) FROM ml) AS num_red_ml,
                   (SELECT COALESCE(SUM(num_blue_ml), 0) FROM ml) AS num_blue_ml
        """)).fetchone()

        print(f"num red potions: {result.num_red_potions}")
        print(f"num green potions: {result.num_green_potions}")
        print(f"num blue potions: {result.num_blue_potions}")
        print(f"num red ml: {result.num_red_ml}")
        print(f"num green ml: {result.num_green_ml}")
        print(f"num blue ml: {result.num_blue_ml}")

        total_potions = result.num_green_potions + result.num_red_potions + result.num_blue_potions
        total_ml = result.num_green_ml + result.num_red_ml + result.num_blue_ml

        potion_capacity = max(1, total_potions // 50)
        ml_capacity = max(1, total_ml // 10000)

    return {
        "potion_capacity": potion_capacity,
        "ml_capacity": ml_capacity
    }'''

# new get capacity plan
@router.post("/plan")
def get_capacity_plan():
    """
    Calculate the capacity for potions and ml based on the current inventory levels.
    """
    with db.engine.begin() as connection:
        # Get the total number of potions and their corresponding ml ratios
        result = connection.execute(sqlalchemy.text("""
            SELECT COALESCE(SUM(inventory), 0) AS total_potions,
                   COALESCE(SUM((red_percent + green_percent + blue_percent + dark_percent) * inventory / 100), 0) AS total_ml_needed
            FROM custom_potions
        """)).fetchone()

        total_potions = result.total_potions
        total_ml_needed = result.total_ml_needed

        # Calculate the potion capacity, allowing for one capacity per 50 potions
        potion_capacity = max(1, math.ceil(total_potions / 50))
        
        # Calculate the ml capacity, allowing for one capacity per 10,000 ml
        ml_capacity = max(1, math.ceil(total_ml_needed / 10000))

    return {
        "potion_capacity": potion_capacity,
        "ml_capacity": ml_capacity
    }

class CapacityPurchase(BaseModel):
    potion_capacity: int
    ml_capacity: int

# old deliver capacity plan
'''# Gets called once a day
@router.post("/deliver/{order_id}")
def deliver_capacity_plan(capacity_purchase: CapacityPurchase, order_id: int):
    """ 
    Purchase additional capacity for potions and ml if there is enough gold.
    """
    with db.engine.begin() as connection:
        # Get the most recent gold amount from the gold_transactions table
        current_gold = connection.execute(sqlalchemy.text("""
            SELECT gold FROM gold_transactions ORDER BY id DESC LIMIT 1
        """)).scalar()

        total_cost = (capacity_purchase.potion_capacity + capacity_purchase.ml_capacity) * 1000
        print(f"total cost: {total_cost}")

        if current_gold < total_cost:
            return {"error": "Not enough gold to purchase capacity."}

        # Update the gold by inserting a new transaction reflecting the gold spent
        new_gold_balance = current_gold - total_cost
        connection.execute(sqlalchemy.text("""
            INSERT INTO gold_transactions (gold) VALUES (:new_gold)
        """), {"new_gold": new_gold_balance})

    return "OK"
'''

# new deliver capacity plan
@router.post("/deliver/{order_id}")
def deliver_capacity_plan(capacity_purchase: CapacityPurchase, order_id: int):
    """ 
    Purchase additional capacity for potions and ml if there is enough gold.
    """
    if capacity_purchase.potion_capacity <= 0 or capacity_purchase.ml_capacity <= 0:
        return {"error": "Potion and ml capacity must be greater than zero."}

    with db.engine.begin() as connection:
        # Get the most recent gold amount from the gold_transactions table
        current_gold = connection.execute(sqlalchemy.text("""
            SELECT gold FROM gold_transactions ORDER BY id DESC LIMIT 1
        """)).scalar()

        # Calculate the total cost for the capacity purchase
        total_cost = (capacity_purchase.potion_capacity + capacity_purchase.ml_capacity) * 1000
        print(f"Total cost for capacity purchase: {total_cost}")

        if current_gold is None:
            return {"error": "Current gold amount is not available."}

        if current_gold < total_cost:
            return {"error": "Not enough gold to purchase capacity."}

        # Deduct the gold and insert a new transaction reflecting the gold spent
        new_gold_balance = current_gold - total_cost
        connection.execute(sqlalchemy.text("""
            INSERT INTO gold_transactions (gold) VALUES (:new_gold)
        """), {"new_gold": new_gold_balance})

        # Log the new balances and capacities
        print(f"New gold balance: {new_gold_balance}")
        print(f"Purchased potion capacity: {capacity_purchase.potion_capacity}")
        print(f"Purchased ml capacity: {capacity_purchase.ml_capacity}")

    return {
        "status": "success",
        "message": "Capacity purchase delivered successfully.",
        "new_gold_balance": new_gold_balance,
        "potion_capacity": capacity_purchase.potion_capacity,
        "ml_capacity": capacity_purchase.ml_capacity
    }

