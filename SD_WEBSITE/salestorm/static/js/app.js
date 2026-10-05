// Identity management
function getCustomerId() {
    let id = localStorage.getItem('customerId');
    if (!id && !window.location.pathname.includes('/login')) {
        window.location.href = '/login';
        return null;
    }
    return id;
}

function logout() {
    localStorage.removeItem('customerId');
    window.location.href = '/login';
}

const customerId = getCustomerId();

async function apiCall(endpoint, method = 'GET', body = null) {
    if (!customerId && endpoint !== '/login') return; // wait for redirect
    
    const headers = {
        'X-Customer-Id': customerId,
        'Content-Type': 'application/json'
    };
    
    if (['POST', 'PATCH', 'DELETE'].includes(method)) {
        headers['Idempotency-Key'] = crypto.randomUUID();
    }

    const res = await fetch(endpoint, {
        method,
        headers,
        body: body ? JSON.stringify(body) : null
    });
    
    const data = await res.json();
    if (!res.ok) throw data;
    return data;
}

function showToast(msg) {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.textContent = msg;
    toast.style.cssText = `
        background: var(--card); border-left: 4px solid var(--accent);
        padding: 12px 24px; margin-top: 10px; border-radius: 4px;
        color: white; font-family: 'Inter', sans-serif;
    `;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}
