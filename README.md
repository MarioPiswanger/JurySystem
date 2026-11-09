# 🐳 Dockerized Web-Framework for IoT 🐳
Requires Docker compose **> 2.27**   
Select preconfigured services in docker-compose.yml by comment or uncomment includes.
##  🐧🐧🚀 Installing - Linux ( production environment )🚀️🐧🐧
⭐ Install git,wget and unzip (can be skip if already installed)
```shell
    sudo apt update 
    sudo apt install -y git
    sudo apt install -y wget 
    sudo apt install -y unzip 
    sudo rm -rf /var/lib/apt/lists/*  
```
⭐ Choose directory or make a new one with appropriate permissions for writing and executing.      
Clone repository adds folder **Dockerized-Web-Framework-for-IoT**.      
⭐ Clone repository
```shell
    git clone https://github.com/fkrenn12/Dockerized-Web-Framework-for-IoT.git  
    chmod +x ./Dockerized-Web-Framework-for-IoT/*.sh 
    chmod o+w ./Dockerized-Web-Framework-for-IoT/.node-red
    rm -rf ./Dockerized-Web-Framework-for-IoT/*.ps1  
```

## 🔳 🔳 🚀 Installing - Windows ( developing environment )🚀️🔳 🔳   
  
⭐ Open prefered IDE (pycharm, vscode) and clone https://github.com/fkrenn12/Dockerized-Web-Framework-for-IoT.git  
⭐ or manual downloading the code or using the commands in Powershell    
In **Windows Powershell** ( not cmd !! )  use following commands.   
```powershell
    Remove-Item -Path ./master.zip
    Invoke-WebRequest  https://github.com/fkrenn12/Dockerized-Web-Framework-for-IoT/archive/master.zip -OutFile ./master.zip
    Expand-Archive -Path ./master.zip -DestinationPath ./master
    Remove-Item -Path ./master.zip
    Copy-Item -Path ./master/Dockerized-Web-Framework-for-IoT-master ./Dockerized-Web-Framework-for-IoT -Recurse -Force
    Remove-Item -Path ./master -Recurse -Force
```  
It will create a new folder: Dockerized-Web-Framework-for-IoT  
## Editing defaults  
⭐ Edit .env.prod (DOMAIN must be set) and docker-composer.yml (choose your services)  
⭐ Execute x-rebuild_and_start.local.development.ps1 on windows development environment
⭐ Execute x-rebuild_and_start.production.sh on linux production environment

# Selectable Services
## *Applications and Web*
### 👉 APP (Running python scripts in container)
### 👉 Flet (Framework for web application in pure Python)
<!---
### 👉 API-FASTAPI-PURE-SQL
-->
### 👉 API-FASTAPI-SQLMODEL  (fastapi using sqlmodel) 


### 👉 NGINX-PHP (HTML and PHP Webserver)
https://web.localhost/index.php

## Öffentliche Event-Anmeldung und Bilder
Die öffentliche Startseite der Jury-App zeigt unter „Anmeldung zu Events“ alle
zukünftigen und laufenden Events nach Datum sortiert. Für eine Anmeldung wählt
der Teilnehmer ein Event, erstellt ein Konto mit Teilnehmerdaten und wird
automatisch einer passenden Wettkampfklasse zugeordnet. Der Login ist separat
unter `/login` erreichbar.

Unter „Bilder“ wählen Besucher ein Event und geben eine Startnummer ein, um
passende Fotos anzusehen. Hosts und Administratoren können dort JPEG- und
PNG-Bilder einem Event zuordnen und hochladen; die Startnummern werden vom
`bib-ocr`-Dienst erkannt.
Die Bilddateien und Zuordnungen liegen im persistenten Docker-Volume
`api-image-uploads`.
## *Database*
### 👉 MariaDB + Phpmyadmin 
https://phpmyadmin.localhost

| Target access | Subdomain  | Username | Password | Database |
| ------------- | ---------- | -------- | -------- | -------- |
| mariadb       | phpmyadmin | root     | example  | ALL      |
| mariadb       | phpmyadmin | foo      | foo      | foo      |


<!---
### 👉 RESTful API for mysql/mariadb
https://github.com/krink-code/db-api?tab=readme-ov-file  
http://127.0.0.1:8980/api/<db>/<table>/  
GET    /     # Show status  
GET    /api                          # Show databases  
GET    /api/<db>                     # Show database tables  
GET    /api/<db>/<table>             # Show database table fields    
GET    /api/<db>/<table>?query=true  # List rows of table  
POST   /api/<db>/<table>             # Create a new row  
PUT    /api/<db>/<table>             # Replace existing row with new row  

GET    /api/<db>/<table>/:id         # Retrieve a row by primary key
PATCH  /api/<db>/<table>/:id         # Update row element by primary key
DELETE /api/<db>/<table>/:id         # Delete a row by primary key

GET    /api/<db>/<table>/count       # Count number of rows in a table

POST   /api                          # Content-Type: text/sql
-->
## *Manage Docker*
### 👉 Portainer (Manage and administrate Docker)
https://portainer.localhost  
At first start, **Portainer** will request to set up an initial administrator.   
## *Tools*
### 👉 Traefik (HTTP-Reverse Proxy and LoadBalancer)
https://traefik.localhost  

| Target access | Subdomain | Default Username | Default Password |
| ------------- | --------- | ---------------- | ---------------- |
| traefik       | traefik   | admin            | admin            |

You will find instructions in file .env to change user and password.    

### System requirements  
Requires Docker compose > 2.27 (check in terminal: docker compose version)

### /mariadb/certs/./generate_certificates.sh

https://linuxize.com/post/how-to-setup-passwordless-ssh-login/