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
    """ """
    #subtract 100ml from num_green_ml for each potion delivered 
    #add quantity of green potions to num_green_potions

    with db.engine.begin() as connection:
        for potion in potions_delivered:
            sql_add_green = "UPDATE global_inventory SET num_green_potions = num_green_potions + :quantity"
            connection.execute(sqlalchemy.text(sql_add_green), {"quantity": potions_delivered[0].quantity, "potion_type": potion.potion_type}).scalar()

            sql_subtract_ml = "UPDATE global_inventory SET num_green_ml = num_green_ml - :potions_delivered_ml"
            connection.execute(sqlalchemy.text(sql_subtract_ml), {"potions_delivered_ml": potions_delivered[0].quantity * 100}).scalar()

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

    with db.engine.begin() as connection:
        current_green_ml = connection.execute(sqlalchemy.text("SELECT num_green_ml FROM global_inventory")).scalar()

    if current_green_ml >= 100 :
        return [
            {
                "potion_type": [0, 100, 0, 0],
                "quantity": 1,
            }
        ]
    
    return [
        {
            "potion-type": [],
        }
    ]

if __name__ == "__main__":
    print(get_bottle_plan())
