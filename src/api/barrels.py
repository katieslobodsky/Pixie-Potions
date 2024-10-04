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

    total_price = barrels_delivered[0].price

    with db.engine.begin() as connection:
        current_gold = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory")).scalar()

        if current_gold < total_price:
            return {"Not enough gold."}
        
        connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET gold = gold - {total_price}"))

        if barrels_delivered[0].potion_type == [0, 1, 0, 0]:
            connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_green_ml = num_green_ml + :ml"), 
                                   {"ml": barrels_delivered[0].quantity * barrels_delivered[0].ml_per_barrel})
        elif barrels_delivered[0].potion_type == [1, 0, 0, 0]:
            connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_red_ml = num_red_ml + :ml"), 
                                   {"ml": barrels_delivered[0].quantity * barrels_delivered[0].ml_per_barrel})
        elif barrels_delivered[0].potion_type == [0, 0, 1, 0]:
            connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_blue_ml = num_blue_ml + :ml"), 
                                   {"ml": barrels_delivered[0].quantity * barrels_delivered[0].ml_per_barrel})
    print(f"Barrels delivered: {barrels_delivered}, order_id: {order_id}")
    return "OK"


# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):

    purchase_plan = []

    with db.engine.begin() as connection:
        current_green_potions = connection.execute(sqlalchemy.text("SELECT num_green_potions FROM global_inventory")).scalar()
        current_red_potions = connection.execute(sqlalchemy.text("SELECT num_red_potions FROM global_inventory")).scalar()
        current_blue_potions = connection.execute(sqlalchemy.text("SELECT num_blue_potions FROM global_inventory")).scalar()

        if current_green_potions < 10:
            purchase_plan.append({
                "sku": "SMALL_GREEN_BARREL",
                "quantity": 1,
            })

        if current_red_potions < 10:
            purchase_plan.append({
                "sku": "SMALL_RED_BARREL",
                "quantity": 1,
            })

        if current_blue_potions < 10:
            purchase_plan.append({
                "sku": "SMALL_BLUE_BARREL",
                "quantity": 1,
            })

    print(wholesale_catalog)

    return purchase_plan



