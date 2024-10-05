import sqlalchemy
from src import database as db

from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth

router = APIRouter(
    prefix="/bottler",
    tags=["bottler"],
    dependencies=[Depends(auth.get_api_key)],
)

class PotionInventory(BaseModel):
    potion_type: list[int]
    quantity: int

@router.post("/deliver/{order_id}")
def post_deliver_bottles(potions_delivered: list[PotionInventory], order_id: int):

    with db.engine.begin() as connection:
        current_green_ml = connection.execute(sqlalchemy.text("SELECT num_green_ml FROM global_inventory")).scalar()
        current_red_ml = connection.execute(sqlalchemy.text("SELECT num_red_ml FROM global_inventory")).scalar()
        current_blue_ml = connection.execute(sqlalchemy.text("SELECT num_blue_ml FROM global_inventory")).scalar()
        
        for potion in potions_delivered:
            ml_needed = potion.quantity * 100                
            if potion.potion_type == [100, 0, 0, 0]:  #Red potion
                if current_red_ml >= ml_needed:
                    connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET num_red_potions = num_red_potions + {potion.quantity}"))
                    connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET num_red_ml = num_red_ml - {ml_needed}"))
            
            elif potion.potion_type == [0, 100, 0, 0]:  #Green potion
                if current_green_ml >= ml_needed:
                    connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET num_green_potions = num_green_potions + {potion.quantity}"))
                    connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET num_green_ml = num_green_ml - {ml_needed}"))
                
            elif potion.potion_type == [0, 0, 100, 0]:  #Blue potion
                if current_blue_ml >= ml_needed:
                    connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET num_blue_potions = num_blue_potions + {potion.quantity}"))
                    connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET num_blue_ml = num_blue_ml - {ml_needed}"))

    print(f"potions delivered: {potions_delivered} order_id: {order_id}")

    return "OK"


@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """

    # Each bottle has a quantity of what proportion of red, blue, and
    # green potion to add.
    # Expressed in integers from 1 to 100 that must sum up to 100.

    # Initial logic: bottle all barrels into red potions.

    bottle_plan = []

    with db.engine.begin() as connection:
        current_green_ml = connection.execute(sqlalchemy.text("SELECT num_green_ml FROM global_inventory")).scalar()
        current_red_ml = connection.execute(sqlalchemy.text("SELECT num_red_ml FROM global_inventory")).scalar()
        current_blue_ml = connection.execute(sqlalchemy.text("SELECT num_blue_ml FROM global_inventory")).scalar()

        quantity_green = current_green_ml/100
        quantity_red = current_red_ml/100
        quantity_blue = current_blue_ml/100

        if current_red_ml >= 100:
            bottle_plan.append({
                "potion_type": [100, 0, 0, 0],
                "quantity": quantity_red
            })

        if current_green_ml >= 100:
            bottle_plan.append({
                "potion_type": [0, 100, 0, 0],
                "quantity": quantity_green
            })

        if current_blue_ml >= 100:
            bottle_plan.append({
                "potion_type": [0, 0, 100, 0],
                "quantity": quantity_blue
            })

        return bottle_plan


if __name__ == "__main__":
    print(get_bottle_plan())

