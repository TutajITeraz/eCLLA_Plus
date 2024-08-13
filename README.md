# Installing database engine

## For manjaro linux:
```
    sudo pacman -Syu
    sudo pacman -S mariadb
```
## For ubuntu linux:
```
    sudo apt update
    sudo apt install mariadb-server
    sudo mysql_secure_installation
```
## Configuring database engine:
```
    sudo mariadb-install-db --user=mysql --basedir=/usr --datadir=/var/lib/mysql
    sudo systemctl enable mariadb --now

    sudo mysql -u root
        CREATE DATABASE ritus;
        CREATE USER ritus_user@localhost IDENTIFIED BY 'SoftCatEarZ1563!';


        GRANT ALL PRIVILEGES ON ritus.* TO ritus_user@localhost ;

        FLUSH PRIVILEGES;
        exit
```


# Configuration:
Edit the ritus_indexer/settings.py:

Add your host to the variables:
```
ALLOWED_HOSTS
CSRF_TRUSTED_ORIGINS
CORS_ALLOWED_ORIGINS
```
Edit username and password for the database:
```
DATABASES
```
## example DATABASES config:
```
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
		'CONN_MAX_AGE': 0,
        'NAME': 'ritus',
        'USER': 'ritus_user',
        'PASSWORD': 'SoftCatEarZ1563!',
        'HOST': '127.0.0.1',
    }
}
```


# Installation

## Following commands must be executed in the project directory!
```

#Check pip version:
    pip --version
#If pip is not installed, install it:
#Manjaro linux command:
    pacman -Syu python-pip
#Ubuntu linux command:
    sudo apt install Python3-pip 

#Install pkg-config (Ubuntu):
    sudo apt install pkg-config
#Install pkg-config (Manjaro):
    sudo pamac install pkg-config


python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

#For a fresh install (no database migration) execute the following operations:
rm indexerapp/migrations/*
python manage.py makemigrations indexerapp
python manage.py migrate
python manage.py createsuperuser #This creates first user that you can use for log in

#For importing existing .sql file (moving database), change filename/path if needed and execute:
sudo mysql -u root -h localhost -p ritus < ~/Downloads/reboldho_indexer.sql


#Setup static files (may be served using nginex apache or other server):
python manage.py collectstatic

```

## To use dubo (SQL assistant):

```
export DUBO_API_KEY="pk.bb63cda35d47463fb858192bee22510f"
```

## Run server:

```
python manage.py runserver 0.0.0.0:8080
```



### Every time you want to run the project, you have to activate the environment first:
	source .venv/bin/activate
### And then run the mysql server
    sudo systemctl enable mariadb --now
### And finaly run the indexer django server:
	python manage.py runserver 0.0.0.0:8080

