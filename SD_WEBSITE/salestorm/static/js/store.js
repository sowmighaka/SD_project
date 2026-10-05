async function loadProducts() {
    const grid = document.getElementById('product-grid');
    try {
        const products = await apiCall('/api/products');
        if (!products) return;
        
        let totalCart = products.reduce((sum, p) => sum + (p.in_cart || 0), 0);
        const badge = document.getElementById('cart-badge');
        if (badge) badge.innerText = totalCart;

        grid.innerHTML = products.map(p => {
            const available = p.available;
            const inCart = p.in_cart || 0;
            const discount = Math.round((1 - p.price / p.mrp) * 100);
            
            const btnHtml = inCart > 0 
                ? `<div class="in-cart-state">
                     <div class="stepper">
                        <button class="step-btn" onclick="updateQty('${p.id}', -1)">-</button>
                        <span>${inCart}</span>
                        <button class="step-btn" onclick="updateQty('${p.id}', 1)">+</button>
                     </div>
                     <span class="in-cart-text">In cart</span>
                   </div>`
                : `<button class="btn-add" onclick="addToCart('${p.id}')">Add to cart</button>`;

            return `
            <div class="card">
                <div class="card-img" style="background: linear-gradient(135deg, ${p.gradient[0]}, ${p.gradient[1]}); overflow: hidden;">
                    <span class="badge">${discount}% off</span>
                    ${p.image ? `<img src="${p.image}" style="width: 100%; height: 100%; object-fit: cover; opacity: 0.9; mix-blend-mode: overlay;">` : p.emoji}
                </div>
                <div class="card-body">
                    <h3 style="margin: 0; font-size: 20px;">${p.name}</h3>
                    <p style="color: var(--text-muted); font-size: 14px; margin: 4px 0 16px 0;">${p.description}</p>
                    
                    <div class="price-row">
                        <span class="price">₹${p.price.toLocaleString('en-IN')}</span>
                        <span class="mrp">₹${p.mrp.toLocaleString('en-IN')}</span>
                    </div>

                    <div class="progress-bg">
                        <div class="progress-fill" style="width: ${(available/p.total)*100}%"></div>
                    </div>
                    <p style="color: var(--text-muted); font-size: 13px; margin: 8px 0 16px 0;">${available} of ${p.total} left</p>
                    
                    ${btnHtml}
                </div>
            </div>`;
        }).join('');
    } catch (e) {
        if(e && e.message) grid.innerHTML = '<p style="color: var(--danger)">Failed to load products.</p>';
    }
}

async function addToCart(productId) {
    try {
        await apiCall('/api/cart/items', 'POST', { productId, qty: 1 });
        showToast('Added to cart!');
        loadProducts();
    } catch (e) {
        showToast(e.message || 'Error adding to cart');
    }
}

async function updateQty(productId, delta) {
    if (delta > 0) {
        await addToCart(productId);
    } else {
        try {
            await apiCall(`/api/cart/items/${productId}`, 'DELETE');
            showToast('Removed from cart!');
            loadProducts();
        } catch (e) {
            showToast(e.message || 'Error removing from cart');
        }
    }
}

// Start polling
const ud = document.getElementById('user-display');
if (ud && customerId) ud.innerText = `Hi, ${customerId}`;

loadProducts();
setInterval(loadProducts, 4000);
