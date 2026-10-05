import time
import random
import threading
from storage import read_json, write_json_atomic

PAYMENTS_FILE = 'data/payments.json'
ORDERS_FILE = 'data/orders.json'
OUTBOX_FILE = 'data/outbox.json'

payment_lock = threading.Lock()

def get_payments(): return read_json(PAYMENTS_FILE, {})
def get_orders(): return read_json(ORDERS_FILE, {})

def process_payment(customer_id, method, amount, idem_key):
    with payment_lock:
        payments = get_payments()
        
        # Idempotency check
        key = f"{customer_id}_{idem_key}"
        for p in payments.values():
            if p.get('idempotency_key') == key:
                return p
        
        pid = f"pay_{int(time.time()*1000)}"
        
        # Fake Gateway Simulator (95% success)
        outcome = 'SUCCESS'
        if random.random() > 0.95:
            outcome = 'FAILED'
            
        payment = {
            'id': pid,
            'customer_id': customer_id,
            'method': method,
            'amount': amount,
            'status': outcome,
            'idempotency_key': key,
            'created_at': time.time()
        }
        
        payments[pid] = payment
        write_json_atomic(PAYMENTS_FILE, payments)
        
        # Simple outbox / direct order creation
        if outcome == 'SUCCESS':
            _create_order_internal(customer_id, pid, amount, method)
            
        return payment

def _create_order_internal(customer_id, payment_id, amount, method):
    orders = get_orders()
    oid = f"ord_{int(time.time()*1000)}"
    orders[oid] = {
        'id': oid,
        'customer_id': customer_id,
        'payment_id': payment_id,
        'amount': amount,
        'method': method,
        'status': 'CONFIRMED',
        'created_at': time.time()
    }
    write_json_atomic(ORDERS_FILE, orders)
