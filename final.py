import streamlit as st
import sqlite3
from sqlite3 import Error
import pandas as pd
from datetime import datetime

conn = sqlite3.connect('re-assignment.db')  # Change 'your_database.db' to your actual database name
cursor = conn.cursor()

# Streamlit app
st.title("Teacher Timetable Management")

# Function to update the is_available column in the database
def update_availability(teacher_id, availability):
    query = f"UPDATE teacher_timetable SET is_available = {availability} WHERE teacher_id = {teacher_id};"
    cursor.execute(query)
    conn.commit()

# Function to update the unavailability table
def update_unavailability():
    # Query to select teacher_id, date, start_time, and end_time
    query = "SELECT teacher_id, date, start_time, end_time FROM teacher_timetable WHERE is_available = 0;"
    unavailability_data = pd.read_sql(query, conn)
    
    # Insert the data into the unavailability table if it doesn't already exist
    for _, row in unavailability_data.iterrows():
        # Fetch department from teacher_table based on teacher_id
        teacher_id = row['teacher_id']
        department_query = f"SELECT department FROM teachr_table WHERE teacher_id = {teacher_id};"
        department_result = cursor.execute(department_query).fetchone()
        department = department_result[0] if department_result else None
        
        # Check if the record already exists in unavailability_3_data
        existing_query = ("SELECT COUNT(*) FROM unavailability_data "
                          "WHERE teacher_id = ? AND date = ? AND start_time = ? AND end_time = ?;")
        existing_result = cursor.execute(existing_query, (teacher_id, row['date'], row['start_time'], row['end_time'])).fetchone()
        if existing_result[0] == 0:  # If the record doesn't exist, insert it
            cursor.execute("INSERT INTO unavailability_data (teacher_id, date, start_time, end_time, department) VALUES (?, ?, ?, ?, ?);",
                           (teacher_id, row['date'], row['start_time'], row['end_time'], department))
    
    conn.commit()

# Function to delete entry from unavailability_3_data
def delete_unavailability(teacher_id):
    cursor.execute("DELETE FROM unavailability_data WHERE teacher_id = ?;", (teacher_id,))
    conn.commit()

# Function to get a dictionary of teachers in the same department based on entries in unavailability_3_data
def get_teachers_in_same_department():
    # Query to select teacher_id, department from unavailability_3_data
    query = "SELECT teacher_id, department FROM unavailability_data;"
    teachers_and_departments = cursor.execute(query).fetchall()

    department_teacher_dict = {}
    
    for teacher_id, department in teachers_and_departments:
        # Fetch teacher_id of other teachers in the same department
        query_replace = (f"SELECT teacher_id FROM teachr_table "
                         f"WHERE department = '{department}' AND teacher_id != {teacher_id};")
        replace_ids = [replace[0] for replace in cursor.execute(query_replace).fetchall()]
        
        # Update the department_teacher_dict
        if teacher_id in department_teacher_dict:
            department_teacher_dict[teacher_id].extend(replace_ids)
        else:
            department_teacher_dict[teacher_id] = replace_ids

    # Insert data into the potential_replacements table with try-except to handle duplicates
    for teacher_id, replace_ids in department_teacher_dict.items():
        for replace_id in replace_ids:
            try:
                cursor.execute("INSERT INTO potential_replacements (teacher_id, replace_id) VALUES (?, ?);",
                               (teacher_id, replace_id))
            except sqlite3.IntegrityError:
                # Handle duplicate entry (optional, you can just ignore it)
                pass

    conn.commit()
    return department_teacher_dict

def replace_teacher_ids_in_timetable(non_clashing_dict, conn):
    for teacher_id, replace_ids in non_clashing_dict.items():
        st.write(f"Replace options for Teacher {teacher_id}: {replace_ids}")

        # Use Streamlit to create a button to initiate the replacement for the current teacher_id
        if st.button(f"Replace Teacher {teacher_id}"):
            # Use the previously provided function to update the teacher_id with the selected replace_id
            selected_replace_id = st.selectbox(f"Select replacement for Teacher {teacher_id}:", replace_ids)
            update_query = f"UPDATE teacher_timetable SET teacher_id = {selected_replace_id} WHERE teacher_id = {teacher_id};"
            conn.execute(update_query)
            st.success(f"Teacher {teacher_id} replaced with {selected_replace_id} in teacher_timetable.")




