import ssl
import socket
from threading import Thread


class ProxyClient(Thread):
    def __init__(self, ip, port):
        Thread.__init__(self)
        self.ip = ip
        self.port = port
        self.proxysocket = None 

        # Create connection to target server
        print(f"[+] Proxy client initialized for {self.ip}:{self.port}")
        if self.port == 443:
            print("[+] Initializing SSL context")
            self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS)
            #self.ssl_context.load_cert_chain(certfile="./server.crt",keyfile="./server.key")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket = self.ssl_context.wrap_socket(self.socket, server_hostname="localhost")
            self.socket.connect((self.ip, self.port))
        else:
            print("[+] Initializing normal socket")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.ip, self.port))

    def run(self):
        while True:
            # Waiting response from target server
            recv_data = self.socket.recv(1024)
            if recv_data:
                # Send response to proxy server and it will forward to client
                print(f"\n[+] Server response:\n{'='*20}\n {recv_data}\n {'='*20}\n")
                self.proxysocket.sendall(recv_data)
            else:
                self.socket.close()
                break

def UserThread(client, port, to_host, to_port):
    # Once we have a connection, we can start proxying in a new thread
    client_proxy = ProxyClient(to_host, to_port)

    # The proxy server will communicates with the proxy client
    client_proxy.proxysocket = client
    client_proxy.start()

    while True:
        # When the proxy server receives user request data 
        request = client.recv(2048)
        # replace http header origin with host address
        if request:
            if to_port == 80 or to_port == 443:
                request = request.replace(bytes(f"Host: {socket.getfqdn('127.0.0.1')}:{port}", 'utf-8'), 
                                          bytes(f'Host: {to_host}', 'utf-8') )

            print(f"[+] The client is send:\n{'='*20}\n {request}\n {'='*20}\n")
            # Send the data to the target server though the proxy client
            client_proxy.socket.sendall(request)
        else:
            # Close the connection
            client.close()

class Proxy(Thread):
    def __init__(self, host, port, to_host, to_port):
        Thread.__init__(self)
        # Proxy server
        self.host = host
        self.port = port

        # Proxy client
        self.to_host = to_host
        self.to_port = to_port

        self.max_connections = 5

    def run(self):
        print(f"Proxy listening on {self.host}:{self.port}")

        # Create a socket (SOCK_STREAM means a TCP socket)
        serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Reuse the socket
        serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Bind the socket 'localhost' to the port
        serversocket.bind((self.host, self.port))
        serversocket.listen(self.max_connections)

        while True:
            # Accept connections from outside
            (client, (ip,port)) = serversocket.accept()
            print("[+] {ip}:{port} is connected to proxy-server".format(ip=ip, port=port))
            # Start new thread for each client
            Thread(target=UserThread, args=(client, self.port, self.to_host, self.to_port)).start()


# ::: About sockets  :::
# Sockets are like a ping-pong game, you send data to the server and the server sends data back to you. 
# In each response someone wait for the other to send data.
# |
# |\
# |  -> Socket server:
# |         *A server bind to localhost:<someport> and wait connections from the client.
# |          When a connection is established, the server will forward data.
# |\
#    -> Socket client
#           *A client connect to localhost:<someport> and send data to the server waiting for a response.


# ::: Basic proxy server
# The user can connect to the proxy server
# User -> Proxy server -> Proxy client -> Server __    
#                                                  |
# User <- Proxy server <- Proxy client <- Server <-/
if __name__ == "__main__":
    server = Proxy("", 8081, "www.youtube.com", 443)
    server.start()