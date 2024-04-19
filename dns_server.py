import socket
import datetime
import sys
import json
import binascii 
import signal
import os
import random

class DNSServer:
    def __init__(self, port=53, ip_address='0.0.0.0', output_file="DNSLog.txt", name_configuration="configuration.json",domain_ip="domain_dns_name_ip.json"):
        self.port = port
        self.ip_address = ip_address
        self.output_file = output_file
        self.name_domain_ip=domain_ip
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.should_stop = False 
        self.domain_ip={}
        self.dictionary={}
        self.array_transit_numbers=[]
        self.pakage_on_server_next=[]
        self.package_dns_transcript = None
        self.Configuration=read_json_file(name_configuration)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if os.path.exists(self.name_domain_ip):
            self.domain_ip=read_json_file(self.name_domain_ip)
        else:
            write_to_json_file(self.domain_ip, self.name_domain_ip)

        signal.signal(signal.SIGINT, self.signal_handler)

    def signal_handler(self, sig, frame):
        self.socket.close()
        self.log_dns_server("Received SIGINT, stopping DNS server gracefully.")
        self.should_stop = True 
        sys.exit(0)

    def log_dns_server(self, log):
        now = datetime.datetime.now()
        formatted_time = now.strftime('%Y-%m-%d %H:%M:%S')
        with open(self.output_file, 'a+') as f:
            f.write(f"{formatted_time}: {log}\n")
    
    def saving_transit_numbers(self, num):
        self.array_transit_numbers.append(num)
        return list(set(self.array_transit_numbers))

    def selection_of_a_unique_id(self):
        while True:
            random_number = random.randint(0, 65535)
            hex_string = (4-len(hex(random_number)[2:]))*'0'+hex(random_number)[2:]
            if not hex_string in self.array_transit_numbers:
                return hex_string

    def start(self):
        self.socket.bind((self.ip_address, self.port))
        self.log_dns_server(f"The DNS server is running on {self.ip_address}:{self.port}")
        try:
            while not self.should_stop: 
                pacage_of_client, addr = self.socket.recvfrom(1024)
                self.log_dns_server(f"Addr:{addr}\n Data {pacage_of_client}")
                self.package_dns_transcript = PakageDns(binascii.hexlify(pacage_of_client).decode('utf-8'))
                self.saving_transit_numbers(self.package_dns_transcript.id)
                if self.package_dns_transcript.flag['QR'] == '0': #запрос(0)/ ответ(1)
                    if self.package_dns_transcript.transcript_QUERIES(self.package_dns_transcript.QUERIES) in self.domain_ip:
                        self.package_dns_transcript.flag['QR'] = '1'
                        self.package_dns_transcript.flag['AA'] = '1'
                        self.package_dns_transcript.flag['RA'] = '1'
                        array_domain = self.domain_ip[self.package_dns_transcript.transcript_QUERIES(self.package_dns_transcript.QUERIES)]
                        self.package_dns_transcript.ANCOUNT=(4-len(hex(len(array_domain['IP']))[2:]))*'0'+hex(len(array_domain['IP']))[2:]
                        mesage_client=self.package_dns_transcript.reassemble()+self.reassemble_ANCOUNT(array_domain)
                        self.socket.sendto(binascii.unhexlify(mesage_client), addr)
                    else:
                        old_id = self.package_dns_transcript.id
                        self.package_dns_transcript.id = self.selection_of_a_unique_id() #отправляет доп запрос на сервер 8.8.8.8
                        self.dictionary = self.modify_dictionary(self.package_dns_transcript.id, value=old_id, addr=addr, remove=False)
                        self.package_dns_transcript.flag['RA'] = "1"
                        self.socket.sendto(binascii.unhexlify(self.package_dns_transcript.reassemble()), ('8.8.8.8',self.port))

                else:
                    (ip_client, port_client)=self.dictionary[self.package_dns_transcript.id]["addr"]
                    self.package_dns_transcript.id = self.dictionary[self.package_dns_transcript.id]["id"]
                    self.package_dns_transcript.flag["AA"] = "0"
                    self.dictionary = self.modify_dictionary(self.package_dns_transcript.id,remove=True)
                    self.socket.sendto(binascii.unhexlify(self.package_dns_transcript.reassemble()), (ip_client, port_client))
                    

        except OSError as e:
            self.log_dns_server(f'Error when starting the server: {e}')
        finally:
            self.socket.close()
            self.log_dns_server('DNS server stopped')  

    def reassemble_ANCOUNT(self,site_array):
        string_ANCOUNT=''
        for elem_ANCOUNT in site_array["IP"]:
            string_ANCOUNT+='C00C00010001'+(8-len(hex(int(site_array["TTL"]))[2:]))*'0'+hex(int(site_array["TTL"]))[2:]+"0004"+self.convert_ip_to_hex_format(elem_ANCOUNT)
        return string_ANCOUNT

    def close(self):
        self.log_dns_server("Received, stopping DNS server gracefully.")
        self.should_stop = True 
        sys.exit(0)
    
    def modify_dictionary(self, key=None, value=None,addr=None, remove=False):
    # Если нужно добавить элемент по ключу
        if not remove and value is not None:
            self.dictionary[key] = {
                                    "id":value,
                                    "addr":addr
        }

        # Если нужно удалить элемент по ключу
        elif remove and key in self.dictionary:
            del self.dictionary[key]

        else:
            self.log_dns_server("Error modify_dictionary")

        return self.dictionary
    
    def convert_ip_to_hex_format(self, ip_address):
        hex_to_10 = ip_address
        array_item_hex = [hex(int(elem))[2:] for elem in hex_to_10.split('.')]
        arr_with_zero = ['0' + item if len(item) < 2 else item for item in array_item_hex]
        return ''.join(arr_with_zero)

