import os
import socket
import threading
import subprocess
import time

class ClientTCP:
    def __init__(self, host='127.0.0.1', tcp_port=12345, udp_port=12346):
        self.BUFFER_SIZE = 312
        self.tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp.settimeout(10)  # Timeout de 10 segundos para a conexão
        
        self.udp_server_address = (host, udp_port)
        self.udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        self.frame_count = 0
        self.start_time = 0
        self.fps = 0

        try:
            self.tcp.connect((host, tcp_port))
            print(f"[+] Connected to {host}:{tcp_port} TCP")
            self.udp.sendto(b"UDP Connection Request", self.udp_server_address)
            print(f"[+] Connected to {host}:{udp_port} UDP")

        except socket.timeout:
            print(f"[-] Connection attempt to {host}:{tcp_port} timed out.")
            self.tcp = None
        except Exception as e:
            print(f"[!] Error connecting: {e}")
            self.tcp = None
    
    def calculate_fps(self):
        current_time = time.time() 
        elapsed_time = current_time - self.start_time
        if elapsed_time > 1:  # Calcula FPS a cada segundo
            self.fps = self.frame_count / elapsed_time
            print(f"Current FPS: {self.fps:.2f}", end='\r')
            self.start_time = current_time
            self.frame_count = 0

    def receive_file(self):
        try:
            print("[-] Receiving file via TCP...")

            #devnull = open(os.devnull, 'w')
            #mpv_process = subprocess.Popen(['mpv', '--cache=no', '-'], 
                                                #stdin=subprocess.PIPE, stdout= devnull)

            devnull = open(os.devnull, 'w')
            mpv_process = subprocess.Popen(['mpv', '--quiet','--cache=no', '--really-quiet', '-', '--no-terminal'], 
                                                stdin=subprocess.PIPE)


            self.start_time = time.time()
            while True:
                data = self.tcp.recv(self.BUFFER_SIZE)
                if not data:
                    break
                mpv_process.stdin.write(data)
                self.frame_count += 1
                self.calculate_fps()  # Chama a função para calcular o FPS a cada frame
            
            mpv_process.stdin.close()
            mpv_process.communicate()  # Espera até que o processo termine

            print("[*] Video streaming to mpv finished.")     
        except Exception as e:
            print(f"[!] Error receiving data: {e}")

    def run(self):
        if not self.tcp:
            print("[!] Connection not established. Exiting.")
            return
        
        try:
            # Receber resposta do servidor via UDP
            udp_response, _ = self.udp.recvfrom(self.BUFFER_SIZE)
            print(f"\t[>] UDP Response: {udp_response.decode()}")
            if udp_response.decode().startswith("File"):
                self.tcp.close()
                self.udp.close()
                exit(1)

            # Solicitar o arquivo ao servidor via TCP
            msg = f"{threading.current_thread().name} TCP true"
            self.tcp.sendall(msg.encode())
            print(f"\t[<] TCP Request: {msg}")

            # Receber o arquivo do servidor via TCP
            self.receive_file()
            
        except Exception as e:
            print(f"[!] Error during communication: {e}")
        finally:
            if self.tcp:
                try:
                    print(f"[*] Closing TCP connection to {self.tcp.getpeername()}")
                except Exception as e:
                    print(f"[!] Error accessing TCP socket info: {e}")
                self.tcp.close()
            
            if self.udp:
                self.udp.close()
                print(f"[*] Closing UDP connection")

if __name__ == '__main__':
    num_clients = 1  # Número de clientes que você quer abrir

    threads = []
    for i in range(num_clients):
        thread = threading.Thread(target=ClientTCP().run, name=f"ClientThread-{i+1}")
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()  # Esperar todas as threads terminarem

    print("All client threads have finished.")
