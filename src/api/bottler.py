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
        current_green_ml = connection.execute(sqlalchemy.text("SELECT num_green_ml FROM ml")).scalar()
        current_red_ml = connection.execute(sqlalchemy.text("SELECT num_red_ml FROM ml")).scalar()
        current_blue_ml = connection.execute(sqlalchemy.text("SELECT num_blue_ml FROM ml")).scalar()

        print(f"Green ml: {current_green_ml}, Red ml: {current_red_ml}, Blue ml: {current_blue_ml}")

        for potion in potions_delivered:
            ml_needed = int(potion.quantity * 100)
            print(f"Delivering potion: {potion.potion_type}, Quantity: {potion.quantity}, ml needed: {ml_needed}")
                
            if potion.potion_type == [100, 0, 0, 0]:  
                if current_red_ml >= ml_needed:
                    connection.execute(
                        sqlalchemy.text("UPDATE potions SET num_red_potions = num_red_potions + :quantity"),
                        {"quantity": potion.quantity}
                    )
                    connection.execute(
                        sqlalchemy.text("UPDATE ml SET num_red_ml = num_red_ml - :ml_needed"),
                        {"ml_needed": ml_needed}
                    )
                else:
                    print(f"Not enough red potion ml - current: {current_red_ml}, needed: {ml_needed}")
            
            elif potion.potion_type == [0, 100, 0, 0]:  
                if current_green_ml >= ml_needed:
                    connection.execute(
                        sqlalchemy.text("UPDATE potions SET num_green_potions = num_green_potions + :quantity"),
                        {"quantity": potion.quantity}
                    )
                    connection.execute(
                        sqlalchemy.text("UPDATE ml SET num_green_ml = num_green_ml - :ml_needed"),
                        {"ml_needed": ml_needed}
                    )
                else:
                    print(f"Not enough green potion ml - current: {current_green_ml}, needed: {ml_needed}")
                
            elif potion.potion_type == [0, 0, 100, 0]: 
                if current_blue_ml >= ml_needed:
                    connection.execute(
                        sqlalchemy.text("UPDATE potions SET num_blue_potions = num_blue_potions + :quantity"),
                        {"quantity": potion.quantity}
                    )
                    connection.execute(
                        sqlalchemy.text("UPDATE ml SET num_blue_ml = num_blue_ml - :ml_needed"),
                        {"ml_needed": ml_needed}
                    )
                else:
                    print(f"Not enough blue potion ml - current: {current_blue_ml}, needed: {ml_needed}")

            print(f"Potions delivered: {potions_delivered}, Order ID: {order_id}")
    return "OK"


@router.post("/plan")
def get_bottle_plan():
    bottle_plan = []

    with db.engine.begin() as connection:
        current_green_ml = connection.execute(sqlalchemy.text("SELECT num_green_ml FROM ml")).scalar()
        current_red_ml = connection.execute(sqlalchemy.text("SELECT num_red_ml FROM ml")).scalar()
        current_blue_ml = connection.execute(sqlalchemy.text("SELECT num_blue_ml FROM ml")).scalar()

        print(f"Current Red ML: {current_red_ml}, Green ML: {current_green_ml}, Blue ML: {current_blue_ml}")

        quantity_green = int(current_green_ml / 100)
        quantity_red = int(current_red_ml / 100)
        quantity_blue = int(current_blue_ml / 100)

        print(f"Quantity red: {quantity_red}, Quantity green: {quantity_green}, Quantity blue: {quantity_blue}")

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

        print(f"Bottle plan: {bottle_plan}")
        return bottle_plan


if __name__ == "__main__":
    print(get_bottle_plan())