# Function to get final replacements for each unique teacher_id
# Function to get final replacements for each unique teacher_id
def check_non_clashing_ids():
    # Query to select teacher_id, date, start_time, and end_time from unavailability_3_data
    unavailability_query = "SELECT teacher_id, date, start_time, end_time FROM unavailability_data;"
    unavailability_data = pd.read_sql(unavailability_query, conn)

    # Dictionary to store non-clashing replace_ids for each teacher_id
    non_clashing_dict = {}

    # Iterate through the rows in unavailability_data
    for _, unavailability_row in unavailability_data.iterrows():
        # Get the teacher_id, date, start_time, and end_time from the current row
        teacher_id = unavailability_row['teacher_id']
        unavailability_date = unavailability_row['date']
        unavailability_start_time = unavailability_row['start_time']
        unavailability_end_time = unavailability_row['end_time']

        # Query to select distinct replace_ids for the current teacher_id
        replace_query = f"SELECT DISTINCT replace_id FROM potential_replacements WHERE teacher_id = {teacher_id};"
        replace_ids = pd.read_sql(replace_query, conn)

        # List to store non-clashing replace_ids
        non_clashing_ids = []

        # Iterate through replace_ids
        for _, replace_row in replace_ids.iterrows():
            replace_id = replace_row['replace_id']

            # Query to select date, start_time, and end_time for the replace_id from teacher_timetable
            timetable_query = f"SELECT date, start_time, end_time FROM teacher_timetable WHERE teacher_id = {replace_id};"
            replace_data = pd.read_sql(timetable_query, conn)

            # Check if the date of replace_id clashes with the date of actual teacher_id
            if unavailability_date not in replace_data['date'].values:
                non_clashing_ids.append(replace_id)
            else:
                # Check if start_time and end_time don't clash
                replace_start_time = replace_data.loc[replace_data['date'] == unavailability_date, 'start_time'].values[0]
                replace_end_time = replace_data.loc[replace_data['date'] == unavailability_date, 'end_time'].values[0]

                if (unavailability_end_time < replace_start_time) or (unavailability_start_time > replace_end_time):
                    non_clashing_ids.append(replace_id)

        # Add the non-clashing replace_ids to the dictionary
        non_clashing_dict[teacher_id] = non_clashing_ids

    # Display the non-clashing replace_ids dictionary
    st.subheader("Non-Clashing Replace IDs")

# Check if the dictionary is not empty
    if non_clashing_dict:
        # Create a DataFrame from the dictionary
        non_clashing_df = pd.DataFrame(list(non_clashing_dict.items()), columns=['Teacher ID', 'Non-Clashing Replace IDs'])
        st.dataframe(non_clashing_df)
    else:
        st.warning("No non-clashing replace IDs found.")


# Function to display the current timetable
def display_timetable():
    st.subheader("Current Teacher Timetable")
    # Query to select all columns from the teacher_timetable table
    query = "SELECT * FROM teacher_timetable;"
    timetable_data = pd.read_sql(query, conn)
    st.dataframe(timetable_data)





# Function to create a database connection
def create_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        st.error(f"Error: {e}")
        

# Function to execute a SQL query
def execute_query(conn, query, data=None):
    try:
        c = conn.cursor()
        if data:
            c.execute(query, data)
        else:
            c.execute(query)
        conn.commit()
        result = c.fetchall()  # Add this line to fetch the result
        return result
    except Error as e:
        st.error(f"Error: {e}")

# Function to add data to a table
def add_data(conn, table_name, data):
    columns = ', '.join(data.keys())
    values = ', '.join(['?' for _ in range(len(data))])
    query = f"INSERT INTO {table_name} ({columns}) VALUES ({values})"
    execute_query(conn, query, tuple(data.values()))

# Function to delete a row from a table
def delete_row(conn, table_name, condition):
    query = f"DELETE FROM {table_name} WHERE {condition}"
    execute_query(conn, query)

# Function to update data in a table
def update_data(conn, table_name, data, condition):
    set_values = ', '.join([f"{key} = ?" for key in data.keys()])
    query = "UPDATE ? SET ? WHERE ?".format(table_name, set_values[1:], condition)
    execute_query(conn, query, tuple(data.values()))

def get_primary_keys(conn, table_name):
    query = f"PRAGMA table_info({table_name})"
    result = execute_query(conn, query)
    primary_keys = [row[1] for row in result if row[5] == 1]  # Column 5 indicates whether it's a primary key
    return primary_keys

def view_table(conn, table_name):
    query = f"SELECT * FROM {table_name}"
    result = execute_query(conn, query)
    st.table(result)


