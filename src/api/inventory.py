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
            SELECT num_green_potions + num_red_potions + num_blue_potions AS total_potions,
                   num_green_ml + num_red_ml + num_blue_ml AS total_ml,
                   gold
            FROM global_inventory
        """)).fetchone()

        return {
            "number_of_potions": result.total_potions,
            "ml_in_barrels": result.total_ml,
            "gold": result.gold
        }

# Gets called once a day
@router.post("/plan")
def get_capacity_plan():
    """ 
    Start with 1 capacity for 50 potions and 1 capacity for 10000 ml of potion. Each additional 
    capacity unit costs 1000 gold.
    """

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT num_green_potions, num_red_potions, num_blue_potions,
                   num_green_ml, num_red_ml, num_blue_ml
            FROM global_inventory
        """)).fetchone()

        total_potions = result.num_green_potions + result.num_red_potions + result.num_blue_potions
        total_ml = result.num_green_ml + result.num_red_ml + result.num_blue_ml

        potion_capacity = total_potions // 50
        ml_capacity = total_ml // 10000

    return {
        "potion_capacity": potion_capacity,
        "ml_capacity": ml_capacity
    }

class CapacityPurchase(BaseModel):
    potion_capacity: int
    ml_capacity: int

# Gets called once a day
@router.post("/deliver/{order_id}")
def deliver_capacity_plan(capacity_purchase : CapacityPurchase, order_id: int):
    """ 
    Start with 1 capacity for 50 potions and 1 capacity for 10000 ml of potion. Each additional 
    capacity unit costs 1000 gold.
    """

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory")).fetchone()
        current_gold = result.gold
        total_cost = (capacity_purchase.potion_capacity + capacity_purchase.ml_capacity) * 1000

        if current_gold < total_cost:
            return {"Not enough gold to purchase capacity."}

        connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET gold = gold - {total_cost}"))

    return "OK"