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

    # Select most recent value of gold
    with db.engine.begin() as connection:
        current_gold = connection.execute(sqlalchemy.text("SELECT gold FROM gold_transactions ORDER BY id DESC LIMIT 1")).scalar()

        print(f"Current gold before barrel purchase: {current_gold}")

        for barrel in barrels_delivered:
            total_barrel_cost = barrel.price * barrel.quantity
            print(f"total barrel cost: {total_barrel_cost}")

            # Check if the purchase would make the gold negative
            if current_gold >= total_barrel_cost:
                current_gold -= total_barrel_cost

                # Update the inventory for the corresponding potion type
                if barrel.potion_type == [1, 0, 0, 0]:  # Red potion
                    connection.execute(sqlalchemy.text("UPDATE ml SET num_red_ml = num_red_ml + :ml"),
                    {"ml": barrel.quantity * barrel.ml_per_barrel},
                    )
                elif barrel.potion_type == [0, 1, 0, 0]:  # Green potion
                    connection.execute(sqlalchemy.text("UPDATE ml SET num_green_ml = num_green_ml + :ml"),
                    {"ml": barrel.quantity * barrel.ml_per_barrel},
                    )
                elif barrel.potion_type == [0, 0, 1, 0]:  # Blue potion
                    connection.execute(sqlalchemy.text("UPDATE ml SET num_blue_ml = num_blue_ml + :ml"),
                    {"ml": barrel.quantity * barrel.ml_per_barrel},
                    )

                elif barrel.potion_type == [0, 0, 0, 1]:  # Dark potion
                    connection.execute(sqlalchemy.text("UPDATE ml SET num_dark_ml = num_dark_ml + :ml"),
                    {"ml": barrel.quantity * barrel.ml_per_barrel},
                    )

                # Insert a new row into gold_transactions
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
        # Get current ml levels and latest gold amount
        current_red_ml = connection.execute(sqlalchemy.text("SELECT num_red_ml FROM ml")).scalar()
        current_green_ml = connection.execute(sqlalchemy.text("SELECT num_green_ml FROM ml")).scalar()
        current_blue_ml = connection.execute(sqlalchemy.text("SELECT num_blue_ml FROM ml")).scalar()
        current_dark_ml = connection.execute(sqlalchemy.text("SELECT num_dark_ml FROM ml")).scalar()
        current_gold = connection.execute(sqlalchemy.text("SELECT gold FROM gold_transactions ORDER BY id DESC LIMIT 1")).scalar()

        # Print current ml levels and gold
        print(f"Current ml levels: Red={current_red_ml}, Green={current_green_ml}, Blue={current_blue_ml}, Dark={current_dark_ml}")
        print(f"Current gold: {current_gold}")

        # Loop through each barrel
        for barrel in wholesale_catalog:
            # Determine if we need more ml for this potion type
            if barrel.potion_type == [1, 0, 0, 0]:  # Red potion
                needs_more_ml = current_red_ml < 200
            elif barrel.potion_type == [0, 1, 0, 0]:  # Green potion
                needs_more_ml = current_green_ml < 200
            elif barrel.potion_type == [0, 0, 1, 0]:  # Blue potion
                needs_more_ml = current_blue_ml < 200
            elif barrel.potion_type == [0, 0, 0, 1]:  # Dark potion
                needs_more_ml = current_dark_ml < 200
            else:
                needs_more_ml = False  # Invalid potion type or not needed

            # If more ml is needed for this potion type, proceed to purchase
            if needs_more_ml:
                # Add barrels one by one to the purchase plan based on individual price
                for _ in range(barrel.quantity):
                    # Check if there is enough gold to buy one barrel
                    if current_gold >= barrel.price:
                        # Add this barrel to the purchase plan
                        purchase_plan.append({
                            "sku": barrel.sku,
                            "ml_per_barrel": barrel.ml_per_barrel,
                            "potion_type": barrel.potion_type,
                            "price": barrel.price,
                            "quantity": 1  # Adding one barrel at a time
                        })

                        # Deduct the cost of this barrel from the available gold
                        current_gold -= barrel.price

                        # Update ml levels based on the purchased barrel
                        if barrel.potion_type == [1, 0, 0, 0]:  # Red potion
                            current_red_ml += barrel.ml_per_barrel
                        elif barrel.potion_type == [0, 1, 0, 0]:  # Green potion
                            current_green_ml += barrel.ml_per_barrel
                        elif barrel.potion_type == [0, 0, 1, 0]:  # Blue potion
                            current_blue_ml += barrel.ml_per_barrel
                        elif barrel.potion_type == [0, 0, 0, 1]:  # Dark potion
                            current_dark_ml += barrel.ml_per_barrel

                        print(f"Added one {barrel.sku} to the plan. Remaining gold: {current_gold}")
                    else:
                        # Not enough gold to buy any more barrels of this type
                        print(f"Not enough gold to purchase more {barrel.sku}. Required: {barrel.price}, Available: {current_gold}")
                        break  # Stop trying to buy more of this barrel type

    # Output the purchase plan
    print(f"Wholesale purchase plan: {purchase_plan}")
    return purchase_plan






