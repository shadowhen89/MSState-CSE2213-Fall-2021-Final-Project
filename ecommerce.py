from database import Database
from json_loader import decode_json

DB_SETTINGS = decode_json("settings/db_settings.json")
DB = Database(DB_SETTINGS["database"], DB_SETTINGS["user"], DB_SETTINGS["password"])

class User:
    
    def __init__(self, username, password):
        self._username = username
        self._password = password
        self._payment_info = ""
        self._shipping_address = ""
        self._cart = ShoppingCart()
        self._orders = OrderHistory()

    def verify_login(self):
        if not DB.is_user_exists(self.username, self.password):
            return False
        self._payment_info, self._shipping_address = DB.fetch_account_details(self.username)
        
        if self._payment_info is None:
            self._payment_info = ""
        if self._shipping_address is None:
            self._shipping_address = ""

        return True

    def edit_payment_info(self, payment_info):
        self._payment_info = payment_info
        DB.edit_payment_info(self.username, payment_info)
        DB.commit()

    def edit_shipping_address(self, shipping_address):
        self._shipping_address = shipping_address
        DB.edit_shipping_address(self.username, shipping_address)
        DB.commit()

    def view_account_details(self):
        print("Account Details")
        print("------------------")
        print("Username: " + self.username)
        print("Payment Info: " + self._payment_info)
        print("Shipping Address: " + self._shipping_address)
    
    def create_account(self):
        result = DB.add_user(self._username, self._password)
        if result:
            DB.commit()
        return result
    
    def delete_account(self):
        result = DB.remove_user(self._username)
        if result:
            DB.commit()
        return result
    
    def checkout_cart(self):
        self._cart.checkout(self.username, self._payment_info, self._shipping_address)
    
    def view_cart(self):
        self._cart.view(self.username)

    def cart_empty(self):
        return self._cart.empty(self.username)

    def fetch_cart_items(self):
        return self._cart.fetch_items(self.username)
    
    def view_orders(self):
        self._orders.view(self.username)

    @property
    def username(self):
        return self._username
    
    @username.setter
    def username(self, value):
        self._username = value
    
    @property
    def password(self):
        return self._password
    
    @password.setter
    def password(self, value):
        self._password = value

    @property
    def cart(self):
        return self._cart

    @property
    def orders(self):
        return self._orders


class ShoppingCart:
    
    def view(self, username):
        cart_items = DB.fetch_cart_items(username)
        print("Name | Price | Quantity")
        print("-----------------------")
        for item in cart_items:
            print("{} | {} | {}".format(item["name"], item["price"], item["quantity"]))

    def checkout(self, username, payment_info, shipping_address):
        DB.checkout_cart(username, payment_info, shipping_address)
        DB.commit()
    
    def empty(self, username):
        return DB.is_cart_empty(username)
    
    def fetch_items(self, username):
        cart_items = DB.fetch_cart_items(username)
        converted_items = []
        for item in cart_items:
            converted_items.append(InventoryItem(item["id"], item["name"], item["price"], item["quantity"]))
        return converted_items


class OrderHistory:
    def view(self, username):
        orders = DB.fetch_orders(username)

        for order in orders:
            print("Order #{}".format(order[0]["orderid"]))
            print("Name | Price | Quantity")
            for item in order:
                print("- {} | {} | {}".format(item["name"], item["price"], item["quantity"]))


class Inventory:
    def __init__(self, category_id):
        self.category_id = category_id
    
    def fetch(self):
        rows = DB.fetch_inventory(0)
        items = []
        for row in rows:
            item_id = row[0]
            name = row[1]
            price = float(row[2])
            stock = int(row[3])

            items.append(InventoryItem(item_id, name, price, stock))
        return items


class InventoryItem:
    def __init__(self, item_id, name, price, stock):
        self.item_id = item_id
        self.name = name
        self.price = price
        self.stock = stock

    def add_to_cart(self, username, quantity):
        DB.add_cart_item(username, self.item_id, quantity)
        DB.commit()
    
    def remove_from_cart(self, username, quantity):
        DB.remove_cart_item(username, self.item_id, quantity)
        DB.commit()

    def __str__(self):
        return "{} | {} | {}".format(self.item_id, self.stock, self.name)
