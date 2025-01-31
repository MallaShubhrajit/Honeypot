import socket
import paramiko
import threading
import logging
from logging.handlers import RotatingFileHandler

# SSH Banner
SSH_BANNER = "SSH-2.0-MySSHServer_1.0"
host_key = paramiko.RSAKey(filename='server.key')

# Logging Setup
logging_format = logging.Formatter('%(asctime)s - %(message)s')

connection_logger = logging.getLogger('connection_logger')
connection_logger.setLevel(logging.INFO)
connection_handler = RotatingFileHandler('connections.log', maxBytes=2000, backupCount=5)
connection_handler.setFormatter(logging_format)
connection_logger.addHandler(connection_handler)

credentials_logger = logging.getLogger('credentials_logger')
credentials_logger.setLevel(logging.INFO)
credentials_handler = RotatingFileHandler('credentials.log', maxBytes=2000, backupCount=5)
credentials_handler.setFormatter(logging_format)
credentials_logger.addHandler(credentials_handler)

# Emulated Shell Function
def emulated_shell(channel, client_ip):
    channel.send(b'corporate_jumpbox2$ ')
    command = b""
    while True:
        char = channel.recv(1)
        if not char:
            break
        channel.send(char)
        command += char
        if char == b'\r':  # Command completed
            command = command.strip()
            if command == b'exit':
                channel.send(b'\nGoodbye!\n')
                break
            elif command == b'pwd':
                response = b'\n/usr/local\n'
            elif command == b'whoami':
                response = b'\ncorpuser1\n'
            elif command == b'ls':
                response = b'\njumpbox1.conf\n'
            else:
                response = b'\nInvalid command\n'
            channel.send(response + b'corporate_jumpbox2$ ')
            command = b""

    channel.close()

# SSH Server Class
class SSHServer(paramiko.ServerInterface):
    def __init__(self, client_ip, input_username, input_password):
        self.event = threading.Event()
        self.client_ip = client_ip
        self.input_username = input_username
        self.input_password = input_password

    def check_channel_request(self, kind, chanid):
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def get_allowed_auths(self, username):
        return "password"

    def check_auth_password(self, username, password):
        credentials_logger.info(f"{self.client_ip} attempted login: {username}/{password}")
        if username == self.input_username and password == self.input_password:
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def check_channel_shell_request(self, channel):
        self.event.set()
        return True

# Client Handler
def client_handle(client, addr, username, password):
    client_ip = addr[0]
    connection_logger.info(f"Connection from {client_ip}")
    try:
        transport = paramiko.Transport(client)
        transport.local_version = SSH_BANNER
        server = SSHServer(client_ip, username, password)
        transport.add_server_key(host_key)
        transport.start_server(server=server)

        channel = transport.accept(20)
        if channel is None:
            return
        channel.send("Welcome to the fake SSH server!\n".encode())
        emulated_shell(channel, client_ip)

    except Exception as e:
        connection_logger.error(f"Error with client {client_ip}: {e}")
    finally:
        try:
            client.close()
        except Exception as e:
            connection_logger.error(f"Error closing connection: {e}")

# Honeypot Function
def honeypot(address, port, username, password):
    socks = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socks.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    socks.bind((address, port))
    socks.listen(5)
    print(f"SSH honeypot is running on {address}:{port}")

    while True:
        try:
            client, addr = socks.accept()
            threading.Thread(target=client_handle, args=(client, addr, username, password), daemon=True).start()
        except Exception as e:
            connection_logger.error(f"Error in honeypot: {e}")

# Run Honeypot
honeypot('127.0.0.1', 2223, 'username', 'password')
