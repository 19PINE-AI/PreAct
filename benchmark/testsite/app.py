"""Lightweight test web application for PreAct benchmarking.

Mimics a WebArena-style e-commerce site with:
- Login page
- Product search/listing
- Product detail with reviews
- Add to cart
- Checkout form
- Order confirmation

This gives us realistic multi-page workflows without requiring
a full Docker environment.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import urllib.parse
import threading
import time

PORT = 8080

# In-memory state
USERS = {"admin": "admin123", "testuser": "password"}
PRODUCTS = [
    {"id": 1, "name": "Wireless Headphones", "price": 49.99, "rating": 4.5, "reviews": 128, "category": "Electronics"},
    {"id": 2, "name": "Running Shoes", "price": 89.99, "rating": 4.2, "reviews": 256, "category": "Sports"},
    {"id": 3, "name": "Coffee Maker", "price": 34.99, "rating": 4.7, "reviews": 89, "category": "Kitchen"},
    {"id": 4, "name": "Laptop Stand", "price": 29.99, "rating": 4.0, "reviews": 45, "category": "Office"},
    {"id": 5, "name": "Yoga Mat", "price": 24.99, "rating": 4.8, "reviews": 312, "category": "Sports"},
    {"id": 6, "name": "Desk Lamp", "price": 19.99, "rating": 3.9, "reviews": 67, "category": "Office"},
    {"id": 7, "name": "Water Bottle", "price": 14.99, "rating": 4.6, "reviews": 189, "category": "Sports"},
    {"id": 8, "name": "Notebook Set", "price": 12.99, "rating": 4.3, "reviews": 78, "category": "Office"},
]
SESSIONS = {}
CARTS = {}
ORDERS = {}

def html_page(title, body, logged_in=False, username=""):
    nav = ""
    if logged_in:
        nav = f"""<nav id="main-nav">
            <a href="/" id="nav-home">Home</a>
            <a href="/products" id="nav-products">Products</a>
            <a href="/cart" id="nav-cart">Cart</a>
            <span id="nav-user">Welcome, {username}</span>
            <a href="/logout" id="nav-logout">Logout</a>
        </nav>"""
    else:
        nav = """<nav id="main-nav">
            <a href="/" id="nav-home">Home</a>
            <a href="/login" id="nav-login">Login</a>
        </nav>"""

    return f"""<!DOCTYPE html>
