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
        # Get current ml values from the ml table
        current_green_ml = connection.execute(sqlalchemy.text("SELECT num_green_ml FROM ml")).scalar()
        current_red_ml = connection.execute(sqlalchemy.text("SELECT num_red_ml FROM ml")).scalar()
        current_blue_ml = connection.execute(sqlalchemy.text("SELECT num_blue_ml FROM ml")).scalar()
        current_dark_ml = connection.execute(sqlalchemy.text("SELECT num_dark_ml FROM ml")).scalar()

        print(f"Green ml: {current_green_ml}, Red ml: {current_red_ml}, Blue ml: {current_blue_ml}, Dark ml: {current_dark_ml}")

        # Looping through each potion that is delivered
        for potion in potions_delivered:
            red_percent, green_percent, blue_percent, dark_percent = potion.potion_type
            quantity = potion.quantity

            # Calculate total ml needed for each potion type
            total_red_ml_needed = red_percent * quantity
            total_green_ml_needed = green_percent * quantity
            total_blue_ml_needed = blue_percent * quantity
            total_dark_ml_needed = dark_percent * quantity

            print(f"Delivering potion: {potion.potion_type}, Quantity: {quantity}")
            print(f"ML needed - Red: {total_red_ml_needed}, Green: {total_green_ml_needed}, Blue: {total_blue_ml_needed}, Dark: {total_dark_ml_needed}")

            # Check if enough ml is available
            if (current_red_ml >= total_red_ml_needed and
                current_green_ml >= total_green_ml_needed and
                current_blue_ml >= total_blue_ml_needed and
                current_dark_ml >= total_dark_ml_needed):

                # Update potion inventory
                connection.execute(
                    sqlalchemy.text("""
                        UPDATE custom_potions
                        SET inventory = inventory + :quantity
                        WHERE red_percent = :red_percent
                        AND green_percent = :green_percent
                        AND blue_percent = :blue_percent
                        AND dark_percent = :dark_percent
                    """),
                    {
                        "quantity": quantity,
                        "red_percent": red_percent,
                        "green_percent": green_percent,
                        "blue_percent": blue_percent,
                        "dark_percent": dark_percent
                    }
                )

                # Subtract the used ml from the ml table
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

                print(f"Updated inventory and ml levels for potion: {potion.potion_type}")

            else:
                print(f"Not enough ml available for potion: {potion.potion_type}. Skipping delivery.")

        print(f"Potions delivered: {potions_delivered}, Order ID: {order_id}")
    return "OK"


@router.post("/plan")
def get_bottle_plan():
    bottle_plan = []

    with db.engine.begin() as connection:
        # Get current ml values from the ml table
        current_red_ml = connection.execute(sqlalchemy.text("SELECT num_red_ml FROM ml")).scalar()
        current_green_ml = connection.execute(sqlalchemy.text("SELECT num_green_ml FROM ml")).scalar()
        current_blue_ml = connection.execute(sqlalchemy.text("SELECT num_blue_ml FROM ml")).scalar()
        current_dark_ml = connection.execute(sqlalchemy.text("SELECT num_dark_ml FROM ml")).scalar()

        # Get potions from custom_potions table
        potions = connection.execute(sqlalchemy.text("""
            SELECT red_percent, green_percent, blue_percent, dark_percent, inventory 
            FROM custom_potions
        """)).fetchall()

        # Iterate over each potion to check if it can be added to the bottle plan
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

            # Calculate max_quantity based on the minimum available ratio for each component
            if ml_requirements:
                max_quantity = min(ml // percent for ml, percent in ml_requirements)
            else:
                max_quantity = 0

            # Limit the quantity to 10 - current inventory to avoid exceeding the inventory threshold
            max_quantity = min(max_quantity, 10 - inventory)

            if max_quantity > 0:
                # Append the potion's ratio and quantity to the bottle plan
                bottle_plan.append({
                    "potion_type": [red_percent, green_percent, blue_percent, dark_percent],
                    "quantity": max_quantity
                })

                # Subtract the ml used for the added potions from each current ml value
                current_red_ml -= red_percent * max_quantity
                current_green_ml -= green_percent * max_quantity
                current_blue_ml -= blue_percent * max_quantity
                current_dark_ml -= dark_percent * max_quantity

        # Return the final bottle plan
        print(f"Bottle plan: {bottle_plan}")
        return bottle_plan

if __name__ == "__main__":
    print(get_bottle_plan())


