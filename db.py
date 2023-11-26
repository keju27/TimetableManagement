import sqlite3
from sqlite3 import Error

def create_connection(db_file):
    """ Create a database connection to a SQLite database """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        print(f'Successful connection to {db_file}')
        return conn
    except Error as e:
        print(e)

    return conn

def create_table(conn, create_table_sql):
    """ Create a table from the create_table_sql statement """
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except Error as e:
        print(e)

def create_all_tables(conn):
    # Teacher Table
    teacher_table_sql = """
        CREATE TABLE IF NOT EXISTS teachr_table (
            teacher_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            department TEXT NOT NULL
        );
    """

    # Teacher Timetable Table
    teacher_timetable_sql = """
        CREATE TABLE IF NOT EXISTS teacher_timetable (
            timetable_id INTEGER PRIMARY KEY,
            teacher_id INTEGER,
            class_id INTEGER,
            date DATE,
            start_time TIME,
            end_time TIME,
            is_available INTEGER,
            FOREIGN KEY (teacher_id) REFERENCES teachr_table (teacher_id)
        );
    """

    # Unavailability Data Table
    unavailability_data_sql = """
        CREATE TABLE IF NOT EXISTS unavailability_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id INTEGER,
            date DATE,
            start_time TIME,
            end_time TIME,
            department TEXT,
            FOREIGN KEY (teacher_id) REFERENCES teachr_table (teacher_id),
            UNIQUE (teacher_id, date, start_time, end_time)
        );
    """

    # Potential Replacements Table
    potential_replacements_sql = """
        CREATE TABLE IF NOT EXISTS potential_replacements (
            potential_id INTEGER PRIMARY KEY AUTOINCREMENT,
            teacher_id INTEGER,
            replace_id INTEGER,
            FOREIGN KEY (teacher_id) REFERENCES teachr_table (teacher_id),
            FOREIGN KEY (replace_id) REFERENCES teachr_table (teacher_id),
            UNIQUE (teacher_id, replace_id)
        );
    """

    # Class Table
    class_sql = """
        CREATE TABLE IF NOT EXISTS class (
            class_id INTEGER PRIMARY KEY,
            name TEXT,
            room_number INTEGER
        );
    """

    # Class Timetable Table
    class_timetable_sql = """
        CREATE TABLE IF NOT EXISTS class_timetable (
            timetable_id INTEGER PRIMARY KEY,
            class_id INTEGER,
            teacher_id INTEGER,
            start_time TIME,
            end_time TIME,
            date DATE,
            FOREIGN KEY (class_id) REFERENCES class(class_id),
            FOREIGN KEY (teacher_id) REFERENCES teachr_table(teacher_id)
        );
    """

    # Create tables
    create_table(conn, teacher_table_sql)
    create_table(conn, teacher_timetable_sql)
    create_table(conn, unavailability_data_sql)
    create_table(conn, potential_replacements_sql)
    create_table(conn, class_sql)
    create_table(conn, class_timetable_sql)

    print("All tables created successfully")

def main():
    database = "re-assignment.db"  # Change this to your desired database name

    # create a database connection
    conn = create_connection(database)

    # create all tables
    if conn is not None:
        create_all_tables(conn)

        # close the database connection
        conn.close()
    else:
        print("Error! cannot create the database connection.")

if __name__ == "__main__":
    main()
