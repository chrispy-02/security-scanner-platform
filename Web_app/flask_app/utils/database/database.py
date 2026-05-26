import mysql.connector
import itertools
import hashlib
import os
from dotenv import load_dotenv
from cryptography.fernet import Fernet
from math import pow


class database:

    def __init__(self):

        if os.getenv("DOCKER_ENV") != "true":
            load_dotenv()

        self.database = os.getenv("MYSQL_DATABASE")
        self.host = os.getenv("MYSQL_HOST", "127.0.0.1")
        self.user = os.getenv("MYSQL_USER")
        self.port = int(os.getenv("MYSQL_PORT", 33306))
        self.password = os.getenv("MYSQL_PASSWORD")

        # Crypto material is read from the environment. The previously hard-coded
        # values were committed publicly and are considered compromised (see SECURITY.md).
        salt = os.getenv("PASSWORD_SALT", "vulnscan-dev-default-salt-change-me").encode("utf-8")

        fernet_key = os.getenv("FERNET_KEY", "").strip()
        if not fernet_key:
            if os.getenv("FLASK_ENV", "production").lower() == "production":
                raise RuntimeError("FERNET_KEY must be set in production.")
            # Ephemeral dev key: sessions reset on restart and won't work across workers.
            fernet_key = Fernet.generate_key().decode()

        self.encryption = {'oneway': {'salt': salt,
                                      'n': int(pow(2, 5)),
                                      'r': 9,
                                      'p': 1
                                      },
                           'reversible': {'key': fernet_key}
                           }

        print("Connecting to MySQL at:", self.host, ":", self.port)

        try:
            cnx = mysql.connector.connect(host=self.host,
                                          user=self.user,
                                          password=self.password,
                                          port=self.port,
                                          database=self.database,
                                          charset='utf8mb4'
                                          )
            cursor = cnx.cursor()
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            print(f"Connected to MySQL Server version: {version[0]}")
        except mysql.connector.Error as err:
            print(f"Error: {err}")

    # Queries the db with a given query and returns the result
    def query(self, query="SELECT * FROM users", parameters=None):

        cnx = mysql.connector.connect(host=self.host,
                                      user=self.user,
                                      password=self.password,
                                      port=self.port,
                                      database=self.database,
                                      charset='utf8mb4'
                                      )

        if parameters is not None:
            cur = cnx.cursor(dictionary=True)
            cur.execute(query, parameters)
        else:
            cur = cnx.cursor(dictionary=True)
            cur.execute(query)

        # Fetch one result
        row = cur.fetchall()
        cnx.commit()

        if "INSERT" in query:
            cur.execute("SELECT LAST_INSERT_ID()")
            row = cur.fetchall()
            cnx.commit()
        cur.close()
        cnx.close()
        return row

    # Insert row(s) into a table in the db. Takes a list of columns and a list of lists of data
    def insertRows(self, table='table', columns=['x', 'y'], parameters=[['v11', 'v12'], ['v21', 'v22']]):

        # Check if there are multiple rows present in the parameters
        has_multiple_rows = any(isinstance(el, list) for el in parameters)
        keys, values = ','.join(columns), ','.join(['%s' for x in columns])

        # Construct the query we will execute to insert the row(s)
        query = f"""INSERT IGNORE INTO {table} ({keys}) VALUES """
        if has_multiple_rows:
            for p in parameters:
                query += f"""({values}),"""
            query = query[:-1]
            parameters = list(itertools.chain(*parameters))
        else:
            query += f"""({values}) """

        insert_id = self.query(query, parameters)[0]['LAST_INSERT_ID()']
        return insert_id

    #######################################################################################
    # AUTHENTICATION RELATED
    #######################################################################################
    def createUser(self, email='me@email.com', password='password', role='user', api_key=None):
        # Get all existing users
        existing = self.query("SELECT * FROM users")

        # If email is in users already, return failure
        for entry in existing:
            if entry['email'] == email:
                return {'success', 0}

        columns = ['role', 'email', 'password', 'api_key']
        # Encrypt password and insert into users
        if password == 'password':
            encrypted_api_key = self.onewayEncrypt(api_key)
            self.insertRows("users", columns, [[f'{role}', f'{email}', f'Oauth', f'{encrypted_api_key}']])
        else:
            encrypted = self.onewayEncrypt(password)
            self.insertRows("users", columns, [[f'{role}', f'{email}', f'{encrypted}']])

        # Return success
        return {'success': 1}
    
    def generate_api_key(self, user_id=None, api_key=None):
        encrypted_api_key = self.onewayEncrypt(api_key)
        set_key_query = "UPDATE users SET api_key = %s WHERE user_id = %s"
        self.query(set_key_query, [encrypted_api_key, user_id])

    def api_authenticate(self, api_key=None):
        api_query = "SELECT * FROM users WHERE api_key = %s"
        encrypted_api_key = self.onewayEncrypt(api_key)
        user_id = self.query(api_query, [encrypted_api_key])
        if (user_id == []):
            return -1, -1
        else:
            return user_id[0]['email'], user_id[0]['user_id']

    # Authenticate login info from /login form fields (NOT OAUTH)
    def authenticate(self, email='me@email.com', password='password'):

        # Get all users
        users = self.query(f"SELECT * FROM users")

        # Encrypt password
        enc_pass = self.onewayEncrypt(password)

        # If email and password is in users, return True
        for entry in users:
            if (email in entry['email']) and (enc_pass in entry['password']):
                return True

        # Else, return false
        return False

    # Encrypts a string using hashlib library
    def onewayEncrypt(self, string):
        encrypted_string = hashlib.scrypt(string.encode('utf-8'),
                                          salt=self.encryption['oneway']['salt'],
                                          n=self.encryption['oneway']['n'],
                                          r=self.encryption['oneway']['r'],
                                          p=self.encryption['oneway']['p']
                                          ).hex()
        return encrypted_string

    # Encrypts or decrypts a message
    def reversibleEncrypt(self, type, message):
        fernet = Fernet(self.encryption['reversible']['key'])

        if type == 'encrypt':
            message = fernet.encrypt(message.encode())
        elif type == 'decrypt':
            message = fernet.decrypt(message).decode()

        return message
