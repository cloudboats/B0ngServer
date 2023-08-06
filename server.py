import socket, threading, sys, os, time, platform, psutil, getpass, random, json, hashlib
from pyfiglet import Figlet

config_file =  "config.json"
banners_file = "banners.txt"
logins_file = "logins.txt"

def load_config():
    with open(config_file, "r") as file:
        config_data = json.load(file)
    return config_data
config = load_config()

# Server configuration
if config["HOST"] == "auto":
    HOST = '127.0.0.1'
else: 
    HOST = config["HOST"]
if config["PORT"] == "auto":
    try:
        PORT = int(sys.argv[1])
    except:
        print("please supply port")
        sys.exit()
else: 
    PORT = config["PORT"]
if config["BYTERATE"] == "auto":
    byterate = 1024
else: 
    byterate = config["BYTERATE"]
if config["PROMPT"] == "auto":
    prompt = "\n!username@b0ngserver ► "
else: 
    prompt = config["PROMPT"]
if config["V_PROMPT"] == "auto":
    verify_prompt = "\nverify@b0ngserver  ► "
else:
    verify_prompt = config["V_PROMPT"]
if config["LOGIN_PROMPT"] == "auto":
    login_prompt = ["username@login ► ","password@login ► "]
else: 
    login_prompt = config["LOGIN_PROMPT"]
if config["PREFIX"] == "auto":
    prefix = "."
else: 
    if len(config["PREFIX"]) > 1:
        print("Prefix > len 1")
        sys.exit()
    else:
        prefix = config["PREFIX"]

clients = []
clients_formatted = []
online_users = []

def encrypt_data(data):
    return hashlib.sha256(data.encode('utf-8')).hexdigest()

def setup_banners():
    global banners, banner_names
    banners_raw = []
    banner_names = []
    banners = []
    with open(banners_file, 'r') as file:
        file_contents = file.read()
    banner_list = file_contents.split(':::end:::')
    for banner in banner_list:
        start_index = banner.find(":::") + 3
        end_index = banner.find(":::", start_index)
        if start_index == -1 or end_index == -1:
            pass
        banner_names.append(banner[start_index:end_index])
        if prefix == "":
            banner = banner.replace("%", " ")
        else:
            banner = banner.replace("%", prefix)
        banner = banner.replace(f":::{banner[start_index:end_index]}:::","")
        banner = banner.replace("!hostname",f"{getpass.getuser()}@{socket.gethostname()}")
        banner = banner.replace("!os", platform.system())
        banner = banner.replace("!cpu", platform.processor())
        banner = banner.replace("!memory", f"{str(round(((psutil.virtual_memory()).total/1000000000),2))} GB")
        banners.append(banner)

def send_prompt(prompt_text,username, client_socket):
    if username == "":
        client_socket.send((prompt_text).encode('utf-8'))
    else:
        client_socket.send(((prompt_text).replace("!username",username)).encode('utf-8'))

def send_data(data, client_socket):
    client_socket.send((str(data)).encode('utf-8'))

def set_client_title(title, client_socket):
    client_socket.send(f"\033]2;{title}\007".encode('utf-8'))

def clear_connection(client_socket):
    client_socket.send("\033[2J".encode('utf-8'))

def get_input(client_socket):
    return (client_socket.recv(byterate).decode('utf-8')).strip()

def verify(client_socket):
    while True:
        num1 = random.randint(1, 10)
        num2 = random.randint(1, 10)
        operator = random.choice(['+', '-', '*'])
        if operator == '+':
            result = num1 + num2
        elif operator == '-':
            result = num1 - num2
        else:
            result = num1 * num2
        captcha_raw = f"{num1} {operator} {num2}"
        figlet = Figlet(font='standard')
        for line in figlet.renderText(captcha_raw).splitlines():
            send_data(f"{line}\n", client_socket)
        send_prompt("\nverify@b0ngserver ► ","",client_socket)
        data = get_input(client_socket)
        if not data:
            pass
        if data == str(result):
            return True
        else: 
            return False

