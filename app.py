from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
from datetime import datetime

app = Flask(__name__)
CORS(app)

def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="admin",          # ← Change if your password is different
        database="grocery_store"
    )

# ====================== PRODUCTS ======================
@app.route('/api/products', methods=['GET'])
def get_products():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM product_info ORDER BY product_id DESC")
    products = cursor.fetchall()
    db.close()
    return jsonify(products)

@app.route('/api/products', methods=['POST'])
def add_product():
    data = request.json
    db = get_db()
    cursor = db.cursor()
    sql = """INSERT INTO product_info 
             (product_name, quantity, price, min_stock) 
             VALUES (%s, %s, %s, %s)"""
    cursor.execute(sql, (data['product_name'], data['quantity'], 
                        data['price'], data['min_stock']))
    db.commit()
    db.close()
    return jsonify({"message": "Product added successfully"}), 201

@app.route('/api/products/<int:pid>', methods=['PUT'])
def update_product(pid):
    data = request.json
    db = get_db()
    cursor = db.cursor()
    sql = """UPDATE product_info 
             SET product_name=%s, quantity=%s, price=%s, min_stock=%s 
             WHERE product_id=%s"""
    cursor.execute(sql, (data['product_name'], data['quantity'], 
                        data['price'], data['min_stock'], pid))
    db.commit()
    db.close()
    return jsonify({"message": "Product updated"})

@app.route('/api/products/<int:pid>', methods=['DELETE'])
def delete_product(pid):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM product_info WHERE product_id = %s", (pid,))
    db.commit()
    db.close()
    return jsonify({"message": "Product deleted"})

# ====================== BILLING ======================
@app.route('/api/bills', methods=['POST'])
def create_bill():
    data = request.json
    items = data.get('items', [])
    total = data.get('total', 0)

    db = get_db()
    cursor = db.cursor()
    try:
        # Insert into bill_history
        cursor.execute("INSERT INTO bill_history (total) VALUES (%s)", (total,))
        db.commit()
        cursor.execute("SELECT LAST_INSERT_ID()")
        bill_id = cursor.fetchone()[0]

        # Insert into sales_history and update stock
        for item in items:
            cursor.execute("""
                INSERT INTO sales_history 
                (bill_id, product_name, quantity, price, amount) 
                VALUES (%s, %s, %s, %s, %s)
            """, (bill_id, item['product_name'], item['quantity'], 
                 item['price'], item['price'] * item['quantity']))

            # Reduce stock
            cursor.execute("""
                UPDATE product_info 
                SET quantity = quantity - %s 
                WHERE product_id = %s
            """, (item['quantity'], item['product_id']))

        db.commit()
        return jsonify({"message": "Bill created successfully", "bill_id": bill_id}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        db.close()

# ====================== SALES ======================
@app.route('/api/sales', methods=['GET'])
def get_sales():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT bill_id, total, DATE(created_at) as date 
        FROM bill_history 
        ORDER BY bill_id DESC
    """)
    sales = cursor.fetchall()
    db.close()
    return jsonify(sales)

# Low Stock
@app.route('/api/low-stock', methods=['GET'])
def low_stock():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT * FROM product_info 
        WHERE quantity < min_stock OR quantity = 0
    """)
    low = cursor.fetchall()
    db.close()
    return jsonify(low)

if __name__ == '__main__':
    app.run(debug=True, port=5000)