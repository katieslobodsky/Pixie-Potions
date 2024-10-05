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
        current_gold = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory")).scalar()

        for barrel in barrels_delivered:
            total_barrel_cost = barrel.price * barrel.quantity
            
            print(f"Processing barrel {barrel.sku} with price {barrel.price} and quantity {barrel.quantity}")
            print(f"Total cost for this barrel: {total_barrel_cost}, Available gold: {current_gold}")
            
            if current_gold >= total_barrel_cost:
                current_gold -= total_barrel_cost 
                
                if barrel.potion_type == [1, 0, 0, 0]:  
                    connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_red_ml = num_red_ml + :ml"),
                                       {"ml": barrel.quantity * barrel.ml_per_barrel})
                elif barrel.potion_type == [0, 1, 0, 0]:  
                    connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_green_ml = num_green_ml + :ml"),
                                       {"ml": barrel.quantity * barrel.ml_per_barrel})
                elif barrel.potion_type == [0, 0, 1, 0]: 
                    connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_blue_ml = num_blue_ml + :ml"),
                                       {"ml": barrel.quantity * barrel.ml_per_barrel})
                
                connection.execute(sqlalchemy.text("UPDATE global_inventory SET gold = :gold"), {"gold": current_gold})

                print(f"Purchased {barrel.quantity} of {barrel.sku}. Remaining gold: {current_gold}")
            else:
                print(f"Not enough gold to purchase {barrel.sku}. Needed: {total_barrel_cost}, Available: {current_gold}")

    print(f"Barrels delivered: {barrels_delivered}, order_id: {order_id}")
    return "OK"


# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):

    purchase_plan = []

    with db.engine.begin() as connection:
        current_red_potions = connection.execute(sqlalchemy.text("SELECT num_red_potions FROM global_inventory")).scalar()
        current_green_potions = connection.execute(sqlalchemy.text("SELECT num_green_potions FROM global_inventory")).scalar()
        current_blue_potions = connection.execute(sqlalchemy.text("SELECT num_blue_potions FROM global_inventory")).scalar()

        for barrel in wholesale_catalog:
            if barrel.potion_type == [1, 0, 0, 0]:
                if current_red_potions < 10:
                    purchase_plan.append({
                        "sku": barrel.sku,
                        "quantity": barrel.quantity,
                    })
            if barrel.potion_type == [0, 1, 0, 0]:
                if current_green_potions < 10:
                    purchase_plan.append({
                        "sku": barrel.sku,
                        "quantity": barrel.quantity,
                    })
            if barrel.potion_type == [0, 0, 1, 0]:
                if current_blue_potions < 10:
                    purchase_plan.append({
                        "sku": barrel.sku,
                        "quantity": barrel.quantity,
                    })

    print(wholesale_catalog)

    return purchase_plan



