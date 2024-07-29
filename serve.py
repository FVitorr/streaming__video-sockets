import base64
import json
import os
import socket
import threading
from moviepy.editor import VideoFileClip

class ServeOn:
    def __init__(self, host='127.0.0.1', udp_port=12345, control_port=12346):
        self.BUFFER_SIZE = 1464
        
        # Cria e configura o socket UDP principal
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, self.BUFFER_SIZE)
        self.server_socket.bind((host, udp_port))
        print(f"[*] UDP Server listening as {host}:{udp_port}")

        # Cria e configura o socket TCP adicional
        self.tcp_control = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_control.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_control.bind((host, control_port))
        self.tcp_control.listen(5)
        print(f"[*] TCP Control Server listening as {host}:{control_port}")

        self.tcp_client_sockets = []  # Lista de conexões TCP ativas
        #self.file_path = "Wildlife.mp4"
        #self.file_path = "BigBuckBunny_640x360.m4v"
        self.file_path = "video.mp4"

#---------------------------------------------------------------------------------------------------

    def send_video_(self, control_tcp, client_address):
        # Loop para enviar segmentos do vídeo conforme solicitado pelo cliente
        start_byte = 0
        end_byte = 0
        send_data = 0
        index = 0
        size_file = self.file_size()['size']
        while True:
            c_request = {"isCount": True, "c_request": 0}
            m = f"Ok"
            while True:
                recive_cliente = control_tcp.recv(self.BUFFER_SIZE)
                try:
                    control_data = json.loads(recive_cliente.decode('utf-8'))
                    #print(control_data, end="\r")
                except json.JSONDecodeError:
                    print(f"[!] Error decoding JSON: {recive_cliente}")
                    c_request["c_request"] += 1


                if control_data:
                    if control_data['c'] == 'Play':
                        start_byte,end_byte = control_data['d']
                        break
                    if control_data['c'] == 'Pause':
                        c_request["isCount"] = False

                if 10 < int(c_request["c_request"]):
                    print("[!]Erro: max request")
                    break

                if c_request["isCount"]: c_request["c_request"] += 1

            control_tcp.sendall(m.encode())
            if c_request["c_request"] > 10:
                return
            data_send = {}
            with open(self.file_path, "rb") as f:
                f.seek(start_byte) #Mover ponteiro de leitura

                bytes_to_send = f.read(end_byte - start_byte)
                encoded = base64.b64encode(bytes_to_send)
                
                data_send['i'] = index
                data_send['data'] = encoded.decode('ascii')
                

                data = json.dumps(data_send).encode('utf-8')
                
                # Log para verificar os dados antes do envio
                #print(f"Sending packet with index {index}, size: {len(bytes_to_send)} bytes", end= '\r')
                #print(f"Data preview (first 50 bytes): {bytes_to_send[:50]}...")  # Log dos primeiros bytes do pacote
                
                self.server_socket.sendto(data, client_address)
                index += 1
            print(f"[*] Sending File ({send_data* 100 /size_file:.2f}%): {send_data}/{size_file}",end='\r')
            send_data += end_byte - start_byte

#---------------------------------------------------------------------------------------------------

    def file_size(self):
        try:
            video = VideoFileClip(self.file_path)
            size = os.path.getsize(self.file_path)
            time = video.duration
            #w,h = video.size() #
            bit_rate = size/time
            return {
                "size": size,
                "time": time,
                "bit_rate": bit_rate
            }
        except FileNotFoundError:
            print(f"[!] File '{self.file_path}' not found.")
            return -1
        
    def get_video_duration(self):
        try:
            clip = VideoFileClip(self.file_path)
            return {"seconds": clip.duration, "minutes": clip.duration/60}
        except Exception as e:
            print(f"Error retrieving video duration: {e}")
            return None

        
    def handle_client(self, udp_socket, control_tcp, client_address, client_control):
        try:
            self.tcp_client_sockets.append(udp_socket)  # Adiciona a nova conexão à lista de clientes TCP ativos

            while True:
                if self.file_size() == -1:
                    m = f'File {self.file_path} not found.'
                    control_tcp.sendall(m.encode())
                    break

                # enviar info para o cliente

                m = {
                     'file_path': self.file_path ,
                     'size_file' : self.file_size().get('size'),
                     'bit_rate' : self.file_size().get('bit_rate')
                    }
                control_tcp.sendall(json.dumps(m).encode("utf-8"))
                print(f"[>] Control TCP {client_control}: {m}")

                msg_tcp = control_tcp.recv(self.BUFFER_SIZE)
                if not msg_tcp:
                    print(f"[!] No data received from {client_address}. Closing connection.")
                    break

                print(f"\t[Received TCP from {client_control}]: {msg_tcp.decode()}")

                if msg_tcp.decode().startswith("ClientThread"):
                    self.send_video_(control_tcp, client_address)
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
