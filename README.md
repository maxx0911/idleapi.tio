# idleAPI.tio
A discord bot that interacts with the Travitia API, specifically the IdleRPG portion.  
This bot is intended for selhosting, and as a demonstration what the API is capable of.

# Installing 
## Prerequisites
To install this code, you need to make sure you need the following prerequisites:
- [Python 3.6+](https://www.python.org/downloads/) installed on your system
- [PostgreSQL 10+](https://www.postgresql.org/download/) installed on your system
  - A database that follows the [schema](./schema.sql)
  - A database user with a password
- [Redis 5+](https://redis.io/download) installed on your system
- A bot application created on [the Discord developer page](https://discordapp.com/developers/applications)

Python is used for interpreting the code so everything runs as it should. Without Python, you cannot run this bot.  
PostgreSQL is the database management system. It's used to store data, namely protected items.  
Redis is an in-memory dictionary-like storage system. It's used to store cooldowns.  

Beside these prerequisites, you need to install some Python packages using pip. The list of required packages can be found in [this file](./requirements.txt).

## Configuration
First of all, clone this repository to your local computer or remote server.
```sh
git clone https://github.com/maxx0911/idleapi.tio.git
cd idleapi.tio
```

Before this bot can work, you need to enter several config values. You can do so by renaming [config-example.py](./config-example.py) to `config.py` and filling in the fields.  
Here is a brief explanation on what these are used for:
- `command_prefix`: This is the prefix used for bot commands. Entering `"< "` will result in commands being run like `< ping`. This can be any string, or a list of strings.
- `token`: Your bot application's token. This is used to connect your bot to discord. You can find it on the [Discord developer page](https://discordapp.com/developers/applications) of your application. Navigate to "Bot" on the left side, and a button to copy the token should appear. **NEVER SHARE THIS WITH ANYONE!**
- `api_token`: The access token provided to you by Travitia. This is used for authorizing requests to the API. Without it, all requests will return an error 403. You can receive one on their [Discord server](https://discord.gg/8TBJbnP).
- `postgres_login`: Your database credentials used to connect to your database. Without them, you cannot store item data.
  - `database`: The name of the database you want to use.
  - `user`: The username/role name of the user you want to connect as.
  - `password`: The password you gave said user/role.
  - `host`: The host address. In most cases, this will be `127.0.0.1`, meaning the database is on your local system.
- `bans`: A list of user IDs that should not be able to access the bot. If a user's ID is in this list, commands they use will be ignored.

Beside the configuration, there is additional config in [the context class](./classes/context.py). Update the emoji IDs in order to allow the use 

## Running the bot
If everything is set up correctly, you can use `python3 ./main.py` to run the bot. In case of errors, check the created `error.log`. If that doesn't help, do not be afraid to [contact me](https://discord.com/users/262133866062413825).

## From the top
If you have already completed a step from previous experience, you can skip it.

1. Install Python
2. Install PostgreSQL
   1. Create a new user named idleapi (or other) with a password
   2. Create a new database named idleapi (or other)
3. Install Redis
4. clone this repository
5. Create a new Discord application and make it into a bot
6. rename `config-example.py` to `config.py` and fill in the fields with your values
7. run main.py