def get_timetable_by_day(conn, table_name, date):
    query = f"SELECT * FROM {table_name} WHERE date = ?;"
    result = execute_query(conn, query, (date,))
    return result

def update_teacher_timetable(data):
    conn = sqlite3.connect('re-assignment.db')  # Change the database name here
    cursor = conn.cursor()

    # Convert time and date to string representations
    formatted_data = (
        data[0],  # class_id
        data[1].strftime('%Y-%m-%d'),  # date
        data[2].strftime('%H:%M:%S'),  # start_time
        data[3].strftime('%H:%M:%S'),  # end_time
        data[4],  # is_available
        data[5]  # teacher_id
    )

    # Execute an update query for teacher_timetable
    cursor.execute(
        "UPDATE teacher_timetable SET class_id = ?, date = ?, start_time = ?, end_time = ?, is_available = ? WHERE teacher_id = ?",
        formatted_data
    )

    conn.commit()
    conn.close()

def check_timetable_clashes(conn):
    query = """
        SELECT t1.teacher_id AS teacher_id1, t2.teacher_id AS teacher_id2
        FROM teacher_timetable t1
        JOIN teacher_timetable t2 ON t1.class_id = t2.class_id
        WHERE t1.teacher_id <> t2.teacher_id 
          AND t1.date = t2.date
          AND (
            (t1.start_time BETWEEN t2.start_time AND t2.end_time)
            OR (t1.end_time BETWEEN t2.start_time AND t2.end_time)
          );
    """

    clashes_df = pd.read_sql_query(query, conn)
    return clashes_df

def display_table_with_update_button(table_name):
    query = f"SELECT * FROM {table_name}"
    df = pd.read_sql_query(query, conn)

    button_pressed = st.button(f"Show {table_name.capitalize()} Table")

    # Display table only when the button is pressed
    if button_pressed:

        # Display the table
        st.write(f"### {table_name.capitalize()} Table")
        st.write(df)

        # Display "Update Row" button
        #update_button_pressed = st.button(f"Update Row in {table_name.capitalize()} Table")

        # If the "Update Row" button is pressed, show a form to update the row
        

def update_row_in_table(table_name, k, primary_key_value, updated_data):
    set_values = ', '.join([f"{column} = ?" for column in updated_data.keys()])
    query = f"UPDATE {table_name} SET {set_values} WHERE {k[:]}_id = ?"
    cursor.execute(query, tuple(updated_data.values()) + (primary_key_value,))
    conn.commit()


# Streamlit app
def main():
    st.title("Database Management App")

    # Database connection


    # Sidebar navigation
    st.sidebar.title("Navigation")
    #selection = st.sidebar.radio("Select Option", ["CRUD"])
    selection = 1
    if selection == 1:
        # Add Data
        st.header("Add Data")
        table_name_add = st.selectbox("Select Table (Add)", ["teachr_table", "teacher_timetable", "class", "class_timetable"], key="add_selectbox")
        if table_name_add == "teachr_table":
            name = st.text_input("Name:")
            department = st.text_input("Department:")
            if st.button("Add"):
                data = {"name": name, "department": department}
                add_data(conn, "teachr_table", data)
        elif table_name_add == "teacher_timetable":
            teacher_id = st.text_input("Teacher ID:")
            class_id = st.text_input("Class ID:")
            date = st.date_input("Date:")
            start_time = st.time_input("Start Time:")
            end_time = st.time_input("End Time:")
            is_available = st.checkbox("Is Available")
            if st.button("Add"):
                data = {
                    "teacher_id": teacher_id,
                    "class_id": class_id,
                    "date": date,
                    "start_time": start_time.strftime('%H:%M:%S'),
                    "end_time": end_time.strftime('%H:%M:%S'),
                    "is_available": is_available,
                }
                add_data(conn, "teacher_timetable", data)
        elif table_name_add == "class":
            class_id = st.text_input("Class ID:")
            name = st.text_input("Name:")
            room_number = st.text_input("Room Number:")
            if st.button("Add"):
                data = {"class_id": class_id, "name": name, "room_number": room_number}
                add_data(conn, "class", data)
        elif table_name_add == "class_timetable":
            timetable_id = st.text_input("Timetable ID:")
            class_id = st.text_input("Class ID:")
            teacher_id = st.text_input("Teacher ID:")
            start_time = st.time_input("Start Time:")
            end_time = st.time_input("End Time:")
            date = st.date_input("Date:")
            if st.button("Add"):
                data = {
                    "timetable_id": timetable_id,
                    "class_id": class_id,
                    "teacher_id": teacher_id,
                    "start_time": start_time.strftime('%H:%M:%S'),
                    "end_time": end_time.strftime('%H:%M:%S'),
                    "date": date,
                }
                add_data(conn, "class_timetable", data)

        # Delete Data
        st.header("Delete Data")
        table_name_delete = st.selectbox("Select Table (Delete)", ["teachr_table", "teacher_timetable", "unavailability_data", "potential_replacements", "class", "class_timetable"], key="delete_selectbox")
        
        # Get primary keys for the selected table
        primary_keys_delete = get_primary_keys(conn, table_name_delete)
        primary_key_value_delete = st.text_input(f"Enter {primary_keys_delete[0]} Value:")

        if st.button("Delete"):
            condition_delete = f"{primary_keys_delete[0]} = {primary_key_value_delete}"
            delete_row(conn, table_name_delete, condition_delete)

        # Update Data

        # View Tables
        display_table_with_update_button("teachr_table")
        display_table_with_update_button("class")
        display_table_with_update_button("class_timetable")
        display_table_with_update_button("teacher_timetable")

    # Close the database connection
    conn.close()

