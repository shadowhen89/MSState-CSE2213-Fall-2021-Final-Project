import psycopg2

class Database:
    def __init__(self, database, user, password):
        self._connection = psycopg2.connect(database=database, user=user, password=password)
        self._cursor = self._connection.cursor()
    
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
