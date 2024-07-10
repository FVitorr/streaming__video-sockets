import os
import socket
import threading
import subprocess
import time

class ClientTCP:
    def __init__(self, host='127.0.0.1', tcp_port=12345, control_port=12346):
        self.BUFFER_SIZE = 4096 * 9
        self.tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp.settimeout(30)  # Timeout de 10 segundos para a conexão

        self.control_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.control_tcp.settimeout(30)  # Timeout de 10 segundos para a conexão

        self.frame_count = 0
        self.start_time = 0
        self.fps = 0

        try:
            self.tcp.connect((host, tcp_port))
            print(f"[+] Connected to {host}:{tcp_port} TCP")
            
            self.control_tcp.connect(('0.tcp.ngrok.io', control_port))
            print(f"[+] Connected to {host}:{control_port} TCP")

        except socket.timeout:
            print(f"[-] Connection attempt to {host}:{tcp_port} timed out.")
            self.tcp = None
            self.control_tcp = None
        except Exception as e:
            print(f"[!] Error connecting: {e}")
            self.tcp = None
            self.control_tcp = None
    
    def calculate_fps(self):
        current_time = time.time() 
        elapsed_time = current_time - self.start_time
        if elapsed_time > 1:  # Calcula FPS a cada segundo
            self.fps = self.frame_count / elapsed_time
            #print(f"Current FPS: {self.fps:.2f}", end='\r')
            self.start_time = current_time
            self.frame_count = 0

    def receive_file(self,size_file : int):
        try:
            print("[-] Receiving file via TCP...")

            devnull = open(os.devnull, 'w')
            mpv_process = subprocess.Popen(['mpv', '--quiet', '--cache=no', '--really-quiet', '-', '--no-terminal'], 
                                                stdin=subprocess.PIPE)

            self.start_time = time.time()
            start_byte = 0
            end_byte = self.BUFFER_SIZE
            while True:

                while True:
                    #Enviar requisição de inicio e fim arquivo
                    request = f"{start_byte} {end_byte}"
                    self.control_tcp.sendall(request.encode())
                    #Verificar se esta tudo certo
                    data = self.control_tcp.recv(self.BUFFER_SIZE).decode()
                    if data != "Erro":
                        break

                #Receber e processar dados
                data = self.tcp.recv(self.BUFFER_SIZE)
                if not data:
                    break
                mpv_process.stdin.write(data) #Escrever no pipe

                start_byte = end_byte
                if size_file > end_byte + self.BUFFER_SIZE:
                    end_byte += self.BUFFER_SIZE
                else:
                    end_byte += size_file - end_byte
  
                print(f"[#] Progress ({end_byte* 100 /size_file}%): {end_byte} de {size_file}", end='\r')

                self.frame_count += len(data)
                self.calculate_fps()  # Chama a função para calcular o FPS a cada frame
            
            mpv_process.stdin.close()
            #mpv_process.communicate()  # Espera até que o processo termine

            print("[*] Video streaming to mpv finished.")     
        except Exception as e:
            print(f"[!] Error receiving data: {e}")

    def run(self):
        if not self.tcp or not self.control_tcp:
            print("[!] Connection not established. Exiting.")
            return
        
        try:
            print("[..] MSG")
            # Receber resposta do servidor via segundo socket TCP
            tcp1_response = self.control_tcp.recv(self.BUFFER_SIZE)
            print(f"\t[>] TCP Response: {tcp1_response.decode()}")
            if tcp1_response.decode().startswith("File"):
                self.tcp.close()
                self.control_tcp.close()
                exit(1)

            # Solicitar o arquivo ao servidor via TCP
            msg = f"{threading.current_thread().name} TCP true"
            self.control_tcp.sendall(msg.encode())
            print(f"\t[<] TCP Request: {msg}")

            # Receber o arquivo do servidor via TCP
            size_file = int(tcp1_response.decode().split()[1])
            self.receive_file(size_file)
            
        except Exception as e:
            print(f"[!] Error during communication: {e}")
        finally:
            if self.tcp:
                try:
                    print(f"[*] Closing TCP connection to {self.tcp.getpeername()}")
                except Exception as e:
                    print(f"[!] Error accessing TCP socket info: {e}")
                self.tcp.close()
            
            if self.control_tcp:
                try:
                    print(f"[*] Closing TCP connection to {self.control_tcp.getpeername()}")
                except Exception as e:
                    print(f"[!] Error accessing TCP socket info: {e}")
                self.control_tcp.close()

if __name__ == '__main__':
    num_clients = 1  # Número de clientes que você quer abrir

    threads = []
    for i in range(num_clients):
        thread = threading.Thread(target=ClientTCP('8.tcp.ngrok.io',17149,12053).run, name=f"ClientThread-{i+1}")
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()  # Esperar todas as threads terminarem

    print("All client threads have finished.")
