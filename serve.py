import json
import os
import socket
import threading
import time

class ServeOn:
    def __init__(self, host='127.0.0.1', udp_port=12345, control_port=12346):
        self.BUFFER_SIZE = 1000
        
        # Cria e configura o socket UDP principal
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((host, udp_port))
        print(f"[*] UDP Server listening as {host}:{udp_port}")

        # Cria e configura o socket TCP adicional
        self.tcp_control = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_control.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_control.bind((host, control_port))
        self.tcp_control.listen(5)
        print(f"[*] TCP Control Server listening as {host}:{control_port}")

        self.tcp_client_sockets = []  # Lista de conexões TCP ativas
        self.file_path = "/home/vitor/Downloads/picapaubiruta.mp4"

    def send_video_udp(self,udp_socket, control_tcp, client_address):
        try:
            # Loop para enviar segmentos do vídeo conforme solicitado pelo cliente
            send_data = 0
            start_byte = 0
            end_byte = self.BUFFER_SIZE
            while True:
                c_request = 0
                m = f"Ok"
                while True:
                    request = control_tcp.recv(self.BUFFER_SIZE).decode()
                    print( request.split()[0],send_data,request)
                    if int(request.split()[0]) == send_data:
                        break
                    c_request += 1
                    if c_request > 10:
                        print("[!]Erro: max request", end='\r')
                        break

                control_tcp.sendall(m.encode())
                if c_request > 10:
                    return
                

                try:
                    with open(self.file_path, "rb") as f:
                        #print(f"[*] Sending File ({send_data* 100 /self.get_file_size():.2f}%): {send_data}/{self.get_file_size()}",end='\r')
                        f.seek(start_byte) #Mover ponteiro de leitura

                        bytes_to_send = f.read(end_byte - start_byte)
                        self.server_socket.sendto(bytes_to_send, client_address)


                    send_data += end_byte - start_byte
                    start_byte = end_byte
                    if end_byte + self.BUFFER_SIZE < self.get_file_size():
                        end_byte += self.BUFFER_SIZE
                    else:
                        end_byte = self.get_file_size()
                except Exception as e:
                    print(f"[!] Error sending video chunk: {e}")
                        
        except Exception as e:
            print(f"[!] Error sending file '{self.file_path}': {e}")
        finally:
            print(f"[*] File '{self.file_path}' sent successfully.")
    def send_video_(self,udp_socket, control_tcp, client_address):
        # Loop para enviar segmentos do vídeo conforme solicitado pelo cliente
        send_data = 0
        start_byte = 0
        end_byte = self.BUFFER_SIZE
        while True:
            c_request = 0
            m = f"Ok"
            while True:
                request = control_tcp.recv(self.BUFFER_SIZE)
                data = json.loads(request.decode('utf-8'))
                print( data['d'],send_data,data)
                if data:
                    if int(data['d']) == send_data:
                        break
                if c_request > 10:
                    print("[!]Erro: max request")
                    break
                c_request += 1

            control_tcp.sendall(m.encode())
            if c_request > 10:
                return
            
            with open(self.file_path, "rb") as f:
                    #print(f"[*] Sending File ({send_data* 100 /self.get_file_size():.2f}%): {send_data}/{self.get_file_size()}",end='\r')
                    f.seek(start_byte) #Mover ponteiro de leitura

                    bytes_to_send = f.read(end_byte - start_byte)
                    self.server_socket.sendto(bytes_to_send, client_address)


            send_data += end_byte - start_byte
            start_byte = end_byte
            if end_byte + self.BUFFER_SIZE < self.get_file_size():
                end_byte += self.BUFFER_SIZE
            else:
                end_byte = self.get_file_size()
 

    def get_file_size(self):
        try:
            size = os.path.getsize(self.file_path)
            return size
        except FileNotFoundError:
            print(f"[!] File '{self.file_path}' not found.")
            return -1
        
    def handle_client(self, udp_socket, control_tcp, client_address, client_control):
        try:
            self.tcp_client_sockets.append(udp_socket)  # Adiciona a nova conexão à lista de clientes TCP ativos

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
                    self.send_video_(udp_socket, control_tcp, client_address)
                    break

        except Exception as e:
            print(f"[!] Error with {client_address} (TCP): {e}")
        finally:
            self.tcp_client_sockets.remove(udp_socket)  # Remove a conexão da lista
            #udp_socket.close()
            control_tcp.close()
            print(f"[*] Closed TCP connection with {client_address}")

    def start(self):
        print("[*] Server is running...")
        try:
            while True:
                try:
                    udp, client_address = self.server_socket.recvfrom(self.BUFFER_SIZE)
                    print(f"[+] Accepted TCP connection from {client_address}")
                    control, client_address1 = self.tcp_control.accept()
                    print(f"[+] Accepted TCP connection from {client_address1}")
                    client_thread = threading.Thread(target=self.handle_client, args=(udp, control, client_address, client_address1))
                    client_thread.start()
                except Exception as e:
                    print(f"[!] Error accepting TCP connections: {e}")
        except KeyboardInterrupt:
            print("\n[*] Shutting down TCP server.")
        finally:
            self.server_socket.close()
            self.tcp_control.close()
            print("[*] Server sockets closed.")

if __name__ == '__main__':
    server = ServeOn(host='127.0.0.1', udp_port=12345, control_port=12346)
    server.start()
