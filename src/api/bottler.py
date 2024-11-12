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
        # Selecting current ML levels
        current_green_ml = connection.execute(sqlalchemy.text("SELECT SUM(num_green_ml) FROM ml")).scalar() or 0
        current_red_ml = connection.execute(sqlalchemy.text("SELECT SUM(num_red_ml) FROM ml")).scalar() or 0
        current_blue_ml = connection.execute(sqlalchemy.text("SELECT SUM(num_blue_ml) FROM ml")).scalar() or 0
        current_dark_ml = connection.execute(sqlalchemy.text("SELECT SUM(num_dark_ml) FROM ml")).scalar() or 0

        print(f"current ML levels: green={current_green_ml}, red={current_red_ml}, blue={current_blue_ml}, dark={current_dark_ml}")

        for potion in potions_delivered:
            red_percent, green_percent, blue_percent, dark_percent = potion.potion_type
            quantity = potion.quantity

            total_red_ml_needed = red_percent * quantity
            total_green_ml_needed = green_percent * quantity
            total_blue_ml_needed = blue_percent * quantity
            total_dark_ml_needed = dark_percent * quantity

            print(f"delivering potion: {potion.potion_type}, quantity: {quantity}")
            print(f"ML needed - red: {total_red_ml_needed}, green: {total_green_ml_needed}, blue: {total_blue_ml_needed}, dark: {total_dark_ml_needed}")

            if (current_red_ml >= total_red_ml_needed and
                current_green_ml >= total_green_ml_needed and
                current_blue_ml >= total_blue_ml_needed and
                current_dark_ml >= total_dark_ml_needed):

                # Selecting price and potion_name for the potion type
                result = connection.execute(
                    sqlalchemy.text("""
                        SELECT potion_id, price, potion_name 
                        FROM potions
                        WHERE red_percent = :red_percent AND green_percent = :green_percent
                          AND blue_percent = :blue_percent AND dark_percent = :dark_percent
                        LIMIT 1
                    """),
                    {
                        "red_percent": red_percent,
                        "green_percent": green_percent,
                        "blue_percent": blue_percent,
                        "dark_percent": dark_percent
                    }
                ).fetchone()

                potion_id, price, potion_name = result.potion_id, result.price, result.potion_name
                message = f"added {quantity} potions of {potion_name} (SKU: POTION_{potion_id})"

                # Inserting change in quantity for potions delivered
                connection.execute(
                    sqlalchemy.text("""
                        INSERT INTO potions_ledger (potion_id, red_percent, green_percent, blue_percent, dark_percent, quantity, price, potion_name, message)
                        VALUES (:potion_id, :red_percent, :green_percent, :blue_percent, :dark_percent, :quantity_change, :price, :potion_name, :message)
                    """),
                    {
                        "potion_id": potion_id,
                        "red_percent": red_percent,
                        "green_percent": green_percent,
                        "blue_percent": blue_percent,
                        "dark_percent": dark_percent,
                        "quantity_change": quantity,
                        "price": price,
                        "potion_name": potion_name,
                        "message": message
                    }
                )
                ml_message = (
                    f"used {total_red_ml_needed} ml red, {total_green_ml_needed} ml green, "
                    f"{total_blue_ml_needed} ml blue, and {total_dark_ml_needed} ml dark for {quantity} {potion_name} potions"
                )
                # Inserting a row in the ml table with all ml changes for each potion delivered
                connection.execute(
                    sqlalchemy.text("""
                        INSERT INTO ml (num_red_ml, num_green_ml, num_blue_ml, num_dark_ml, message)
                        VALUES (:red_ml_used, :green_ml_used, :blue_ml_used, :dark_ml_used, :message)
                    """),
                    {
                        "red_ml_used": -total_red_ml_needed,
                        "green_ml_used": -total_green_ml_needed,
                        "blue_ml_used": -total_blue_ml_needed,
                        "dark_ml_used": -total_dark_ml_needed,
                        "message": ml_message
                    }
                )

                print(f"inserted change in quantity for potion and recorded ml usage for potion: {potion.potion_type}")

            else:
                print(f"not enough ml available for potion: {potion.potion_type}")

        print(f"potions delivered: {potions_delivered}, order ID: {order_id}")
    return "OK"


@router.post("/plan")
def get_bottle_plan():
    bottle_plan = []

    with db.engine.begin() as connection:
        # Selecting ml levels as a sum of all rows
        current_red_ml = connection.execute(sqlalchemy.text("SELECT SUM(num_red_ml) FROM ml")).scalar()
        current_green_ml = connection.execute(sqlalchemy.text("SELECT SUM(num_green_ml) FROM ml")).scalar()
        current_blue_ml = connection.execute(sqlalchemy.text("SELECT SUM(num_blue_ml) FROM ml")).scalar()
        current_dark_ml = connection.execute(sqlalchemy.text("SELECT SUM(num_dark_ml) FROM ml")).scalar()

        potions = connection.execute(sqlalchemy.text("SELECT red_percent, green_percent, blue_percent, dark_percent FROM potions")).fetchall()

        for potion in potions:
            red_percent, green_percent, blue_percent, dark_percent = potion
            # Selecting the current total quantity of this potion type from potions_ledger
            quantity = connection.execute(sqlalchemy.text("""
                SELECT COALESCE(SUM(quantity), 0) FROM potions_ledger
                WHERE red_percent = :red_percent AND green_percent = :green_percent
                  AND blue_percent = :blue_percent AND dark_percent = :dark_percent
            """), {
                "red_percent": red_percent,
                "green_percent": green_percent,
                "blue_percent": blue_percent,
                "dark_percent": dark_percent
            }).scalar()

            if quantity >= 10:
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


