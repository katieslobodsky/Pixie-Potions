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
        # Selecting the sum of quantities for each potion type
        available_potions = connection.execute(sqlalchemy.text("""
            SELECT potion_id, potion_name, red_percent, green_percent, blue_percent, dark_percent, SUM(quantity) AS total_quantity, price
            FROM potions
            WHERE quantity > 0
            GROUP BY potion_id, potion_name, red_percent, green_percent, blue_percent, dark_percent, price
        """)).fetchall()

    for potion in available_potions:
        potion_id = potion.potion_id
        potion_name = potion.potion_name
        red_percent = potion.red_percent
        green_percent = potion.green_percent
        blue_percent = potion.blue_percent
        dark_percent = potion.dark_percent
        total_quantity = potion.total_quantity
        price = potion.price

        catalog.append({
            "sku": f"POTION_{potion_id}",
            "name": potion_name,
            "quantity": total_quantity,
            "price": price,
            "potion_type": [red_percent, green_percent, blue_percent, dark_percent]
        })

    return catalog