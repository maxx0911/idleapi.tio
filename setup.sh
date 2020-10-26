#!/bin/bash

if [ $(whoami) != "postgres" ]; then
    echo "This script must be run as the postgres user!"
    echo "Use the following: \"sudo -u postgres setup.sh\""
    exit 1
fi

echo "This script will create a new PostgreSQL user as well as a database."
echo "Please make sure to read the script in order to make sure nothing is out of the ordinary."
echo "If you cannot read bash scripts, please ask a friend to verify."

read -p "Press any button to continue."

read -p "What should the new user's name be? " DB_USERNAME
# we check if that user already exists
if [ $(psql postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USERNAME'") -eq 1 ]; then
    echo "Error: User $DB_USERNAME already exists."
fi

read -p "What should the new database's name be? " DB_DATABASE
# we check if that database already exists
if [ $(psql postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_DATABASE'") -eq 1 ]; then
    echo "Error: Database $DB_DATABASE already exists."
fi

echo "Username $DB_USERNAME"
echo "Database name $DB_DATABASE"
read -p "Is this information correct? (Y/n) " -n 1 -r
if [[ $REPLY =~ ^[Yy]$ ]]; then
    $(createuser -e -l $DB_USERNAME)
    $(createdb -e -O $DB_USERNAME $DB_DATABSAE)
fi

echo "Successfully created database $DB_DATABASE with owner $DB_USERNAME"
echo "It is advised to change this user's password by using \"sudo -u $DB_USERNAME psql\", followed by \"\\password\". You can then exit the psql shell by typing \"\\q.\""
read -p "Press any button to exit."
exit 0