class PakageDns:
    def __init__(self,package):
        self.id = package[:2*2]
        self.flag = self.transcript_flag(package[2*2:4*2])
        self.QDCOUNT = package[4*2:6*2]
        self.ANCOUNT = package[6*2:8*2]
        self.NSCOUNT = package[8*2:10*2]
        self.ARCOUNT = package[10*2:12*2]
        self.QUERIES = package[12*2:]
        
    
    def transcript_QUERIES(self, QUERIES):
        length_next = 0
        array_QUERIES = []
        sting_QUERIES = ''
        while int(QUERIES[length_next:length_next+2],16) !=0:
            length = int(QUERIES[length_next:length_next+2],16)
            array_QUERIES.append(QUERIES[length_next+2:length_next+2+length*2])
            length_next = length_next+length*2+2
        for elem_QUERIES in array_QUERIES:
            sting_QUERIES = sting_QUERIES + ''.join([chr(int(elem_QUERIES[i:i+2],16)) for i in range(0,len(elem_QUERIES),2)])+'.'
        return sting_QUERIES[:-1]
    
    def reassemble(self):
        self.flag = (4-len(hex(int(''.join(self.flag.values()),2))[2:]))*'0'+hex(int(''.join(self.flag.values()),2))[2:]
        attributes = vars(self)
        string_attributes=''
        for key, elem in attributes.items():
            string_attributes = string_attributes+elem
        return string_attributes

    def transcript_flag(self, flag):
        flag_bin = (16-len(bin(int(flag, 16))[2:]))*'0'+bin(int(flag, 16))[2:]
        return {
            "QR":flag_bin[:1],
            "Opcode":flag_bin[1:5],
            "AA":flag_bin[5:6],
            "TC":flag_bin[6:7],
            "RD":flag_bin[7:8],
            "RA":flag_bin[8:9],
            "Z":flag_bin[9:12],
            "RCODE":flag_bin[12:16]
        }

def read_json_file(file_name):
    try:
        with open(file_name, 'r', encoding='utf-8') as file:
            data = json.load(file)
        return data
    except FileNotFoundError:
        DNSServer.log_dns_server(f"File '{file_name}' no")
        return None
    except json.JSONDecodeError:
        DNSServer.log_dns_server(f"Error JSON file'{file_name}'.")
        return None

def write_to_json_file(data, file_path):
    try:
        with open(file_path, 'w') as json_file:
            json.dump(data, json_file, indent=4)  # Записываем данные в файл с отступами для удобства чтения
        return True
    except Exception as e:
        DNSServer.log_dns_server(f"Error file JSON file: {e}")
        return False


if __name__ == "__main__":
    server_default = DNSServer(name_configuration="configuration.json")
    server_default.start()