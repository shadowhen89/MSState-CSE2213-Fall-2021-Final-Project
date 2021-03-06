import psycopg2
from datetime import date, datetime

class Database:
    def __init__(self, database, user, password):
        self._connection = psycopg2.connect(database=database, user=user, password=password)
        self._cursor = self._connection.cursor()
    
    def execute(self, query, vals = ()):
        self._cursor.execute(query, vals)

    def commit(self):
        self._connection.commit()
    
    def close(self):
        self._connection.close()

    """Adds user and returns if adding user is success"""
    def add_user(self, username, password):
        try:
            self._cursor.execute("INSERT INTO users VALUES (%s, %s)", (username, password))
        except:
            return False
        return True
    
    """Removes user and returns if removing user is success"""
    def remove_user(self, username):
        if not self.is_username_exists(username):
            return False
        vals = (username,)
        self._cursor.execute("DELETE FROM order_items WHERE userid=%s", vals)
        self._cursor.execute("DELETE FROM orders WHERE userid=%s", vals)
        self._cursor.execute("DELETE FROM cart_items WHERE username=%s", vals)
        self._cursor.execute("DELETE FROM users WHERE username=%s", vals)
        return True
    
    """Fetches payment info and shipping addreess of an user"""
    def fetch_account_details(self, username):
        self._check_user_in_database(username)
        self._cursor.execute("SELECT paymentinfo, shippingaddress FROM users WHERE username = %s", (username,))
        result = self._cursor.fetchone()
        return result[0], result[1]

    """Edits user's payment info and returns if editing payment info is success"""
    def edit_payment_info(self, username, payment_info):
        if not self.is_username_exists(username):
            return False
        self._cursor.execute("UPDATE users SET paymentinfo = %s WHERE username = %s", (payment_info, username))
        return True
    
    """Edits user's shipping address and returns if editing shipping address is success"""
    def edit_shipping_address(self, username, shipping_address):
        if not self.is_username_exists(username):
            return False
        self._cursor.execute("UPDATE users SET shippingaddress = %s WHERE username = %s", (shipping_address, username))
        return True
    
    """Adds item to the cart based on the username, item id, and quantity"""
    def add_cart_item(self, username, item_id, quantity):
        if quantity <= 0:
            raise Exception("Quantity for adding cart item must be non-negative non-zero number")

        self._check_user_in_database(username)
        self._cursor.execute("SELECT quantity FROM cart_items WHERE username = %s AND itemid = %s", (username, item_id))
        result = self._cursor.fetchone()

        if result is None:
            try:
                self._cursor.execute("INSERT INTO cart_items VALUES (%s, %s, %s)", (username, item_id, quantity))
            except:
                raise Exception("Item id %s does not exist in the database" % (item_id))
        else:
            final_quantity = str(int(quantity) + int(result[0]))
            self._cursor.execute("UPDATE cart_items SET quantity = %s WHERE username = %s AND itemid = %s", (final_quantity, username, item_id))
    
    """Removes item from the cart based on the username, item id, and quantity"""
    def remove_cart_item(self, username, item_id, quantity):
        if quantity <= 0:
            raise Exception("Quantity for adding cart item must be non-negative non-zero number")
        self._check_user_in_database(username)

        self._cursor.execute("SELECT quantity FROM cart_items WHERE username = %s AND itemid = %s", (username, item_id))
        result = self._cursor.fetchone()
        if result is None:
            raise Exception("No item with id %s exists in the cart" % (item_id))
        
        result_quantity = result[0]
        final_quantity = result_quantity - int(quantity)

        if final_quantity == 0:
            self._cursor.execute("DELETE FROM cart_items WHERE username = %s AND itemid = %s", (username, item_id))
        elif final_quantity > 0:
            self._cursor.execute("UPDATE cart_items SET quantity = %s WHERE username = %s AND itemid = %s", (final_quantity, username, item_id))
        else:
            raise Exception("Final quantity cannot be negative")
    
    """Fetch cart items based on username"""
    def fetch_cart_items(self, username):
        self._cursor.execute(
            "SELECT I._id, I.name, I.price, C.quantity "
            "FROM inventory AS I, cart_items AS C "
            "WHERE I._id = C.itemid AND C.username = %s ",
            (username,)
        )
        cart_item_list = []
        for row in self._cursor.fetchall():
            cart_item_dict = {"id": row[0], "name": row[1], "price": row[2], "quantity": row[3]}
            cart_item_list.append(cart_item_dict)
        return cart_item_list
    
    """Checkouts the cart by generating order, copying cart items as order items, and clearing the cart"""
    def checkout_cart(self, username, payment_info, shipping_address):
        self._check_user_in_database(username)

        # Fetch cart items
        cart_item_query = \
            "SELECT _id, quantity, price, stock " \
            "FROM cart_items, inventory " \
            "WHERE itemid = _id AND username = %s"
        cart_item_vals = (username,)
        self._cursor.execute(cart_item_query, cart_item_vals)
        cart_items = self._cursor.fetchall()

        # Raises error if the cart is empty since we cannot checkout with empty cart
        # and generate an order
        if len(cart_items) == 0:
            raise Exception("Cannot checkout empty cart")

        # Generate an order id
        self._cursor.execute("SELECT _id FROM orders WHERE userid = %s ORDER BY _id DESC LIMIT 1", (username,))
        result = self._cursor.fetchone()
        next_id = -1
        if result == None:
            next_id = str(0)
        else:
            next_id = str(int(result[0]) + 1)

        # Create new order
        now = datetime.now()
        insert_date = "%s-%s-%s" % (now.year, now.month, now.day)
        insert_query = "INSERT INTO orders VALUES (%s, %s, %s, %s, %s)"
        insert_vals = (next_id, username, insert_date, payment_info, shipping_address)
        self._cursor.execute(insert_query, insert_vals)
        
        # Add order items
        order_item_query = "INSERT INTO order_items VALUES (%s, %s, %s, %s, %s, %s)"
        for i in range(len(cart_items)):
            cart_item = cart_items[i]
            order_item_vals = (i, next_id, username, cart_item[0], cart_item[1], cart_item[2])
            self._cursor.execute(order_item_query, order_item_vals)
        
        # Clears cart
        self._cursor.execute("DELETE FROM cart_items WHERE username = %s", (username,))

        # Decrements the inventory stock
        decrement_query = "UPDATE inventory SET stock = %s WHERE _id = %s"
        for item in cart_items:
            new_stock = str(int(item[3]) - int(item[1]))
            self._cursor.execute(decrement_query, (new_stock, item[0]))
    
    def fetch_orders(self, username):
        query = \
            "SELECT O.orderid, O._id, I.name, O.price, O.quantity " \
            "FROM order_items AS O, inventory AS I " \
            "WHERE O.userid = %s AND I._id = O.itemid " \
            "ORDER BY O.orderid "
        vals = (username,)
        self._cursor.execute(query, vals)
        order_items = self._cursor.fetchall()

        orders = []
        orders_idx = -1
        for item in order_items:
            if orders_idx != int(item[0]):
                orders.append([])
                orders_idx += 1
            order_info = {"orderid": item[0], "linenum": item[1], "name": item[2], "price": item[3], "quantity": item[4]}
            orders[orders_idx].append(order_info)
        return orders

    """Returns if the user's cart is empty"""
    def is_cart_empty(self, username):
        self._cursor.execute("SELECT * FROM cart_items WHERE username=%s", (username,))
        cart_items = self._cursor.fetchall()
        return len(cart_items) == 0

    def fetch_inventory(self, category_id):
        self._cursor.execute("SELECT _id, name, price, stock FROM inventory WHERE categoryid = %s ORDER BY _id", (str(category_id),))
        return self._cursor.fetchall()

    """Returns whether the username exists in the database"""
    def is_username_exists(self, username):
        self._cursor.execute("SELECT username FROM users WHERE username LIKE %s", (username,))
        results = self._cursor.fetchall()
        return len(results) > 0
    
    """Returns if the user login match"""
    def is_user_exists(self, username, password):
        query = "SELECT username, password FROM users WHERE username LIKE %s AND password LIKE %s"
        vals = (username, password)
        self._cursor.execute(query, vals)
        result = self._cursor.fetchone()

        if result is None:
            return False
        return result[0] == username and result[1] == password
    
    def _check_user_in_database(self, username):
        if not self.is_username_exists(username):
            raise Exception("Username %s does not exist in the database" % (username))

