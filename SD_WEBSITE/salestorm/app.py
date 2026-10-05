from flask import Flask, request, jsonify, render_template
import os
import json
from inventory import reserve_item, get_products, get_reservations, remove_item
from payments import process_payment, get_orders
from storage import read_json

app = Flask(__name__)
CONFIG_FILE = 'config.json'

def get_config():
    return read_json(CONFIG_FILE, {"HOLD_MINUTES": 10, "MAX_PER_PRODUCT": 2, "POLL_SECONDS": 4})

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/cart')
def cart():
    return render_template('cart.html')

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
        
    # Accept any password so anyone can log in for the demo
    return jsonify({'status': 'success', 'username': username}), 200

@app.route('/api/products', methods=['GET'])
def api_products():
    customer_id = request.headers.get('X-Customer-Id', '')
    prods = get_products()
    res = get_reservations()
    
    # Calculate how many of each product the user has in cart
    user_res = [r for r in res.values() if r['customer_id'] == customer_id and r['status'] == 'RESERVED']
    cart_counts = {}
    for r in user_res:
        cart_counts[r['product_id']] = cart_counts.get(r['product_id'], 0) + r['qty']
        
    for p in prods:
        p['in_cart'] = cart_counts.get(p['id'], 0)
        
    return jsonify(prods)

@app.route('/api/cart', methods=['GET'])
def api_cart():
    customer_id = request.headers.get('X-Customer-Id', '')
    res = get_reservations()
    prods = {p['id']: p for p in get_products()}
    
    user_res = [r for r in res.values() if r['customer_id'] == customer_id and r['status'] == 'RESERVED']
    
    items = []
    total = 0
    for r in user_res:
        p = prods.get(r['product_id'])
        if p:
            items.append({
                'reservation_id': r['id'],
                'product_id': p['id'],
                'name': p['name'],
                'price': p['price'],
                'qty': r['qty'],
                'expires_at': r['expires_at'],
                'emoji': p['emoji'],
                'image': p.get('image', '')
            })
            total += p['price'] * r['qty']
            
    return jsonify({'items': items, 'total': total})

@app.route('/api/cart/items', methods=['POST'])
def add_to_cart():
    data = request.json
    customer_id = request.headers.get('X-Customer-Id')
    idem_key = request.headers.get('Idempotency-Key')
    config = get_config()
    
    result = reserve_item(
        customer_id, 
        data['productId'], 
        data.get('qty', 1), 
        config['HOLD_MINUTES'], 
        idem_key,
        config['MAX_PER_PRODUCT']
    )
    
    if 'error' in result:
        return jsonify(result), 409
    return jsonify(result), 201

@app.route('/api/cart/items/<product_id>', methods=['DELETE'])
def remove_from_cart(product_id):
    customer_id = request.headers.get('X-Customer-Id')
    result = remove_item(customer_id, product_id, 1)
    return jsonify(result), 200

@app.route('/api/checkout', methods=['POST'])
def checkout():
    data = request.json
    customer_id = request.headers.get('X-Customer-Id')
    idem_key = request.headers.get('Idempotency-Key')
    
    # Calculate amount from reservations
    res = get_reservations()
    prods = {p['id']: p for p in get_products()}
    user_res = [r for r in res.values() if r['customer_id'] == customer_id and r['status'] == 'RESERVED']
    
    if not user_res:
        return jsonify({'error': 'EMPTY_CART'}), 409
        
    amount = sum(prods[r['product_id']]['price'] * r['qty'] for r in user_res)
    
    payment = process_payment(customer_id, data.get('method', 'UPI'), amount, idem_key)
    
    if payment['status'] == 'SUCCESS':
        # Release holds as sold
        pass # In full implementation, we transition RESERVED -> SOLD here
        return jsonify(payment), 201
    else:
        return jsonify(payment), 402

if __name__ == '__main__':
    # Init data dirs
    os.makedirs('data', exist_ok=True)
    if not os.path.exists('data/reservations.json'):
        with open('data/reservations.json', 'w') as f: json.dump({}, f)
    app.run(port=5000, debug=True)