def main_2():


    st.sidebar.title("replacement")
    #selection = st.sidebar.radio("Select Option", ["replace"])
    selection=1

    if selection== 1 :


# Streamlit UI
        st.header("Update Teacher Availability")

        teacher_id = st.number_input("Enter Teacher ID:", min_value=1)
        availability = st.radio("Set Availability:", [0, 1])

        if st.button("Update Availability"):
            update_availability(teacher_id, availability)
            st.success(f"Availability updated for Teacher ID {teacher_id}.")

        # Button to update unavailability table
        if st.button("Update Unavailability Table"):
            if availability == 1:  # If availability is set to 1, delete the entry from unavailability_3_data
                delete_unavailability(teacher_id)
                st.success(f"Entry deleted for Teacher ID {teacher_id} from unavailability_data.")
            else:
                update_unavailability()
                st.success("Unavailability table updated.")

        # Button to get teachers in the same department
        if st.button("Get Teachers in Same Department"):
            department_teacher_dict = get_teachers_in_same_department()
            if department_teacher_dict:
                st.success("Teachers in the same department:")
                for department, teachers in department_teacher_dict.items():
                    st.write(f"Department: {department}, Teachers: {', '.join(map(str, teachers))}")
            else:
                st.warning("No entries in unavailability_data.")

        # Button to get final replacements
        if st.button("Get Final Replacements"):
            final_replacements = check_non_clashing_ids()
            if final_replacements:
                st.success("Final Replacements:")
                for teacher_id, replace_ids in final_replacements.items():
                    st.write(f"Teacher ID: {teacher_id}, Final Replacements: {', '.join(map(str, replace_ids))}")
            else:
                st.warning("No final replacements found.")
            

        # Display current timetable
        display_timetable()

        # Close the database connection
        conn.close()

def main_3():
    st.header("View Timetable by Day")

    # Select table
    table_name_view_day = st.selectbox("Select Table to View", ["teacher_timetable", "class_timetable"])

    # Set the default date to today's date
    default_date = datetime.now().date()

    # Select date
    date_to_view = st.date_input("Date:", value=default_date)

    if st.button("View Timetable"):
        timetable_data_by_day = get_timetable_by_day(conn, table_name_view_day, date_to_view)
        if timetable_data_by_day:
            st.success(f"Timetable for {table_name_view_day} on {date_to_view}:")
            st.dataframe(timetable_data_by_day)
        else:
            st.warning(f"No entries found for {table_name_view_day} on {date_to_view}.")


def main_4():
    st.title("Timetable Clashes Checker")

    database = "re-assignment.db"  # Change this to your database name
    conn = sqlite3.connect(database)

    if st.button("Check Timetable Clashes"):
        clashes_df = check_timetable_clashes(conn)

        if not clashes_df.empty:
            st.subheader("Timetable Clashes:")
            st.dataframe(clashes_df)
        else:
            st.success("No timetable clashes found!")

if __name__ == "__main__":
    app_mode = st.sidebar.radio("Select App Mode", ["CRUD", "Replacemet Management","Today's timetable","Clashes"])

    if app_mode == "CRUD":
        main()
    elif app_mode == "Replacemet Management":
        main_2()
    elif app_mode == "Today's timetable":
        main_3()
    elif app_mode == "Clashes":
        main_4()