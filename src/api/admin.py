import sqlalchemy
from src import database as db

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
from src.api.carts import carts, cart_counter

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.post("/reset")
def reset():
    """
    Reset the game state. Gold goes to 100, all potions are removed from
    inventory, and all barrels are removed from inventory. Carts are all reset.
    """
    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text("""
            DELETE FROM gold_transactions
        """))

        # Insert a new gold transaction with value of 100
        connection.execute(sqlalchemy.text("""
            INSERT INTO gold_transactions (gold) VALUES (:gold)
        """), {"gold": 100})

        # Reset potions table
        connection.execute(sqlalchemy.text("""
            UPDATE potions 
            SET num_green_potions = 0, 
                num_red_potions = 0, 
                num_blue_potions = 0
        """))

        # Reset ml table
        connection.execute(sqlalchemy.text("""
            UPDATE ml 
            SET num_green_ml = 0, 
                num_red_ml = 0, 
                num_blue_ml = 0
        """))

        # Delete all carts
        connection.execute(sqlalchemy.text("""
            DELETE FROM carts
        """))

        # Delete all cart items
        connection.execute(sqlalchemy.text("""
            DELETE FROM cart_items
        """))

    return "OK"

