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
        current_dark_ml = connection.execute(sqlalchemy.text("SELECT num_dark_ml FROM ml")).scalar()

        print(f"green ml: {current_green_ml}, red ml: {current_red_ml}, blue ml: {current_blue_ml}, dark ml: {current_dark_ml}")

        for potion in potions_delivered:
            red_percent, green_percent, blue_percent, dark_percent = potion.potion_type
            quantity = potion.quantity

            total_red_ml_needed = red_percent * quantity
            total_green_ml_needed = green_percent * quantity
            total_blue_ml_needed = blue_percent * quantity
            total_dark_ml_needed = dark_percent * quantity

            print(f"delivering potion: {potion.potion_type}, Quantity: {quantity}")
            print(f"ML needed - Red: {total_red_ml_needed}, Green: {total_green_ml_needed}, Blue: {total_blue_ml_needed}, Dark: {total_dark_ml_needed}")

            if (current_red_ml >= total_red_ml_needed and
                current_green_ml >= total_green_ml_needed and
                current_blue_ml >= total_blue_ml_needed and
                current_dark_ml >= total_dark_ml_needed):

                # Updating potion inventory (adding new quantity of ml)
                connection.execute(
                    sqlalchemy.text("UPDATE custom_potions SET inventory = inventory + :quantity WHERE red_percent = :red_percent AND green_percent = :green_percent AND blue_percent = :blue_percent AND dark_percent = :dark_percent"),
                    {
                        "quantity": quantity,
                        "red_percent": red_percent,
                        "green_percent": green_percent,
                        "blue_percent": blue_percent,
                        "dark_percent": dark_percent
                    }
                )

                # Updating ml table (subtracing current - ml used)
                connection.execute(
                    sqlalchemy.text("UPDATE ml SET num_red_ml = num_red_ml - :ml_used"),
                    {"ml_used": total_red_ml_needed}
                )
                connection.execute(
                    sqlalchemy.text("UPDATE ml SET num_green_ml = num_green_ml - :ml_used"),
                    {"ml_used": total_green_ml_needed}
                )
                connection.execute(
                    sqlalchemy.text("UPDATE ml SET num_blue_ml = num_blue_ml - :ml_used"),
                    {"ml_used": total_blue_ml_needed}
                )
                connection.execute(
                    sqlalchemy.text("UPDATE ml SET num_dark_ml = num_dark_ml - :ml_used"),
                    {"ml_used": total_dark_ml_needed}
                )

                print(f"updated inventory and ml levels for potion: {potion.potion_type}")

            else:
                print(f"not enough ml available for potion: {potion.potion_type}")

        print(f"potions delivered: {potions_delivered}, order ID: {order_id}")
    return "OK"


@router.post("/plan")
def get_bottle_plan():
    bottle_plan = []

    with db.engine.begin() as connection:
        current_red_ml = connection.execute(sqlalchemy.text("SELECT num_red_ml FROM ml")).scalar()
        current_green_ml = connection.execute(sqlalchemy.text("SELECT num_green_ml FROM ml")).scalar()
        current_blue_ml = connection.execute(sqlalchemy.text("SELECT num_blue_ml FROM ml")).scalar()
        current_dark_ml = connection.execute(sqlalchemy.text("SELECT num_dark_ml FROM ml")).scalar()

        potions = connection.execute(sqlalchemy.text("""
            SELECT red_percent, green_percent, blue_percent, dark_percent, inventory 
            FROM custom_potions
        """)).fetchall()

        for potion in potions:
            red_percent, green_percent, blue_percent, dark_percent, inventory = potion

            if inventory >= 10:
                continue

            ml_requirements = [
                (current_red_ml, red_percent),
                (current_green_ml, green_percent),
                (current_blue_ml, blue_percent),
                (current_dark_ml, dark_percent)
            ]
            
            ml_requirements = [(ml, percent) for ml, percent in ml_requirements if percent > 0]

            if ml_requirements:
                max_quantity = min(ml // percent for ml, percent in ml_requirements)
            else:
                max_quantity = 0

            if max_quantity > 0:
                bottle_plan.append({
                    "potion_type": [red_percent, green_percent, blue_percent, dark_percent],
                    "quantity": max_quantity
                })

                current_red_ml -= red_percent * max_quantity
                current_green_ml -= green_percent * max_quantity
                current_blue_ml -= blue_percent * max_quantity
                current_dark_ml -= dark_percent * max_quantity

        print(f"Bottle plan: {bottle_plan}")
        return bottle_plan

if __name__ == "__main__":
    print(get_bottle_plan())


