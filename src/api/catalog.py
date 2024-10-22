import sqlalchemy
from src import database as db

from fastapi import APIRouter

router = APIRouter()

@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Retrieve the catalog of all custom potions, including their quantities and prices.
    """

    catalog = []
    with db.engine.begin() as connection:
        custom_potions = connection.execute(sqlalchemy.text("""
            SELECT potion_id, potion_name, red_percent, green_percent, blue_percent, dark_percent, inventory, price
            FROM custom_potions
            WHERE inventory > 0
        """)).fetchall()

    for potion in custom_potions:
        potion_id = potion.potion_id
        potion_name = potion.potion_name
        red_percent = potion.red_percent
        green_percent = potion.green_percent
        blue_percent = potion.blue_percent
        dark_percent = potion.dark_percent
        inventory = potion.inventory
        price = potion.price

        catalog.append({
            "sku": f"POTION_{potion_id}",
            "name": potion_name,
            "quantity": inventory,
            "price": price,
            "potion_type": [red_percent, green_percent, blue_percent, dark_percent]
        })

    return catalog
