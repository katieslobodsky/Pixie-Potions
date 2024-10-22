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
        result = connection.execute(sqlalchemy.text("""
            SELECT (SELECT COALESCE(SUM(inventory), 0) FROM custom_potions) AS total_potions
        """)).fetchone()

        ml_result = connection.execute(sqlalchemy.text("""
            SELECT COALESCE(SUM(num_red_ml), 0) + 
                   COALESCE(SUM(num_green_ml), 0) + 
                   COALESCE(SUM(num_blue_ml), 0) + 
                   COALESCE(SUM(num_dark_ml), 0) AS total_ml
            FROM ml
        """)).scalar()

        gold_result = connection.execute(sqlalchemy.text("SELECT gold FROM gold_transactions ORDER BY id DESC LIMIT 1")).scalar()

        return {
            "number_of_potions": result.total_potions,
            "ml_in_barrels": ml_result,
            "gold": gold_result
        }

@router.post("/plan")
def get_capacity_plan():
    """
    Calculate the capacity for potions and ml based on the current inventory levels.
    """
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT COALESCE(SUM(inventory), 0) AS total_potions,
                   COALESCE(SUM((red_percent + green_percent + blue_percent + dark_percent) * inventory / 100), 0) AS total_ml_needed
            FROM custom_potions
        """)).fetchone()

        total_potions = result.total_potions
        total_ml_needed = result.total_ml_needed

        potion_capacity = max(1, math.ceil(total_potions / 50))
        ml_capacity = max(1, math.ceil(total_ml_needed / 10000))

    return {
        "potion_capacity": potion_capacity,
        "ml_capacity": ml_capacity
    }

class CapacityPurchase(BaseModel):
    potion_capacity: int
    ml_capacity: int


@router.post("/deliver/{order_id}")
def deliver_capacity_plan(capacity_purchase: CapacityPurchase, order_id: int):
    """ 
    Purchase additional capacity for potions and ml if there is enough gold.
    """
    if capacity_purchase.potion_capacity <= 0 or capacity_purchase.ml_capacity <= 0:
        return {"error": "potion and ml capacity must be greater than zero."}

    with db.engine.begin() as connection:
        current_gold = connection.execute(sqlalchemy.text("SELECT gold FROM gold_transactions ORDER BY id DESC LIMIT 1")).scalar()

        total_cost = (capacity_purchase.potion_capacity + capacity_purchase.ml_capacity) * 1000
        print(f"total cost for capacity purchase: {total_cost}")

        if current_gold is None:
            return {"error": "current gold amount is not available."}

        if current_gold < total_cost:
            return {"error": "not enough gold to purchase capacity."}

        new_gold_balance = current_gold - total_cost
        connection.execute(sqlalchemy.text("""
            INSERT INTO gold_transactions (gold) VALUES (:new_gold)
        """), {"new_gold": new_gold_balance})

        # Log the new balances and capacities
        print(f"new gold balance: {new_gold_balance}")
        print(f"purchased potion capacity: {capacity_purchase.potion_capacity}")
        print(f"purchased ml capacity: {capacity_purchase.ml_capacity}")

    return {
        "status": "success",
        "message": "Capacity purchase delivered successfully.",
        "new_gold_balance": new_gold_balance,
        "potion_capacity": capacity_purchase.potion_capacity,
        "ml_capacity": capacity_purchase.ml_capacity
    }

