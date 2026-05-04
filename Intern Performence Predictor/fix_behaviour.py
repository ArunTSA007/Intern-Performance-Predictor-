import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "database.db")

def migrate_behaviours():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute("UPDATE behaviour_ratings SET rating = '5' WHERE rating = 'Excellent'")
    c.execute("UPDATE behaviour_ratings SET rating = '4' WHERE rating = 'Good'")
    c.execute("UPDATE behaviour_ratings SET rating = '3' WHERE rating = 'Average'")
    c.execute("UPDATE behaviour_ratings SET rating = '2' WHERE rating = 'Poor'")
    conn.commit()
    conn.close()
    print("Database behaviour ratings migrated successfully.")

if __name__ == '__main__':
    migrate_behaviours()
