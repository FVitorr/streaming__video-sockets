import os
import socket
import threading
import time

class ServeOn:
    def __init__(self, host='127.0.0.1', tcp_port=12345, control_port=12346):
        self.BUFFER_SIZE = 4096 * 9
        
        # Cria e configura o socket TCP principal
        self.tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp.bind((host, tcp_port))
        self.tcp.listen(5)
        print(f"[*] TCP Server listening as {host}:{tcp_port}")

        # Cria e configura o socket TCP adicional
        self.tcp_control = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_control.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_control.bind((host, control_port))
        self.tcp_control.listen(5)
        print(f"[*] TCP Control Server listening as {host}:{control_port}")

        self.tcp_client_sockets = []  # Lista de conexões TCP ativas
        self.file_path = "/home/vitor/Downloads/picapaubiruta.mp4"

    def send_video_tcp(self,tcp_socket, control_tcp):
        try:
            # Loop para enviar segmentos do vídeo conforme solicitado pelo cliente
            send_data = 0
            last_data = ()
            while True:
                
                m = f"Ok"
                while True:
                    request = control_tcp.recv(self.BUFFER_SIZE).decode()
                    if len(request.split()) != 2:
                        m = f"Erro"
                    else:
                        start_byte, end_byte = map(int, request.split())
                        last_data = (start_byte, end_byte)
                        break
                control_tcp.sendall(m.encode())

                try:
                    with open(self.file_path, "rb") as f:
                        print(f"[*] Sending File ({send_data* 100 /self.get_file_size()}%): {send_data}/{self.get_file_size()}",end='\r')
                        f.seek(start_byte) #Mover ponteiro de leitura

                        bytes_to_send = f.read(end_byte - start_byte)
                        tcp_socket.sendall(bytes_to_send)

                        send_data += end_byte - start_byte
                except Exception as e:
                    print(f"[!] Error sending video chunk: {e}")
                        
        except Exception as e:
            print(f"[!] Error sending file '{self.file_path}': {e}")
        finally:
            print(f"[*] File '{self.file_path}' sent successfully.")

    def get_file_size(self):
        try:
            size = os.path.getsize(self.file_path)
            return size
        except FileNotFoundError:
            print(f"[!] File '{self.file_path}' not found.")
            return -1
        
    def handle_client(self, tcp_socket, control_tcp, client_address, client_control):
        try:
            self.tcp_client_sockets.append(tcp_socket)  # Adiciona a nova conexão à lista de clientes TCP ativos

            while True:
                if self.get_file_size() == -1:
                    m = f'File {self.file_path} not found.'
                    control_tcp.sendall(m.encode())
                    break
                
                # Enviar info para o cliente
                m = f'{self.file_path} {self.get_file_size()}'
                control_tcp.sendall(m.encode())
                print(f"[>] Control TCP {client_control}: {m}")

                msg_tcp = control_tcp.recv(self.BUFFER_SIZE)
                if not msg_tcp:
                    print(f"[!] No data received from {client_address}. Closing connection.")
                    break

                print(f"\t[Received TCP from {client_control}]: {msg_tcp.decode()}")

                if msg_tcp.decode().startswith("ClientThread"):
                    self.send_video_tcp(tcp_socket, control_tcp)
                    break

        except Exception as e:
            print(f"[!] Error with {client_address} (TCP): {e}")
        finally:
            self.tcp_client_sockets.remove(tcp_socket)  # Remove a conexão da lista
            tcp_socket.close()
            control_tcp.close()
            print(f"[*] Closed TCP connection with {client_address}")

    def start(self):
        print("[*] Server is running...")
        try:
            while True:
                try:
                    tcp, client_address = self.tcp.accept()
                    print(f"[+] Accepted TCP connection from {client_address}")
                    control, client_address1 = self.tcp_control.accept()
                    print(f"[+] Accepted TCP connection from {client_address1}")
                    client_thread = threading.Thread(target=self.handle_client, args=(tcp, control, client_address, client_address1))
                    client_thread.start()
                except Exception as e:
                    print(f"[!] Error accepting TCP connections: {e}")
        except KeyboardInterrupt:
            print("\n[*] Shutting down TCP server.")
        finally:
            self.tcp.close()
            self.tcp_control.close()
            print("[*] Server sockets closed.")

if __name__ == '__main__':
    server = ServeOn(host='127.0.0.1', tcp_port=12345, control_port=12346)
    server.start()