<html>
<head><title>{title}</title>
<style>
body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; }}
nav {{ background: #333; padding: 10px; margin-bottom: 20px; }}
nav a {{ color: white; margin-right: 15px; text-decoration: none; }}
nav span {{ color: #aaa; float: right; }}
.product {{ border: 1px solid #ddd; padding: 15px; margin: 10px 0; }}
.product h3 {{ margin-top: 0; }}
.btn {{ background: #007bff; color: white; padding: 8px 16px; border: none; cursor: pointer; border-radius: 4px; }}
.btn:hover {{ background: #0056b3; }}
.btn-danger {{ background: #dc3545; }}
input, select, textarea {{ padding: 8px; margin: 5px 0; border: 1px solid #ccc; border-radius: 4px; }}
.form-group {{ margin: 10px 0; }}
.form-group label {{ display: block; margin-bottom: 5px; font-weight: bold; }}
.success {{ background: #d4edda; border: 1px solid #c3e6cb; padding: 15px; border-radius: 4px; }}
.error {{ background: #f8d7da; border: 1px solid #f5c6cb; padding: 15px; border-radius: 4px; }}
.rating {{ color: #ffc107; }}
table {{ width: 100%; border-collapse: collapse; }}
th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
th {{ background: #f5f5f5; }}
.search-box {{ display: flex; gap: 10px; margin-bottom: 20px; }}
.search-box input {{ flex: 1; }}
</style>
</head>
<body>{nav}{body}</body>
</html>"""


class ShopHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress request logging

    def get_session(self):
        cookies = self.headers.get("Cookie", "")
        for part in cookies.split(";"):
            part = part.strip()
            if part.startswith("session="):
                sid = part.split("=", 1)[1]
                return SESSIONS.get(sid)
        return None

    def set_session(self, username):
        sid = f"sess_{int(time.time())}_{username}"
        SESSIONS[sid] = {"username": username}
        CARTS.setdefault(username, [])
        return sid

    def send_html(self, html, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)
        session = self.get_session()
        logged_in = session is not None
        username = session["username"] if session else ""

        if path == "/":
            body = """<h1 id="page-title">TestShop</h1>
            <p>Welcome to TestShop — a simple e-commerce site for benchmarking.</p>
            <a href="/products" class="btn" id="browse-btn">Browse Products</a>"""
            if not logged_in:
                body += ' <a href="/login" class="btn" id="login-btn">Login</a>'
            self.send_html(html_page("TestShop", body, logged_in, username))

        elif path == "/login":
            body = """<h1 id="page-title">Login</h1>
            <form method="POST" action="/login" id="login-form">
                <div class="form-group">
                    <label for="username">Username</label>
                    <input type="text" name="username" id="username" placeholder="Username" required>
                </div>
                <div class="form-group">
                    <label for="password">Password</label>
                    <input type="password" name="password" id="password" placeholder="Password" required>
                </div>
                <button type="submit" class="btn" id="login-submit">Login</button>
            </form>
            <p><small>Test credentials: admin / admin123</small></p>"""
            self.send_html(html_page("Login", body))

        elif path == "/products":
            query = params.get("q", [""])[0].lower()
            category = params.get("category", [""])[0]
            sort_by = params.get("sort", [""])[0]

            filtered = PRODUCTS
            if query:
                filtered = [p for p in filtered if query in p["name"].lower() or query in p["category"].lower()]
            if category:
                filtered = [p for p in filtered if p["category"] == category]
            if sort_by == "price_asc":
                filtered = sorted(filtered, key=lambda p: p["price"])
            elif sort_by == "price_desc":
                filtered = sorted(filtered, key=lambda p: p["price"], reverse=True)
            elif sort_by == "rating":
                filtered = sorted(filtered, key=lambda p: p["rating"], reverse=True)

            categories = sorted(set(p["category"] for p in PRODUCTS))
            cat_options = "".join(f'<option value="{c}" {"selected" if c==category else ""}>{c}</option>' for c in categories)

            body = f"""<h1 id="page-title">Products</h1>
            <div class="search-box">
                <form method="GET" action="/products" id="search-form" style="display:flex;gap:10px;width:100%">
                    <input type="text" name="q" id="search-input" placeholder="Search products..." value="{query}">
                    <select name="category" id="category-filter">
                        <option value="">All Categories</option>
                        {cat_options}
                    </select>
                    <select name="sort" id="sort-select">
                        <option value="">Sort by</option>
                        <option value="price_asc" {"selected" if sort_by=="price_asc" else ""}>Price: Low to High</option>
                        <option value="price_desc" {"selected" if sort_by=="price_desc" else ""}>Price: High to Low</option>
                        <option value="rating" {"selected" if sort_by=="rating" else ""}>Highest Rated</option>
                    </select>
                    <button type="submit" class="btn" id="search-btn">Search</button>
                </form>
            </div>
            <div id="product-list">"""

            if not filtered:
                body += '<p id="no-results">No products found.</p>'
            for p in filtered:
                stars = "★" * int(p["rating"]) + "☆" * (5 - int(p["rating"]))
                body += f"""<div class="product" id="product-{p['id']}">
                    <h3><a href="/product/{p['id']}" id="product-link-{p['id']}">{p['name']}</a></h3>
                    <p>Price: <span class="price">${p['price']:.2f}</span></p>
                    <p class="rating">{stars} ({p['rating']}) — {p['reviews']} reviews</p>
                    <p>Category: {p['category']}</p>
                    <a href="/product/{p['id']}" class="btn">View Details</a>
                </div>"""

            body += f"</div><p id='result-count'>Showing {len(filtered)} of {len(PRODUCTS)} products</p>"
            self.send_html(html_page("Products", body, logged_in, username))

        elif path.startswith("/product/"):
            try:
                pid = int(path.split("/")[2])
                product = next((p for p in PRODUCTS if p["id"] == pid), None)
            except (ValueError, IndexError):
                product = None

            if not product:
                self.send_html(html_page("Not Found", "<h1>Product Not Found</h1>", logged_in, username), 404)
                return

            stars = "★" * int(product["rating"]) + "☆" * (5 - int(product["rating"]))
            add_btn = ""
            if logged_in:
                add_btn = f"""<form method="POST" action="/cart/add" id="add-to-cart-form">
                    <input type="hidden" name="product_id" value="{product['id']}">
                    <div class="form-group">
                        <label for="quantity">Quantity</label>
                        <input type="number" name="quantity" id="quantity" value="1" min="1" max="10">
                    </div>
                    <button type="submit" class="btn" id="add-to-cart-btn">Add to Cart</button>
                </form>"""
            else:
                add_btn = '<p><a href="/login" class="btn">Login to Add to Cart</a></p>'

            body = f"""<h1 id="product-title">{product['name']}</h1>
            <div id="product-detail">
                <p id="product-price">Price: ${product['price']:.2f}</p>
                <p id="product-rating" class="rating">{stars} ({product['rating']} out of 5)</p>
                <p id="product-reviews">{product['reviews']} customer reviews</p>
                <p id="product-category">Category: {product['category']}</p>
                {add_btn}
            </div>
            <a href="/products">← Back to Products</a>"""
            self.send_html(html_page(product["name"], body, logged_in, username))

        elif path == "/cart":
            if not logged_in:
                self.send_response(302)
                self.send_header("Location", "/login")
                self.end_headers()
                return

            cart = CARTS.get(username, [])
            total = sum(item["price"] * item["qty"] for item in cart)

            body = '<h1 id="page-title">Shopping Cart</h1>'
            if not cart:
                body += '<p id="empty-cart">Your cart is empty.</p><a href="/products" class="btn">Browse Products</a>'
            else:
                body += '<table id="cart-table"><tr><th>Product</th><th>Price</th><th>Qty</th><th>Subtotal</th><th>Action</th></tr>'
                for i, item in enumerate(cart):
                    body += f"""<tr id="cart-item-{i}">
                        <td>{item['name']}</td><td>${item['price']:.2f}</td><td>{item['qty']}</td>
                        <td>${item['price'] * item['qty']:.2f}</td>
                        <td><a href="/cart/remove?idx={i}" class="btn btn-danger" id="remove-{i}">Remove</a></td>
                    </tr>"""
                body += f"""</table>
                <p id="cart-total"><strong>Total: ${total:.2f}</strong></p>
                <a href="/checkout" class="btn" id="checkout-btn">Proceed to Checkout</a>
                <a href="/products">Continue Shopping</a>"""
            self.send_html(html_page("Cart", body, logged_in, username))

        elif path == "/cart/remove":
            if logged_in:
                idx = int(params.get("idx", [0])[0])
                cart = CARTS.get(username, [])
                if 0 <= idx < len(cart):
                    cart.pop(idx)
            self.send_response(302)
            self.send_header("Location", "/cart")
            self.end_headers()

        elif path == "/checkout":
            if not logged_in:
                self.send_response(302)
                self.send_header("Location", "/login")
                self.end_headers()
                return

            cart = CARTS.get(username, [])
            total = sum(item["price"] * item["qty"] for item in cart)

            body = f"""<h1 id="page-title">Checkout</h1>
            <p>Order Total: <strong id="order-total">${total:.2f}</strong></p>
            <form method="POST" action="/checkout" id="checkout-form">
                <div class="form-group">
                    <label for="full_name">Full Name</label>
                    <input type="text" name="full_name" id="full_name" placeholder="John Doe" required>
                </div>
                <div class="form-group">
                    <label for="email">Email</label>
                    <input type="email" name="email" id="email" placeholder="john@example.com" required>
                </div>
                <div class="form-group">
                    <label for="address">Shipping Address</label>
                    <textarea name="address" id="address" placeholder="123 Main St, City, State ZIP" required></textarea>
                </div>
                <div class="form-group">
                    <label for="card_number">Card Number</label>
                    <input type="text" name="card_number" id="card_number" placeholder="4111111111111111" required>
                </div>
                <button type="submit" class="btn" id="place-order-btn">Place Order</button>
            </form>"""
            self.send_html(html_page("Checkout", body, logged_in, username))

        elif path.startswith("/order/"):
            oid = path.split("/")[2]
            order = ORDERS.get(oid)
            if not order:
                self.send_html(html_page("Not Found", "<h1>Order Not Found</h1>"), 404)
                return
            body = f"""<div class="success">
                <h1 id="page-title">Order Confirmed!</h1>
                <p id="order-id">Order ID: {oid}</p>
                <p id="order-name">Name: {order['name']}</p>
                <p id="order-email">Email: {order['email']}</p>
                <p id="order-total">Total: ${order['total']:.2f}</p>
                <p id="order-items">Items: {order['item_count']}</p>
            </div>
            <a href="/products" class="btn">Continue Shopping</a>"""
            self.send_html(html_page("Order Confirmed", body, logged_in, username))

        elif path == "/logout":
            self.send_response(302)
            self.send_header("Location", "/")
            self.send_header("Set-Cookie", "session=; Max-Age=0")
            self.end_headers()

        else:
            self.send_html(html_page("Not Found", "<h1>404 Not Found</h1>"), 404)

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode()
        params = urllib.parse.parse_qs(body)
        session = self.get_session()
        logged_in = session is not None
        username = session["username"] if session else ""

        if self.path == "/login":
            uname = params.get("username", [""])[0]
            pwd = params.get("password", [""])[0]
            if USERS.get(uname) == pwd:
                sid = self.set_session(uname)
                self.send_response(302)
                self.send_header("Location", "/products")
                self.send_header("Set-Cookie", f"session={sid}; Path=/")
                self.end_headers()
            else:
                html = html_page("Login Failed",
                    '<div class="error"><h1>Login Failed</h1><p id="error-msg">Invalid credentials</p></div>'
                    '<a href="/login">Try Again</a>')
                self.send_html(html, 401)

        elif self.path == "/cart/add":
            if not logged_in:
                self.send_response(302)
                self.send_header("Location", "/login")
                self.end_headers()
                return
            pid = int(params.get("product_id", [0])[0])
            qty = int(params.get("quantity", [1])[0])
            product = next((p for p in PRODUCTS if p["id"] == pid), None)
            if product:
                cart = CARTS.setdefault(username, [])
                # Check if already in cart
                existing = next((i for i in cart if i["id"] == pid), None)
                if existing:
                    existing["qty"] += qty
                else:
                    cart.append({"id": pid, "name": product["name"], "price": product["price"], "qty": qty})
            self.send_response(302)
            self.send_header("Location", "/cart")
            self.end_headers()

        elif self.path == "/checkout":
            if not logged_in:
                self.send_response(302)
                self.send_header("Location", "/login")
                self.end_headers()
                return
            name = params.get("full_name", [""])[0]
            email = params.get("email", [""])[0]
            cart = CARTS.get(username, [])
            total = sum(item["price"] * item["qty"] for item in cart)
            oid = f"ORD-{int(time.time())}"
            ORDERS[oid] = {
                "name": name, "email": email, "total": total,
                "item_count": sum(i["qty"] for i in cart), "items": list(cart),
            }
            CARTS[username] = []  # Clear cart
            self.send_response(302)
            self.send_header("Location", f"/order/{oid}")
            self.end_headers()

        else:
            self.send_html("<h1>Not Found</h1>", 404)


def run_server(port=PORT):
    server = HTTPServer(("", port), ShopHandler)
    print(f"TestShop running on http://localhost:{port}")
    server.serve_forever()


def start_background(port=PORT):
    """Start the server in a background thread."""
    t = threading.Thread(target=run_server, args=(port,), daemon=True)
    t.start()
    time.sleep(0.5)
    return t


if __name__ == "__main__":
    run_server()
