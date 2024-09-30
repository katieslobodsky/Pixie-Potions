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
    # Updating gold & ml
    with sqlalchemy.Engine.begin() as connection:
        current_gold = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory")).scalar()

    if(current_gold > barrels_delivered[0].price) :
        with sqlalchemy.Engine.begin() as connection:
            connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET gold = gold-{barrels_delivered[0]}"))
        with sqlalchemy.Engine.begin() as connection:
            connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET num_green_ml = num_green_ml-{barrels_delivered[0].quantity*500}"))

    print(f"barrels delievered: {barrels_delivered} order_id: {order_id}")

    return "OK"

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    print(wholesale_catalog)

    return [
        {
            "sku": "SMALL_RED_BARREL",
            "quantity": 1,
        }
    ]

