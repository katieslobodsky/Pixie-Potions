import sqlalchemy
from src import database as db

from fastapi import APIRouter

router = APIRouter()

'''
@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """

    with db.engine.begin() as connection:
        num_red_potions = connection.execute(sqlalchemy.text("SELECT num_red_potions FROM potions")).scalar()
        num_green_potions = connection.execute(sqlalchemy.text("SELECT num_green_potions FROM potions")).scalar()
        num_blue_potions = connection.execute(sqlalchemy.text("SELECT num_blue_potions FROM potions")).scalar()

    if num_red_potions > 0:
        return [
            {
                "sku": "RED_POTION_0",
                "name": "red potion",
                "quantity": num_red_potions,
                "price": 50,  
                "potion_type": [100, 0, 0, 0],  
            }
        ]

    if num_green_potions > 0:
        return [
            {
                "sku": "GREEN_POTION_0",
                "name": "green potion",
                "quantity": num_green_potions,
                "price": 75,  
                "potion_type": [0, 100, 0, 0],  
            }
        ]
    
    if num_blue_potions > 0:
        return [
            {
                "sku": "BLUE_POTION_0",
                "name": "blue potion",
                "quantity": num_blue_potions,
                "price": 100,  
                "potion_type": [0, 0, 100, 0],  
            }
        ]
    
    return []
'''

@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Retrieve the catalog of all custom potions, including their quantities and prices.
    """

    catalog = []
    with db.engine.begin() as connection:
        # Query all potions from the custom_potions table
        custom_potions = connection.execute(sqlalchemy.text("""
            SELECT potion_id, red_percent, green_percent, blue_percent, dark_percent, inventory, price
            FROM custom_potions
            WHERE inventory > 0
        """)).fetchall()

    # Loop through each potion and add it to the catalog list
    for potion in custom_potions:
        potion_id = potion.potion_id
        red_percent = potion.red_percent
        green_percent = potion.green_percent
        blue_percent = potion.blue_percent
        dark_percent = potion.dark_percent
        inventory = potion.inventory
        price = potion.price

        # Create an entry for the catalog
        catalog.append({
            "sku": f"POTION_{potion_id}",
            "name": f"custom potion {potion_id}",
            "quantity": inventory,
            "price": price,
            "potion_type": [red_percent, green_percent, blue_percent, dark_percent]
        })

    return catalog
