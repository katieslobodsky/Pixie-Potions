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
        # Get total potions and ml from the potions and ml tables
        result = connection.execute(sqlalchemy.text("""
            SELECT (SELECT COALESCE(SUM(num_green_potions + num_red_potions + num_blue_potions), 0) FROM potions) AS total_potions,
                   (SELECT COALESCE(SUM(num_green_ml + num_red_ml + num_blue_ml), 0) FROM ml) AS total_ml
        """)).fetchone()


        # Get the most recent gold amount from the gold_transactions table
        gold_result = connection.execute(sqlalchemy.text("""
            SELECT gold FROM gold_transactions ORDER BY id DESC LIMIT 1
        """)).scalar()

        print(f"total potions: {result.total_potions}")
        print(f"ml in barrels: {result.total_ml}")
        print(f"gold: {gold_result}")

        return {
            "number_of_potions": result.total_potions,
            "ml_in_barrels": result.total_ml,
            "gold": gold_result
        }


# Gets called once a day
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
    }


class CapacityPurchase(BaseModel):
    potion_capacity: int
    ml_capacity: int

# Gets called once a day
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
