import os
import socket
import threading

class ServeOn:
    def __init__(self, host='127.0.0.1', tcp_port=12345, udp_port=12346):
        self.BUFFER_SIZE = 312
        self.tcp_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_server_socket.bind((host, tcp_port))
        self.tcp_server_socket.listen(5)
        print(f"[*] TCP Server listening as {host}:{tcp_port}")

        self.udp_server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_server_socket.bind((host, udp_port))
        print(f"[*] UDP Server listening as {host}:{udp_port}")

        self.tcp_client_sockets = []  # Lista de conexões TCP ativas
        self.file_path = "/home/vitor/Downloads/picapaubiruta.mp4"

    def broadcast_tcp(self, message):
        # Envia mensagem para todos os clientes TCP conectados
        message = message.encode() if isinstance(message, str) else message
        for client_socket in self.tcp_client_sockets:
            try:
                client_socket.sendall(message)
            except Exception as e:
                print(f"[!] Error sending to {client_socket.getpeername()}: {e}")

    def send_video_tcp(self, client_socket):
        print("[*] Sending File ...")
        try:
            with open(self.file_path, "rb") as f:
                while True:
                    bytes_read = f.read(self.BUFFER_SIZE)
                    if not bytes_read:
                        break
                    client_socket.sendall(bytes_read)
            print(f"[*] File '{self.file_path}' sent successfully.")
        except Exception as e:
            print(f"[!] Error sending file '{self.file_path}': {e}")

    def get_file_size(self):
        try:
            size = os.path.getsize(self.file_path)
            return size
        except FileNotFoundError:
            print(f"[!] File '{self.file_path}' not found.")
            return -1
        
        
    def handle_client(self, tcp_socket, udp_socket, client_address,client_address_udp):
        try:
            self.tcp_client_sockets.append(tcp_socket)  # Adiciona a nova conexão à lista de clientes TCP ativos

            while True:
    
                if self.get_file_size() == -1:
                    m = f'File {self.file_path} not found.'
                    udp_socket.sendto(m.encode(), client_address_udp)
                    break
                
                m = f'{self.file_path} {self.get_file_size()} '
                udp_socket.sendto(m.encode(), client_address_udp)


                msg_tcp = tcp_socket.recv(self.BUFFER_SIZE)
                print(f"\t[Received TCP from {client_address}]: {msg_tcp.decode()}")

                # Enviar arquivo apenas se receber a mensagem correta via TCP
                if msg_tcp.decode().startswith("ClientThread"):
                    self.send_video_tcp(tcp_socket)
                    break

        except Exception as e:
            print(f"[!] Error with {client_address} (TCP): {e}")
        finally:
            self.tcp_client_sockets.remove(tcp_socket)  # Remove a conexão da lista
            tcp_socket.close()
            print(f"[*] Closed TCP connection with {client_address}")

    def start(self):
        print("[*] Server is running...")
        try:
            while True:
                try:
                    tcp, client_address = self.tcp_server_socket.accept()
                    print(f"[+] Accepted TCP connection from {client_address}")
                    udp, client_address_udp = self.udp_server_socket.recvfrom(self.BUFFER_SIZE)
                    print(f"[+] Accepted UDP connection from {client_address_udp}")
                    client_thread = threading.Thread(target=self.handle_client, args=(tcp, self.udp_server_socket, client_address,client_address_udp))
                    client_thread.start()
                except Exception as e:
                    print(f"[!] Error accepting TCP connections: {e}")
        except KeyboardInterrupt:
            print("\n[*] Shutting down TCP server.")
        finally:
            self.tcp_server_socket.close()
            self.udp_server_socket.close()
            print("[*] Server sockets closed.")

if __name__ == '__main__':
    server = ServeOn(host='127.0.0.1', tcp_port=12345, udp_port=12346)
    server.start()
