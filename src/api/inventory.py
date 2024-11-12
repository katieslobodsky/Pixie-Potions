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
        total_potions = connection.execute(sqlalchemy.text("SELECT COALESCE(SUM(quantity), 0) AS total_potions FROM potions_ledger")).scalar()

        total_ml = connection.execute(sqlalchemy.text("""
            SELECT COALESCE(SUM(num_red_ml), 0) +
                   COALESCE(SUM(num_green_ml), 0) + 
                   COALESCE(SUM(num_blue_ml), 0) +
                   COALESCE(SUM(num_dark_ml), 0) AS total_ml
            FROM ml
        """)).scalar()

        gold_balance = connection.execute(sqlalchemy.text("SELECT COALESCE(SUM(gold), 0) AS total_gold FROM gold_transactions")).scalar()

    return {
        "number_of_potions": total_potions,
        "ml_in_barrels": total_ml,
        "gold": gold_balance
    }


@router.post("/plan")
def get_capacity_plan():
    """
    Calculate the capacity for potions and ml based on the current inventory levels.
    """
    with db.engine.begin() as connection:
        total_potions = connection.execute(sqlalchemy.text("SELECT COALESCE(SUM(quantity), 0) AS total_potions FROM potions_ledger")).scalar()

        total_ml_needed = connection.execute(sqlalchemy.text("""
            SELECT COALESCE(SUM(
                (potions.red_percent + potions.green_percent + potions.blue_percent + potions.dark_percent) 
                * potions_ledger.quantity / 100.0
            ), 0)
            FROM potions
            JOIN potions_ledger ON potions.potion_id = potions_ledger.potion_id
        """)).scalar()

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
        return {"error": "Potion and ml capacity must be greater than zero."}

    with db.engine.begin() as connection:
        current_gold = connection.execute(sqlalchemy.text("SELECT COALESCE(SUM(gold), 0) FROM gold_transactions")).scalar()
        total_cost = (capacity_purchase.potion_capacity + capacity_purchase.ml_capacity) * 1000
        if current_gold < total_cost:
            return {"error": "Not enough gold to purchase capacity."}

        connection.execute(sqlalchemy.text("""
            INSERT INTO gold_transactions (gold, message) 
            VALUES (:gold_change, :message)
        """), {
            "gold_change": -total_cost,
            "message": f"Subtracted {total_cost} gold for purchasing capacity: {capacity_purchase.potion_capacity} potion capacity and {capacity_purchase.ml_capacity} ml capacity"
        })

        # updating capacity table
        connection.execute(sqlalchemy.text("""
            INSERT INTO capacity (potion_capacity, ml_capacity)
            SELECT 
                COALESCE(MAX(potion_capacity), 0) + :potion_capacity,
                COALESCE(MAX(ml_capacity), 0) + :ml_capacity
            FROM capacity
        """), {
            "potion_capacity": capacity_purchase.potion_capacity,
            "ml_capacity": capacity_purchase.ml_capacity
        })

    return {
        "status": "success",
        "message": "Capacity purchase delivered successfully.",
        "remaining_gold": current_gold - total_cost,
        "potion_capacity": capacity_purchase.potion_capacity,
        "ml_capacity": capacity_purchase.ml_capacity
    }


