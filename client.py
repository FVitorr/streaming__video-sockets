import base64
import json
import os
import socket
import struct
import threading
import subprocess
import time

class ClientTCP:
    def __init__(self, host='127.0.0.1', udp_port=12345, control_port=12346):
        self.BUFFER_SIZE = 1464
        self.SLEEP_TIME = 0.5

        #UDP troca de dados
        self.udp_server_address = (host, udp_port)
        self.udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self.BUFFER_SIZE)

        #TCP para controle
        self.control_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.control_tcp.settimeout(10)  # Timeout de 10 segundos para a conexão

        self.frame_count = 0
        self.start_time = 0
        self.fps = 0

        self.msg_control = {"d":(0,self.BUFFER_SIZE),"c":"Play"}

        try:
            self.udp.sendto(b"UDP Connection Request", self.udp_server_address)
            print(f"[+] Connected to {host}:{udp_port} UDP")

            self.control_tcp.connect((host, control_port))
            print(f"[+] Connected to {host}:{control_port} TCP")

        except socket.timeout:
            print(f"[-] Connection attempt to {host}:{control_port} timed out.")
            self.tcp = None
            self.control_tcp = None
        except Exception as e:
            print(f"[!] Error connecting: {e}")
            self.tcp = None
            self.control_tcp = None

#---------------------------------------------------------------------------------------------------

    def receive_file(self,size_file : int, bit_rate: int):
        try:
            print("[-] Receiving file via TCP...")

            self.BUFFER_SIZE = int(bit_rate) * 2
            print(f"[*] Buffer size: {self.BUFFER_SIZE}")
            devnull = open(os.devnull, 'w')
            mpv_process = subprocess.Popen(
                ['mpv', '-cache=no', '--demuxer-thread=no', '--no-audio', '-'],
                stdin=subprocess.PIPE,
                stderr=devnull
            )

            #Iniciar a thread de controle do vídeo
            thread = threading.Thread(target=self.handle_input, args= [mpv_process])
            thread.daemon = True  #Tornar a thread daemon para que ela não bloqueie a saída
            thread.start()


            self.start_time = time.time()
            end_byte = 1464
            start_byte = 0

            buffer_ = []
            buffer_ordenado = []
            count = 5
            bytes_recebidos = 0
            while True:
                while True:
                    #Enviar requisição de inicio e fim arquivo
                    self.msg_control['d'] = (start_byte,end_byte)

                    msg = json.dumps(self.msg_control).encode("utf-8")
                    self.control_tcp.sendall(msg)
                    
                    #print(self.msg_control,end='\r')
                    if self.msg_control['c'] in ('Avancar','Voltar'):self.msg_control['c'] = "Play"
                    #Verificar se esta tudo certo
                    if self.msg_control['c'] != "Pause":
                        data = self.control_tcp.recv(self.BUFFER_SIZE).decode()
                        if data != "Erro":
                            break
                    else:
                        time.sleep(0.5)

                #Receber e processar dados
                data,_ = self.udp.recvfrom(self.BUFFER_SIZE)
                if not data:
                    break
                
                data_response = json.loads(data.decode('utf-8'))
                data_response['data'] = base64.b64decode(data_response['data'])
                bytes_recebidos += len(data_response['data'])
                buffer_.append(data_response)
                if bytes_recebidos >= self.BUFFER_SIZE or end_byte == size_file: 
                    buffer_ = sorted(buffer_, key = lambda x: x['i']) 
                    
                    print(f"[#] Progress ({end_byte* 100 /size_file:.2f}%): {end_byte} de {size_file}", end='\r')
                    
                    time.sleep(self.SLEEP_TIME/2)
                    for i in buffer_:
                        mpv_process.stdin.write(i['data'])
                        mpv_process.stdin.flush()
                    
                    buffer_ = []
                    bytes_recebidos = 0

                    print("[*] Video streaming to mpv finished.")
                    #Sinalizar fim do arquivo, -> Msg não esta sendo recebida pelo servidor
                    self.msg_control = f'{-1} c c'
                    self.control_tcp.sendall(self.msg_control.encode())
                    break
  
                #print(f"[#] Progress ({end_byte* 100 /size_file:.2f}%): {end_byte} de {size_file}", end='\r')
                start_byte = end_byte
                if end_byte + 1464 < size_file:
                    end_byte += 1464
                else:
                    end_byte = size_file
            while(1):
                time.sleep(100)
            mpv_process.stdin.close()
            mpv_process.terminate() 
        except Exception as e:
            print(f"[!] Error receiving data: {e}")


            

    def handle_input(self, mpv_process):
        comand = ["Pause", "Play", "Voltar", "Avancar", "Stop"]
        print("[1 = Pause 2 = Play 3 = Voltar 4 = Avançar 5 = Stop]\n >>")
        while True:
            entry = int(input())
            if entry > 0 and entry < 6:
                #self.msg_control['c'] = comand[entry -1]
                if entry == 0:
                    command = "pause"
                if entry == 1:
                    command = "cycle pause"
                elif entry == 2:
                    command = "seek -10"
                elif entry == 3:
                    command = "seek 10"
                elif entry == 4:
                    command = "stop"

                if mpv_process.stdin:
                    mpv_process.stdin.write((command + '\n').encode('utf-8'))
                    mpv_process.stdin.flush()
                
    def run(self):
        if not self.control_tcp:
            print("[!] Connection not established. Exiting.")
            return
        
        try:
            print("[..] MSG")
            # Receber resposta do servidor via segundo socket TCP
            tcp1_response = self.control_tcp.recv(self.BUFFER_SIZE)
            data = json.loads(tcp1_response.decode('utf-8'))
            print(f"\t[>] TCP Response: {data}")

            # Solicitar o arquivo ao servidor via TCP
            msg = f"{threading.current_thread().name} TCP true"
            self.control_tcp.sendall(msg.encode())
            print(f"\t[<] TCP Request: {msg}")

            # Receber o arquivo do servidor via UDP
            self.receive_file(data['size_file'], data['bit_rate'])
            
        except Exception as e:
            print(f"[!] Error during communication: {e}")
        finally:
            # if self.tcp:
            #     try:
            #         print(f"[*] Closing TCP connection to {self.tcp.getpeername()}")
            #     except Exception as e:
            #         print(f"[!] Error accessing TCP socket info: {e}")
            #     self.tcp.close()
            
            #if self.control_tcp:
                #try:
                    #print(f"[*] Closing TCP connection to {self.control_tcp.getpeername()}")
                #except Exception as e:
                    #print(f"[!] Error accessing TCP socket info: {e}")
                #self.control_tcp.close()
            pass

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
