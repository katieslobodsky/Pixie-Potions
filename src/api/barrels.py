import sqlalchemy
from src import database as db

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth

router = APIRouter(
    prefix="/barrels",
    tags=["barrels"],
    dependencies=[Depends(auth.get_api_key)],
)

class Barrel(BaseModel):
    sku: str

    ml_per_barrel: int
    potion_type: list[int]
    price: int

    quantity: int


@router.post("/deliver/{order_id}")
def post_deliver_barrels(barrels_delivered: list[Barrel], order_id: int):

    with db.engine.begin() as connection:
        current_gold = connection.execute(sqlalchemy.text("SELECT SUM(gold) FROM gold_transactions")).scalar() or 0
        print(f"current gold before barrel purchase: {current_gold}")

        for barrel in barrels_delivered:
            total_barrel_cost = barrel.price * barrel.quantity
            print(f"total barrel cost: {total_barrel_cost}")

            if current_gold >= total_barrel_cost:
                current_gold -= total_barrel_cost
                ml_message = f"delivered {barrel.quantity} barrels of {barrel.sku} adding {barrel.quantity * barrel.ml_per_barrel} ml"

                # Inserting a new row with ml change for the corresponding potion type
                ml_change = barrel.quantity * barrel.ml_per_barrel
                if barrel.potion_type == [1, 0, 0, 0]:
                    connection.execute(sqlalchemy.text("INSERT INTO ml (num_red_ml, message) VALUES (:change, :message)"),
                        {"change": ml_change, "message": ml_message},
                    )
                elif barrel.potion_type == [0, 1, 0, 0]:  
                    connection.execute(sqlalchemy.text("INSERT INTO ml (num_green_ml, message) VALUES (:change, :message)"),
                        {"change": ml_change, "message": ml_message},
                    )
                elif barrel.potion_type == [0, 0, 1, 0]: 
                    connection.execute(sqlalchemy.text("INSERT INTO ml (num_blue_ml, message) VALUES (:change, :message)"),
                        {"change": ml_change, "message": ml_message},
                    )
                elif barrel.potion_type == [0, 0, 0, 1]:  
                    connection.execute(sqlalchemy.text("INSERT INTO ml (num_dark_ml, message) VALUES (:change, :message)"),
                        {"change": ml_change, "message": ml_message},
                    )

                gold_message = f"Subtracted {total_barrel_cost} gold for purchasing {barrel.quantity} of {barrel.sku}."

                # Inserting a new row with gold change into gold_transactions
                connection.execute(sqlalchemy.text("INSERT INTO gold_transactions (gold, message) VALUES (:gold, :message)"),
                    {"gold": -total_barrel_cost, "message": gold_message},
                )
                print(
                    f"purchased {barrel.quantity} of {barrel.sku}. remaining gold: {current_gold}"
                )
            else:
                print(
                    f"not enough gold for {barrel.sku}. needed: {total_barrel_cost}, available: {current_gold}"
                )
    print(f"barrels delivered: {barrels_delivered}, order_id: {order_id}")
    return "OK"


@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    purchase_plan = []

    with db.engine.begin() as connection:
        # Selecting ml levels and gold amount as a sum of all rows
        current_red_ml = connection.execute(sqlalchemy.text("SELECT SUM(num_red_ml) FROM ml")).scalar() or 0
        current_green_ml = connection.execute(sqlalchemy.text("SELECT SUM(num_green_ml) FROM ml")).scalar() or 0
        current_blue_ml = connection.execute(sqlalchemy.text("SELECT SUM(num_blue_ml) FROM ml")).scalar() or 0
        current_dark_ml = connection.execute(sqlalchemy.text("SELECT SUM(num_dark_ml) FROM ml")).scalar() or 0
        current_gold = connection.execute(sqlalchemy.text("SELECT SUM(gold) FROM gold_transactions")).scalar() or 0

        print(f"current ml levels: red={current_red_ml}, green={current_green_ml}, blue={current_blue_ml}, dark={current_dark_ml}")
        print(f"current gold: {current_gold}")

        priority_order = [
            (current_red_ml, [1, 0, 0, 0]), 
            (current_green_ml, [0, 1, 0, 0]), 
            (current_blue_ml, [0, 0, 1, 0]),  
            (current_dark_ml, [0, 0, 0, 1]), 
        ]
        
        priority_order.sort(key=lambda x: x[0])  

        for ml_level, potion_type in priority_order:
            for barrel in wholesale_catalog:
                if barrel.potion_type == potion_type:
                    needs_more_ml = ml_level < 200
                    purchased_quantity = 0  

                    if needs_more_ml:
                        for _ in range(barrel.quantity):
                            if current_gold >= barrel.price:
                                purchased_quantity += 1
                                current_gold -= barrel.price

                                if potion_type == [1, 0, 0, 0]:  
                                    current_red_ml += barrel.ml_per_barrel
                                elif potion_type == [0, 1, 0, 0]:  
                                    current_green_ml += barrel.ml_per_barrel
                                elif potion_type == [0, 0, 1, 0]:  
                                    current_blue_ml += barrel.ml_per_barrel
                                elif potion_type == [0, 0, 0, 1]:  
                                    current_dark_ml += barrel.ml_per_barrel

                                print(f"purchased one {barrel.sku}, remaining gold: {current_gold}")
                            else:
                                print(f"not enough gold to purchase {barrel.sku}. Required: {barrel.price}, available: {current_gold}")
                                break  

                    if purchased_quantity > 0:
                        purchase_plan.append({
                            "sku": barrel.sku,
                            "ml_per_barrel": barrel.ml_per_barrel,
                            "potion_type": barrel.potion_type,
                            "price": barrel.price,
                            "quantity": purchased_quantity  
                        })

    print(f"Wholesale purchase plan: {purchase_plan}")
    return purchase_plan








