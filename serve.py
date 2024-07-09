import os
import socket
import threading

class ServeOn:
    def __init__(self, host='127.0.0.1', tcp_port=12345, udp_port=12346):
        self.BUFFER_SIZE = 4096
        self.tcp_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_server_socket.bind((host, tcp_port))
        self.tcp_server_socket.listen(5)
        print(f"[*] TCP Server listening as {host}:{tcp_port}")

        self.udp_server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_server_socket.bind((host, udp_port))
        print(f"[*] UDP Server listening as {host}:{udp_port}")

        self.tcp_client_sockets = []  # Lista de conexões TCP ativas
        self.udp_clients = {}  # Dicionário para armazenar conexões UDP ativas

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
        file_path = "download.mp4"
        try:
            with open(file_path, "rb") as f:
                while True:
                    bytes_read = f.read(self.BUFFER_SIZE)
                    if not bytes_read:
                        break
                    client_socket.sendall(bytes_read)
            print(f"[*] File '{file_path}' sent successfully.")
        except Exception as e:
            print(f"[!] Error sending file '{file_path}': {e}")

    def get_file_size(self,file_path):
      try:
        size = os.path.getsize(file_path)
        return size
      except FileNotFoundError:
        print(f"File '{file_path}' not found.")
        return -1
        
    def handle_client(self, tcp_socket, udp_socket, client_address):
        self.tcp_client_sockets.append(tcp_socket)  # Adiciona a nova conexão à lista de clientes TCP ativos
        
        try:
            while True:
                if udp_socket:
                    try:
                        udp_message, _ = udp_socket.recvfrom(self.BUFFER_SIZE)
                        decoded_udp_message = udp_message.decode()
                        print(f"\t[Received UDP from {client_address}]: {decoded_udp_message}")
                    except Exception as e:
                        print(f"[!] Error receiving UDP data from {client_address}: {e}")

                msg_tcp= tcp_socket.recv(self.BUFFER_SIZE)
                print(f"\t[Received TCP from {client_address}]: {msg_tcp.decode()}")

                #Enviar info
                m = f'download.mp4 {self.get_file_size("download.mp4")} '
                udp_socket.sendto(m.encode(),_)
                
                self.send_video_tcp(tcp_socket)
        except Exception as e:
            print(f"[!] Error with {client_address} (TCP): {e}")
        finally:
            self.tcp_client_sockets.remove(tcp_socket)  # Remove a conexão da lista
            tcp_socket.close()
            print(f"[*] Closed TCP connection with {client_address}")
    def start(self):
        print("[*] Server is running...")
        try:
            thread = threading.Thread(target=self.server_thread)
            thread.start()
            thread.join()

        except KeyboardInterrupt:
            print("\n[*] Shutting down the server.")
        finally:
            self.tcp_server_socket.close()
            self.udp_server_socket.close()
            print("[*] Server sockets closed.")
    def server_thread(self):
      try:
        while True:
            try:
                tcp, client_address = self.tcp_server_socket.accept()
                udp, client_address_udp = self.udp_server_socket.recvfrom(self.BUFFER_SIZE)
                print(f"[+] Accepted TCP connection from {client_address}")
                client_thread = threading.Thread(target=self.handle_client, args=(tcp, self.udp_server_socket, client_address))
                client_thread.start()
            except Exception as e:
                print(f"[!] Error accepting TCP connections: {e}")
      except KeyboardInterrupt:
          print("\n[*] Shutting down TCP server.")


if __name__ == '__main__':
    server = ServeOn(host='127.0.0.1', tcp_port=12345, udp_port=12346)
    server.start()