def getuptime():
    global start_time
    total_seconds = time.time() - start_time
    days = round((total_seconds // 86400))
    hours = round(((total_seconds // 3600) % 24))
    minutes = round(((total_seconds // 60) % 60))
    seconds = round((total_seconds % 60),2)
    return f"{days}:{hours}:{minutes}:{seconds}"

def send_banner(banner, client_socket):
    global banners, banner_names
    try:
        banner_to_print = banners[banner_names.index(banner)]
        banner_lines = banner_to_print.split("\n")
        for line in banner_lines:
            line = line.replace("!uptime", getuptime())
            with open(logins_file, 'r') as fp:
                total_users = len(fp.readlines())
            line = line.replace("!clients", f"{len(clients)}/{total_users}")
            send_data(f"{line}\n", client_socket)
    except Exception as e: 
        print(e)

def broadcast_data(data, sender_socket):
    for client_socket in clients:
        if client_socket == sender_socket:
            client_socket.send((f"{data}").encode('utf-8'))
        else:
            client_socket.send((f"\n{data}").encode('utf-8'))
            client_socket.send(prompt.encode('utf-8'))

def disconnect_client(username, client_socket):
    if username == "":
        pass
    else:
        online_users.remove(username)
    clients.remove(client_socket)
    client_socket.close()

def process_data(data, usertype, username, client_socket, client_address):
    if data == "":
        send_data("",client_socket)
    elif " " in data:
        command = data.split(" ")[0]
        arg = data.replace(f"{command} ","")
    else:
        arg = ""
        command = data

    if command == f"{prefix}killserver" and usertype == "admin":
        if verify(client_socket):
            clear_connection(client_socket)
            print(f"Client killing server: {client_address[0]}:{client_address[1]}")
            send_data("Killing Server\n", client_socket)
            print(f"\nServer Killed.")
            os._exit(0)
        else:
            print(f"Client failed to kill server: {client_address[0]}:{client_address[1]}")
            send_data("Captcha Failed\n", client_socket)
            return
    elif command == f"{prefix}broadcast" and usertype == "admin":
        if arg == "":
            send_data(f"Usage: {prefix}broadcast <data>",client_socket)
        else:
            broadcast_data(arg, client_socket)
    elif command == f"{prefix}serverinfo" and usertype != "admin":
        send_banner("user_serverinfo_banner", client_socket)
    elif command == f"{prefix}serverinfo" and usertype == "admin":
        send_banner("admin_serverinfo_banner", client_socket)
    elif command == f"{prefix}showusers" and usertype == "admin":
        with open(logins_file, 'r') as file:
            users = (file.read()).splitlines()
            for line in users:
                usertype, username, password = line.split(":")
                if len(users) == 1:
                    if username in online_users:
                        send_data(f"\n-  online - - {usertype}:{username}:{password}",client_socket)
                    else:
                        send_data(f"\n- offline - - {usertype}:{username}:{password}",client_socket)
                    pass
                elif username in online_users:
                    if users.index(line) == 0:
                        # ╭─────╮
                        send_data(f"\n┌  online ┐ ┌ {usertype}:{username}:{password}",client_socket)
                    elif users.index(line) == len(users) - 1:
                        # ╰─────╯
                        send_data(f"\n└  online ┘ └ {usertype}:{username}:{password}",client_socket)
                    else:
                        send_data(f"\n│  online │ │ {usertype}:{username}:{password}",client_socket)
                else:
                    if users.index(line) == 0:
                        # ╭─────╮
                        send_data(f"\n┌ offline ┐ ┌ {usertype}:{username}:{password}",client_socket)
                    elif users.index(line) == len(users) - 1:
                        # ╰─────╯
                        send_data(f"\n└ offline ┘ └ {usertype}:{username}:{password}",client_socket)
                    else:
                        send_data(f"\n│ offline │ │ {usertype}:{username}:{password}",client_socket)
    elif command == f"{prefix}adduser" and usertype == "admin":
        if arg == "":
            send_data(f"Usage: {prefix}adduser <usertype>:<username>:<passwordhash>",client_socket)
        else:
            add_usertype, add_username, add_passwordhash = arg.split(":")
            print(f"adding user: {add_usertype}:{add_username}:{add_passwordhash}")
            with open(logins_file, 'a') as db:
                db.write(f"\n{add_usertype}:{add_username}:{add_passwordhash}")
            send_data(f"User: {add_username} added to db",client_socket)
    elif command == f"{prefix}deleteuser" and usertype == "admin":
        with open(logins_file, 'r') as db:    
            lines = (db.read()).splitlines()
            for line in lines:
                usertype, username, password = line.split(":")
                if username == arg:
                    lines.remove(line)
                else: 
                    if lines.index(line) == len(lines) - 1:
                        send_data(f"invalid user: {arg}", client_socket)
                        return
                    else:
                        pass
            if verify(client_socket):
                with open(logins_file,'w') as db:
                    pass
                with open(logins_file,'w') as db:
                    for line in lines:
                        if lines.index(line) == 0:
                            db.write(f"{line}")
                        else:
                            db.write(f"\n{line}")
                send_data(f"Removed user: {arg} from db", client_socket)
            else:
                send_data(f"Failed Captcha", client_socket)      
    elif command == f"{prefix}hash" and usertype == "admin":
        if arg == "":
            send_data(f"Usage: {prefix}hash <data>",client_socket)
        else:
            send_data(encrypt_data(arg), client_socket)
    elif command == f"{prefix}exit":
        clear_connection(client_socket)
        disconnect_client(username, client_socket)
        print(f"User disconnected: {username} {client_address[0]}:{client_address[1]}")
    elif command == f"{prefix}print":
        if arg == "":
            send_data(f"Usage: {prefix}print <data>",client_socket)
        else:
            send_data(arg, client_socket)
    elif command == f"{prefix}help" and usertype != "admin":
        send_banner("help_banner", client_socket)
    elif command == f"{prefix}help" and usertype == "admin":
        send_banner("admin_help_banner", client_socket)
    elif command == f"{prefix}clear":
        clear_connection(client_socket)
        send_banner("welcome_banner", client_socket)
    else:
        send_data(f"command: {command} not found...", client_socket)

def send_login(client_socket, client_address):
    clear_connection(client_socket)
    send_banner("login_banner", client_socket)
    send_data(f"{login_prompt[0]}", client_socket)
    input_username = get_input(client_socket)
    if not input_username:
        send_data(f"\nUsername not provided\n", client_socket)
        return False
        
    with open(logins_file, 'r') as file:
        logins = file.read().splitlines()
        for login in logins:
            usertype, username, password = login.split(":")
            if input_username == username:
                send_data(f"{login_prompt[1]}", client_socket)
                input_password = get_input(client_socket)
                if encrypt_data(input_password) == password:
                    print(f"login: {usertype}:{username}:{password} address: {client_address[0]}:{client_address[1]}")
                    online_users.append(username)
                    return f"{usertype}:{username}:{password}"
                else:
                    send_data(f"\nPassword Invalid\n", client_socket)
                    return False
        send_data(f"\nUsername not found\n", client_socket)
        return False

def handle_client(client_socket, client_address):
    getuser = send_login(client_socket, client_address)
    if getuser: 
        usertype, username, password = getuser.split(":")
        set_client_title(f"User: {username} | Type: {usertype}", client_socket)
        clear_connection(client_socket)
        send_banner("welcome_banner", client_socket)
        while True:
            try:
                send_prompt(prompt,username, client_socket)
                data = get_input(client_socket)
                if not data:
                    break
                #print(f"Recived data: {data.encode('utf-8')}, from client: {client_address[0]}:{client_address[1]}")
                process_data(data, usertype, username, client_socket, client_address)
            except:
                pass

        disconnect_client(username, client_socket)    
    else:
        disconnect_client("", client_socket)      

def start_server():
    global start_time
    start_time = time.time()
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)
    print(f"Server is running and listening on {HOST}:{PORT}")
    while True:
        client_socket, client_address = server_socket.accept()
        clients.append(client_socket)
        print(f"connection: {client_address[0]}:{client_address[1]}")
        client_thread = threading.Thread(target=handle_client, args=(client_socket,client_address))
        client_thread.start()

setup_banners()
start_server()
