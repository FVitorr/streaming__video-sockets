import base64
import json
import os
import socket
import threading
from moviepy.editor import VideoFileClip

class ServeOn:
    def __init__(self, host='127.0.0.1', udp_port=12345, control_port=12346):
        self.BUFFER_SIZE = 1464 * 3
        
        # Cria e configura o socket UDP principal
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, self.BUFFER_SIZE)
        self.udp_socket.bind((host, udp_port))
        print(f"[*] UDP Server listening as {host}:{udp_port}")

        # Cria e configura o socket TCP adicional
        self.tcp_control_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_control_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_control_socket.bind((host, control_port))
        self.tcp_control_socket.listen(5)
        print(f"[*] TCP Control Server listening as {host}:{control_port}")

        self.active_tcp_connections = []  # Lista de conexões TCP ativas
        self.video_file_path = "video4.mp4"

#---------------------------------------------------------------------------------------------------

    def send_video_(self, control_tcp, client_address):
        # Loop para enviar segmentos do vídeo conforme solicitado pelo cliente
        start_byte = 0
        end_byte = 0
        bytes_sent = 0
        packet_index = 0
        video_size = self.get_video_info()['size']
        
        while True:
            c_request = {"isCount": True, "c_request": 0}
            m = f"Ok"
            control_data = ""

            while True:
                cliente_response = control_tcp.recv(self.BUFFER_SIZE)
                
                try:
                    control_data = json.loads(cliente_response.decode('utf-8'))
                except json.JSONDecodeError:
                    print(f"[!] Error decoding JSON: {cliente_response}")
                    c_request["c_request"] += 1

                if control_data:
                    if control_data['c'] == 'Play':
                        start_byte,end_byte = control_data['d']
                        break
                    if control_data['c'] == 'Pause':
                        c_request["isCount"] = False
                    if control_data['c'] == 'Stop':
                        print("[*] Stop video")
                        control_tcp.close()
                        break

                if 10 < int(c_request["c_request"]):
                    print("[!]Erro: max request")
                    break

                if c_request["isCount"]: c_request["c_request"] += 1

            control_tcp.sendall(m.encode())

            if c_request["c_request"] > 10:
                return
            
            data_send = {}

            with open(self.video_file_path, "rb") as f:
                f.seek(start_byte) #Mover ponteiro de leitura

                bytes_to_send = f.read(end_byte - start_byte)
                encoded = base64.b64encode(bytes_to_send)
                
                data_send['i'] = packet_index
                data_send['data'] = encoded.decode('ascii')

                data = json.dumps(data_send).encode('utf-8')
                
                self.udp_socket.sendto(data, client_address)
                packet_index += 1

            print(f"[*] Sending File ({bytes_sent* 100 /video_size:.2f}%): {bytes_sent}/{video_size}",end='\r')
            bytes_sent += end_byte - start_byte
            if (bytes_sent >= video_size or end_byte == video_size):
                print("[*] Video streaming finished.")
                break

#---------------------------------------------------------------------------------------------------

    def get_video_info(self):
        try:
            video_clip = VideoFileClip(self.video_file_path)
            size = os.path.getsize(self.video_file_path)
            duration = video_clip.duration
            bit_rate = size/duration
            return {
                "size": size,
                "time": duration,
                "bit_rate": bit_rate
            }
        except FileNotFoundError:
            print(f"[!] File '{self.video_file_path}' not found.")
            return -1
        
    def get_video_duration(self):
        try:
            clip = VideoFileClip(self.video_file_path)
            return {"seconds": clip.duration, "minutes": clip.duration/60}
        except Exception as e:
            print(f"Error retrieving video duration: {e}")
            return None

        
    def handle_client(self, udp_socket, control_tcp, client_address, client_control):
        try:
            self.active_tcp_connections.append(udp_socket)  # Adiciona a nova conexão à lista de clientes TCP ativos

            while True:
                if self.get_video_info() == -1:
                    m = f'File {self.video_file_path} not found.'
                    control_tcp.sendall(m.encode())
                    break

                m = {
                     'file_path': self.video_file_path ,
                     'size' : self.get_video_info().get('size'),
                     'bit_rate' : self.get_video_info().get('bit_rate')
                    }
                control_tcp.sendall(json.dumps(m).encode("utf-8"))
                print(f"[>] Control TCP {client_control}: {m}")

                msg_tcp = control_tcp.recv(self.BUFFER_SIZE)
                if not msg_tcp:
                    print(f"[!] No data received from {client_address}. Closing connection.")
                    break

                print(f"\t[Received TCP from {client_control}]: {msg_tcp.decode()}")

                video = ['video5.mp4', 'video4.mp4', 'video3.mp4']
                self.video_file_path = video[int(list(msg_tcp.decode())[-1])-1]

                if msg_tcp.decode().startswith("ClientThread"):
                    self.send_video_(control_tcp, client_address)
                    break

        except Exception as e:
            print(f"[!] Error with {client_address} (TCP): {e}")
        finally:
            self.active_tcp_connections.remove(udp_socket)  # Remove a conexão da lista
            #udp_socket.close()
            control_tcp.close()
            print(f"[*] Closed TCP connection with {client_address}")

    def start(self):
        print("[*] Server is running...")
        try:
            while True:
                try:
                    udp, client_address = self.udp_socket.recvfrom(self.BUFFER_SIZE)
                    print(f"[+] Accepted TCP connection from {client_address}")
                    control_socket, client_control_address = self.tcp_control_socket.accept()
                    print(f"[+] Accepted TCP connection from {client_control_address}")
                    client_thread = threading.Thread(target=self.handle_client, args=(udp, control_socket, client_address, client_control_address))
                    client_thread.start()
                except Exception as e:
                    print(f"[!] Error accepting TCP connections: {e}")
        except KeyboardInterrupt:
            print("\n[*] Shutting down TCP server.")
        finally:
            self.udp_socket.close()
            self.tcp_control_socket.close()
            print("[*] Server sockets closed.")

if __name__ == '__main__':
    print("[*] Starting server...")
    print("---------------------------------")
    server = ServeOn(host='192.168.0.102', udp_port=12345, control_port=12346)
    server.start()