""""
Postgres Database Connection Class. This class should be used in production. Set "DEV_MODE=False" as an environmental variable.
"""

import os
import threading
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

import psycopg2 as pg
from dotenv import load_dotenv
from fastapi import HTTPException
from starlette.status import (
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_422_UNPROCESSABLE_ENTITY,
)

load_dotenv()
try:
    if (os.getenv("POSTGRES_URI") is not None
    ):
        POSTGRES_URI = os.getenv("POSTGRES_URI")
        POSTGRES_SSL = os.getenv("POSTGRES_SSL") #set to 'require' if connecting to an online database.
    else:
        POSTGRES_URI = None
        POSTGRES_SSL = None
except KeyError as e:
    POSTGRES_URI = None


class PostgresAccess:
    """Class handling Remote Postgres connection and writes. Change POSTGRES_URI, if migrating database to a new location."""

    def __init__(self):
        try:
            # Connect to an existing database
            connection = pg.connect(POSTGRES_URI, sslmode=POSTGRES_SSL)

            # Create a cursor to perform database operations
            cursor = connection.cursor()
            # Print PostgreSQL details
            print("PostgreSQL server information")
            print(connection.get_dsn_parameters(), "\n")
            # Executing a SQL query
            cursor.execute("SELECT version();")
            # Fetch result
            record = cursor.fetchone()
            print("You are connected to - ", record, "\n")

        except (Exception, pg.OperationalError) as error:
            print("Error while connecting to PostgreSQL:", error)

        try:
            self.expiration_limit = int(os.getenv("FASTAPI_AUTH_AUTOMATIC_EXPIRATION"))
        except KeyError:
            self.expiration_limit = 15

        self.init_db()

    def init_db(self):
        """
        The init_db function creates a new database if one does not exist.
        It also migrates the old user_database to the new format, and adds columns for email, password, and username.

        Args:
            self: Access variables that belong to the class

        Returns:
            The connection to the database
        """
        try:
            connection = pg.connect(POSTGRES_URI, sslmode=POSTGRES_SSL)
            c = connection.cursor()
            # Create database
            c.execute(
                """
            CREATE TABLE IF NOT EXISTS user_database (
                id INTEGER PRIMARY KEY,
                latest_query_date TEXT,
                total_queries INTEGER)
            """
            )
            connection.commit()
            # Migration: Add User username
            try:
                c.execute(
                    "ALTER TABLE user_database ADD COLUMN IF NOT EXISTS username TEXT"
                )
                c.execute(
                    "ALTER TABLE user_database ADD COLUMN IF NOT EXISTS email TEXT"
                )
                c.execute(
                    "ALTER TABLE user_database ADD COLUMN IF NOT EXISTS password TEXT"
                )
                connection.commit()
            except pg.OperationalError as e:
                pass
        except pg.OperationalError as e:
            print(e)
            # pass  # Column already exist

    def create_key(self, username, email, password) -> dict:
        """
        The create_key function creates a new User for the user.
        It takes in the username, email, password and never_expire as parameters.
        If there is already an existing user with that username or email it will return an error message to the client.
        Otherwise it will create a new User for that user and insert them into the database.

        Args:
            self: Access variables that belongs to the class
            username: Check if the username is already in use
            email: Check if the email is already in use
            password: Store the password in the database

        Returns:
            The user_id
        """
        user_id = str(uuid.uuid4())

        connection = pg.connect(POSTGRES_URI, sslmode=POSTGRES_SSL)
        c = connection.cursor()
        c.execute(
            """SELECT username, email
                   FROM user_database
                   WHERE username=%s OR email=%s""",
            (username, email),
        )
        result = c.fetchone()
        if result:
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail="This user already exists in the database. Please choose another userusername or password.",
            )
        else:
            c.execute(
                """
                    INSERT INTO user_database
                    (user_id, latest_query_date, total_queries, username, email, password)
                    VALUES(%s, %s, %s, %s, %s, %s)
                """,
                (
                    user_id,
                    (
                        datetime.utcnow() + timedelta(days=self.expiration_limit)
                    ).isoformat(timespec="seconds"),
                    0,
                    username,
                    email,
                    password,
                ),
            )
            connection.commit()

        return {"api-key": user_id}

    def renew_key(self, user_id: str, new_expiration_date: str) -> Optional[str]:
        """
        The renew_key function takes an User and a new expiration date.
        If the User is not found, it raises a 404 error.
        Otherwise, it updates the expiration date of the User to be that specified by new_expiration_date (or 15 days from now if no argument is given).
        It returns a string containing information about what happened.

        Args:
            self: Access the class attributes
            user_id:str: Check if the User is valid
            new_expiration_date:str: Set the new expiration date

        Returns:
            A string

        """
        connection = pg.connect(POSTGRES_URI, sslmode=POSTGRES_SSL)
        c = connection.cursor()

        # We run the query like check_key but will use the response differently
        c.execute(
            """
            SELECT is_active, total_queries, expiration_date, never_expire
            FROM user_database
            WHERE user_id = %s""",
            (user_id,),
        )

        response = c.fetchone()

        # User not found
        if not response:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND, detail="User not found"
            )

        response_lines = []

        # Previously revoked key. Issue a text warning and reactivate it.
        if response[0] == 0:
            response_lines.append("This User was revoked and has been reactivated.")

            # Without an expiration date, we set it here
        if not new_expiration_date:
            parsed_expiration_date = (
                datetime.utcnow() + timedelta(days=self.expiration_limit)
            ).isoformat(timespec="seconds")

        else:
            try:
                # We parse and re-write to the right timespec
                parsed_expiration_date = datetime.fromisoformat(
                    new_expiration_date
                ).isoformat(timespec="seconds")
            except ValueError as exc:
                raise HTTPException(
                    status_code=HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="The expiration date could not be parsed. \
                            Please use ISO 8601.",
                ) from exc

        c.execute(
            """
            UPDATE user_database
            SET expiration_date = %s, is_active = 1
            WHERE user_id = %s
            """,
            (
                parsed_expiration_date,
                user_id,
            ),
        )

        connection.commit()

        response_lines.append(
            f"The new expiration date for the User is {parsed_expiration_date}"
        )

        return " ".join(response_lines)

    def revoke_key(self, user_id: str):
        """
        The revoke_key function revokes an User.

        Args:
            self: Access the class attributes and methods
            user_id:str: Specify the User to revoke

        Returns:
            None

        """
        connection = pg.connect(POSTGRES_URI, sslmode=POSTGRES_SSL)
        c = connection.cursor()

        c.execute(
            """
            UPDATE user_database
            SET is_active = 0
            WHERE user_id = %s
            """,
            (user_id,),
        )

        connection.commit()

    def check_key(self, user_id: str) -> bool:
        """
        The check_key function checks if the User is valid.
        It returns True if it is, False otherwise.


        Args:
            self: Access the class attributes
            user_id:str: Fetch the user_id from the database

        Returns:
            True if the User is valid, false otherwise
        """
        connection = pg.connect(POSTGRES_URI, sslmode=POSTGRES_SSL)
        c = connection.cursor()

        c.execute(
            """
            SELECT is_active, total_queries, expiration_date, never_expire
            FROM user_database
            WHERE user_id = %s""",
            (user_id,),
        )

        response = c.fetchone()

        if (
            # Cannot fetch a row
            not response
            # Inactive
            or response[0] != 1
            # Expired key
            or (
                (not response[3])
                and (datetime.fromisoformat(response[2]) < datetime.utcnow())
            )
        ):
            # The key is not valid
            return False
        else:
            # The key is valid

            # We run the logging in a separate thread as writing takes some time
            threading.Thread(
                target=self._update_usage,
                args=(
                    user_id,
                    response[1],
                ),
            ).start()

            # We return directly
            return True

    def _update_usage(self, user_id: str, usage_count: int):
        connection = pg.connect(POSTGRES_URI, sslmode=POSTGRES_SSL)
        c = connection.cursor()

        # If we get there, this means it’s an active User that’s in the database.\
        #   We update the table.
        c.execute(
            """
            UPDATE user_database
            SET total_queries = %s, latest_query_date = %s
            WHERE user_id = %s
            """,
            (
                usage_count + 1,
                datetime.utcnow().isoformat(timespec="seconds"),
                user_id,
            ),
        )

        connection.commit()

    def get_usage_stats(self) -> List[Tuple[str, bool, bool, str, str, int]]:
        """
        The get_usage_stats function returns a list of tuples with values being user_id, is_active, expiration_date, \
        latest_query_date, and total_queries. The function will return the usage stats for all Users in the database.
        
        Args:
            self: Refer to the object of the class
        
        Returns:
            A list of tuples with values being user_id, is_active, expiration_date, latest_query_date, and total
        """
        connection = pg.connect(POSTGRES_URI, sslmode=POSTGRES_SSL)
        c = connection.cursor()

        c.execute(
            """
            SELECT user_id, is_active, never_expire, expiration_date, \
                latest_query_date, total_queries, username, email
            FROM user_database
            ORDER BY latest_query_date DESC
            """,
        )
        response = c.fetchall()

        return response


postgres_access = PostgresAccess()
