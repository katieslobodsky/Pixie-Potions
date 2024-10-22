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

    # Selecting most recent value of gold
    with db.engine.begin() as connection:
        current_gold = connection.execute(sqlalchemy.text("SELECT gold FROM gold_transactions ORDER BY id DESC LIMIT 1 FOR UPDATE")).scalar()

        print(f"Current gold before barrel purchase: {current_gold}")

        for barrel in barrels_delivered:
            total_barrel_cost = barrel.price * barrel.quantity
            print(f"total barrel cost: {total_barrel_cost}")

            if current_gold >= total_barrel_cost:
                current_gold -= total_barrel_cost

                # Updating the inventory for the corresponding potion type
                if barrel.potion_type == [1, 0, 0, 0]:  
                    connection.execute(sqlalchemy.text("UPDATE ml SET num_red_ml = num_red_ml + :ml"),
                    {"ml": barrel.quantity * barrel.ml_per_barrel},
                    )
                elif barrel.potion_type == [0, 1, 0, 0]:  
                    connection.execute(sqlalchemy.text("UPDATE ml SET num_green_ml = num_green_ml + :ml"),
                    {"ml": barrel.quantity * barrel.ml_per_barrel},
                    )
                elif barrel.potion_type == [0, 0, 1, 0]: 
                    connection.execute(sqlalchemy.text("UPDATE ml SET num_blue_ml = num_blue_ml + :ml"),
                    {"ml": barrel.quantity * barrel.ml_per_barrel},
                    )

                elif barrel.potion_type == [0, 0, 0, 1]:  
                    connection.execute(sqlalchemy.text("UPDATE ml SET num_dark_ml = num_dark_ml + :ml"),
                    {"ml": barrel.quantity * barrel.ml_per_barrel},
                    )

                # Inserting a new row with updated gold into gold_transactions
                connection.execute(sqlalchemy.text("INSERT INTO gold_transactions (gold) VALUES (:gold)"),
                    {"gold": current_gold},
                )      

                print(
                    f"Purchased {barrel.quantity} of {barrel.sku}. Remaining gold: {current_gold}"
                )
            else:
                print(
                    f"Not enough gold for {barrel.sku}. Needed: {total_barrel_cost}, available: {current_gold}"
                )

    print(f"Barrels delivered: {barrels_delivered}, order_id: {order_id}")
    return "OK"


@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    purchase_plan = []

    with db.engine.begin() as connection:
        # Getting current ml levels and latest gold amount
        current_red_ml = connection.execute(sqlalchemy.text("SELECT num_red_ml FROM ml")).scalar()
        current_green_ml = connection.execute(sqlalchemy.text("SELECT num_green_ml FROM ml")).scalar()
        current_blue_ml = connection.execute(sqlalchemy.text("SELECT num_blue_ml FROM ml")).scalar()
        current_dark_ml = connection.execute(sqlalchemy.text("SELECT num_dark_ml FROM ml")).scalar()
        current_gold = connection.execute(sqlalchemy.text("SELECT gold FROM gold_transactions ORDER BY id DESC LIMIT 1")).scalar()

        print(f"Current ml levels: Red={current_red_ml}, Green={current_green_ml}, Blue={current_blue_ml}, Dark={current_dark_ml}")
        print(f"Current gold: {current_gold}")

        # Looping through each barrel
        for barrel in wholesale_catalog:
            if barrel.potion_type == [1, 0, 0, 0]:  
                needs_more_ml = current_red_ml < 200
            elif barrel.potion_type == [0, 1, 0, 0]: 
                needs_more_ml = current_green_ml < 200
            elif barrel.potion_type == [0, 0, 1, 0]:  
                needs_more_ml = current_blue_ml < 200
            elif barrel.potion_type == [0, 0, 0, 1]:  
                needs_more_ml = current_dark_ml < 200
            else:
                needs_more_ml = False  

            # If more ml is needed for this potion type, proceed to purchase if we have enough gold
            if needs_more_ml:
                for _ in range(barrel.quantity):
                    if current_gold >= barrel.price:
                        purchase_plan.append({
                            "sku": barrel.sku,
                            "ml_per_barrel": barrel.ml_per_barrel,
                            "potion_type": barrel.potion_type,
                            "price": barrel.price,
                            "quantity": 1  
                        })

                        current_gold -= barrel.price

                        # Updating ml levels based on the purchased barrel
                        if barrel.potion_type == [1, 0, 0, 0]:  
                            current_red_ml += barrel.ml_per_barrel
                        elif barrel.potion_type == [0, 1, 0, 0]:
                            current_green_ml += barrel.ml_per_barrel
                        elif barrel.potion_type == [0, 0, 1, 0]: 
                            current_blue_ml += barrel.ml_per_barrel
                        elif barrel.potion_type == [0, 0, 0, 1]:  
                            current_dark_ml += barrel.ml_per_barrel

                        print(f"Added one {barrel.sku} to the plan. Remaining gold: {current_gold}")
                    else:
                        print(f"Not enough gold to purchase more {barrel.sku}. Required: {barrel.price}, Available: {current_gold}")
                        break  

    print(f"Wholesale purchase plan: {purchase_plan}")
    return purchase_plan






