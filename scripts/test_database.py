from app.database.connection import test_database_connection


if __name__ == "__main__":
    result = test_database_connection()

    print("Database connection successful!")
    print("SELECT 1 returned:", result)