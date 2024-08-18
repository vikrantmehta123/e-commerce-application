from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.sql import text
from application import db

# Model for Products FTS
class ProductFTS:
    id = Column(Integer, primary_key=True)
    product_name = Column(String(100), nullable=False)
    description = Column(String(255))
    price = Column(Float, nullable=False)
    brand = Column(String(100), nullable=False)
    unit = Column(String, nullable=False)
    image_path = Column(String)  

def search_in_database(search_term:str):
    conn = db.engine.connect()
    
    # Search in Product FTS table
    product_results = conn.execute(text("SELECT * FROM product_fts WHERE product_fts MATCH :search_term"), {'search_term': search_term}).fetchall()
    
    conn.close()
    
    # Convert product results to JSON-serializable format
    products_json = [{"id": row[0], "product_name": row[1], "description": row[2], "brand": row[3], "price": row[4], "unit": row[5]} for row in product_results]

    return {
        'products': products_json
    }


def setup_fts():
    product_ai_trigger = """
    CREATE TRIGGER product_ai AFTER INSERT ON Product
    BEGIN
    INSERT INTO product_fts (id, product_name, description, brand, price, unit, image_path)
    VALUES (new.id, new.product_name, new.description, new.brand, new.price, new.unit, new.image_path);
    END;
    """

    product_ad_trigger = """
    CREATE TRIGGER product_ad AFTER DELETE ON Product
    BEGIN
    DELETE FROM product_fts WHERE id = old.id;
    END;
    """

    product_au_trigger = """
    CREATE TRIGGER product_au AFTER UPDATE ON Product
    BEGIN
    UPDATE product_fts SET
        product_name = new.product_name,
        description = new.description,
        brand = new.brand,
        price = new.price,
        unit = new.unit,
        image_path = new.image_path
    WHERE id = old.id;
    END;
    """

    # Then execute these using SQLAlchemy's conn.execute() method.

    with db.engine.connect() as conn:        
        conn.execute(text("DROP TABLE IF EXISTS product_fts;"))
        conn.execute(text("CREATE VIRTUAL TABLE IF NOT EXISTS product_fts USING fts5(id UNINDEXED, product_name, description, brand, price, unit, image_path);"))

        conn.execute(text("DROP TRIGGER IF EXISTS product_ai;"))
        conn.execute(text("DROP TRIGGER IF EXISTS product_ad;"))
        conn.execute(text("DROP TRIGGER IF EXISTS product_au;"))
        
        conn.execute(text(product_ai_trigger))
        conn.execute(text(product_ad_trigger))
        conn.execute(text(product_au_trigger))

        conn.commit()