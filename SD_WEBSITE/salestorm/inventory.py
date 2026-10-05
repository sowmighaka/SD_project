import threading
import time
from storage import read_json, write_json_atomic
import json

inventory_lock = threading.Lock()

PRODUCTS_FILE = 'data/products.json'
RESERVATIONS_FILE = 'data/reservations.json'
WAITLIST_FILE = 'data/waitlist.json'

def get_products():
    return read_json(PRODUCTS_FILE, [])

def get_reservations():
    return read_json(RESERVATIONS_FILE, {})

def reserve_item(customer_id, product_id, qty, hold_mins, idempotency_key, max_per_prod):
    # atomic reserve
    with inventory_lock:
        prods = get_products()
        res = get_reservations()
        
        # Idempotency check
        key = f"{customer_id}_{idempotency_key}"
        for r in res.values():
            if r.get('idempotency_key') == key:
                return {'status': 'success', 'reserved': True}

        prod = next((p for p in prods if p['id'] == product_id), None)
        if not prod:
            return {'error': 'NOT_FOUND', 'message': 'Product not found'}

        # Calculate current cart qty
        current_qty = sum(r['qty'] for r in res.values() if r['customer_id'] == customer_id and r['product_id'] == product_id and r['status'] == 'RESERVED')
        
        if current_qty + qty > max_per_prod:
            return {'error': 'LIMIT_REACHED', 'message': f'Limit {max_per_prod} per product'}
            
        if prod['available'] < qty:
            return {'error': 'OUT_OF_STOCK', 'message': 'Not enough stock'}

        # Update stock
        prod['available'] -= qty
        prod['reserved'] += qty
        
        res_id = f"res_{int(time.time()*1000)}_{customer_id}"
        res[res_id] = {
            'id': res_id,
            'customer_id': customer_id,
            'product_id': product_id,
            'qty': qty,
            'status': 'RESERVED',
            'expires_at': time.time() + (hold_mins * 60),
            'idempotency_key': key
        }
        
        write_json_atomic(PRODUCTS_FILE, prods)
        write_json_atomic(RESERVATIONS_FILE, res)
        return {'status': 'success', 'reservation_id': res_id}

def remove_item(customer_id, product_id, qty_to_remove=1):
    with inventory_lock:
        prods = get_products()
        res = get_reservations()
        
        user_res = [r for r_id, r in res.items() if r['customer_id'] == customer_id and r['product_id'] == product_id and r['status'] == 'RESERVED']
        
        removed = 0
        for r in user_res:
            if removed >= qty_to_remove: break
            take = min(r['qty'], qty_to_remove - removed)
            r['qty'] -= take
            removed += take
            if r['qty'] <= 0:
                r['status'] = 'RELEASED'
                
        prod = next((p for p in prods if p['id'] == product_id), None)
        if prod and removed > 0:
            prod['reserved'] -= removed
            prod['available'] += removed
            
        if removed > 0:
            write_json_atomic(PRODUCTS_FILE, prods)
            write_json_atomic(RESERVATIONS_FILE, res)
            
        return {'status': 'success'}

def sweeper():
    while True:
        time.sleep(1)
        with inventory_lock:
            res = get_reservations()
            prods = get_products()
            changed = False
            now = time.time()
            
            for r_id, r in res.items():
                if r['status'] == 'RESERVED' and r['expires_at'] < now:
                    r['status'] = 'RELEASED'
                    prod = next((p for p in prods if p['id'] == r['product_id']), None)
                    if prod:
                        prod['reserved'] -= r['qty']
                        prod['available'] += r['qty']
                    changed = True
            
            if changed:
                write_json_atomic(PRODUCTS_FILE, prods)
                write_json_atomic(RESERVATIONS_FILE, res)

# Start sweeper thread
threading.Thread(target=sweeper, daemon=True).start()
