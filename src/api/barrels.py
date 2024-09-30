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
    """ """
    with db.engine.begin() as connection:
        current_gold = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory")).scalar()

    if current_gold > barrels_delivered[0].price:
        with db.engine.begin() as connection:
            connection.execute(sqlalchemy.text("""
                UPDATE global_inventory
                SET gold = gold - gold.price
            """), {"price": barrels_delivered[0].price})

        with db.engine.begin() as connection:
            connection.execute(sqlalchemy.text("""
                UPDATE global_inventory
                SET num_green_ml = num_green_ml + :ml
            """), {"ml": barrels_delivered[0].quantity * barrels_delivered[0].ml_per_barrel})

    print(f"barrels delivered: {barrels_delivered} order_id: {order_id}")

    return "OK"

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    print(wholesale_catalog)

    return [
        {
            "sku": "SMALL_GREEN_BARREL",
            "quantity": 1,
        }
    ]

