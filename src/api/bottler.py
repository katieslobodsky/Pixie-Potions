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
    with db.engine.begin() as connection:
        for potion in potions_delivered:
            sql = "UPDATE inventory SET quantity = quantity + potion.quantity WHERE potion_type = potion.potion_type"
            connection.execute(sqlalchemy.text(sql), {"quantity": potion.quantity, "potion_type": potion.potion_type})

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
        sql_check_inventory = "SELECT quantity FROM inventory WHERE potion_type = '0,100,0,0'"
        result = connection.execute(sqlalchemy.text(sql_check_inventory))

        green_inventory = 0
        for row in result:
            green_inventory = row['quantity']

        if green_inventory < 10:
            sql_purchase_barrel = "UPDATE inventory SET quantity = quantity + 1 WHERE potion_type = '0,100,0,0'"
            connection.execute(sqlalchemy.text(sql_purchase_barrel))
            green_inventory += 1
    

    return [
            {
                "potion_type": [0, 100, 0, 0],
                "quantity": green_inventory,
            }
        ]

if __name__ == "__main__":
    print(get_bottle_plan())
