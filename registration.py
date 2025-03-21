import sqlite3
from werkzeug.security import generate_password_hash

DATABASE = "instance/projects.db"  # Update this if needed

def register_user(username, password):
    hashed_password = generate_password_hash(password)
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    try:
        cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hashed_password))
        conn.commit()
        print(f"User '{username}' registered successfully!")
    except sqlite3.IntegrityError:
        print(f"Username '{username}' already exists.")
    
    conn.close()

if __name__ == "__main__":
    username = input("Enter your desired username: ")
    password = input("Enter your password: ")
    register_user(username, password)

