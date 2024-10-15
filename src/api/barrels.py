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
        current_gold = connection.execute(
            sqlalchemy.text("SELECT gold FROM gold_transactions ORDER BY id DESC LIMIT 1")
        ).scalar()
        print(f"current gold before purchase: {current_gold}")

        for barrel in barrels_delivered:
            total_barrel_cost = barrel.price * barrel.quantity
            print(f"total barrel cost: {total_barrel_cost}")

            # Check if the purchase would make the gold negative
            if current_gold >= total_barrel_cost:
                current_gold -= total_barrel_cost

                # Update the inventory for the corresponding potion type
                if barrel.potion_type == [1, 0, 0, 0]:  # Red potion
                    connection.execute(
                        sqlalchemy.text(
                            "UPDATE ml SET num_red_ml = num_red_ml + :ml"
                        ),
                        {"ml": barrel.quantity * barrel.ml_per_barrel},
                    )
                elif barrel.potion_type == [0, 1, 0, 0]:  # Green potion
                    connection.execute(
                        sqlalchemy.text(
                            "UPDATE ml SET num_green_ml = num_green_ml + :ml"
                        ),
                        {"ml": barrel.quantity * barrel.ml_per_barrel},
                    )
                elif barrel.potion_type == [0, 0, 1, 0]:  # Blue potion
                    connection.execute(
                        sqlalchemy.text(
                            "UPDATE ml SET num_blue_ml = num_blue_ml + :ml"
                        ),
                        {"ml": barrel.quantity * barrel.ml_per_barrel},
                    )

                # Insert a new row into gold_transactions
                connection.execute(
                    sqlalchemy.text(
                        "INSERT INTO gold_transactions (gold) VALUES (:gold)"
                    ),
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
        # Fetch current inventory and gold information
        current_red_potions = connection.execute(
            sqlalchemy.text("SELECT num_red_potions FROM potions")
        ).scalar()
        current_green_potions = connection.execute(
            sqlalchemy.text("SELECT num_green_potions FROM potions")
        ).scalar()
        current_blue_potions = connection.execute(
            sqlalchemy.text("SELECT num_blue_potions FROM potions")
        ).scalar()
        current_gold_plan = connection.execute(
            sqlalchemy.text("SELECT gold FROM gold_transactions ORDER BY id DESC LIMIT 1")
        ).scalar()

        print(f"Current gold: {current_gold_plan}")

        for barrel in wholesale_catalog:
            total_cost = barrel.price * barrel.quantity
            print(f"Total cost for {barrel.sku}: {total_cost}")

            # Check if there's enough gold and potion inventory is below 10
            if current_gold_plan >= total_cost:
                if barrel.potion_type == [1, 0, 0, 0]:  # Red potion
                    if current_red_potions < 10:
                        purchase_plan.append({"sku": barrel.sku, "ml_per_barrel": barrel.ml_per_barrel, "potion_type": barrel.potion_type, "price": barrel.price, "quantity": barrel.quantity})
                        current_gold_plan -= total_cost
                        print(f"Added {barrel.sku} to plan, remaining gold: {current_gold_plan}")
                
                elif barrel.potion_type == [0, 1, 0, 0]:  # Green potion
                    if current_green_potions < 10:
                        purchase_plan.append({"sku": barrel.sku, "ml_per_barrel": barrel.ml_per_barrel, "potion_type": barrel.potion_type, "price": barrel.price, "quantity": barrel.quantity})
                        current_gold_plan -= total_cost
                        print(f"Added {barrel.sku} to plan, remaining gold: {current_gold_plan}")
                
                elif barrel.potion_type == [0, 0, 1, 0]:  # Blue potion
                    if current_blue_potions < 10:
                        purchase_plan.append({"sku": barrel.sku, "ml_per_barrel": barrel.ml_per_barrel, "potion_type": barrel.potion_type, "price": barrel.price, "quantity": barrel.quantity})
                        current_gold_plan -= total_cost
                        print(f"Added {barrel.sku} to plan, remaining gold: {current_gold_plan}")
            else:
                print(f"Not enough gold for {barrel.sku}, required: {total_cost}, available: {current_gold_plan}")

    print(f"Wholesale catalog checked: {wholesale_catalog}")
    return purchase_plan





