# -*- coding: utf-8 -*-
import socket
import argparse
import os
import threading
import struct
from enum import Enum



class client :



    # ******************** TYPES *********************

    # *

    # * @brief Return codes for the protocol methods

    class RC(Enum) :

        OK = 0

        ERROR = 1

        USER_ERROR = 2

    class OP:
        REGISTER = 0
        UNREGISTER = 1
        CONNECT = 2
        DISCONNECT = 3
        PUBLISH = 4
        DELETE = 5
        LIST_USERS = 6
        LIST_CONTENT = 7
        GET_FILE = 8

    # ****************** ATTRIBUTES ******************

    _server = None

    _port = -1

    _connected_user = None

    _listen_port = None

    _server_socket = None

    _listener_thread = None



    # ******************** METHODS *******************





    @staticmethod
    def register(user):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((client._server, client._port))
                
                # 1. Preparar datos según estructura peticion
                operacion = 0  # OP_REGISTER = 0
                usuario = user.encode().ljust(256, b'\x00')  # 256 bytes
                nombre_fichero = b'\x00' * 256  # Campo vacío
                descripcion = b'\x00' * 256      # Campo vacío
                puerto = 0                       # No relevante para REGISTER

                # 2. Empaquetar con struct.pack
                packed_data = struct.pack(
                    "!B256s256s256si",
                    operacion,
                    usuario,
                    nombre_fichero,
                    descripcion,
                    puerto
                )
                
                # 4. Enviar y recibir respuesta
                s.sendall(packed_data)
                response = s.recv(1)
                code = response[0] if response else 2
                
                if code == 0:
                    print("REGISTER OK")
                    return client.RC.OK
                elif code == 1:
                    print("USERNAME IN USE")
                    return client.RC.USER_ERROR
                else:
                    print("REGISTER FAIL")
                    return client.RC.ERROR
                    
        except Exception as e:
            print("REGISTER FAIL")
            return client.RC.ERROR



    @staticmethod
    def unregister(user):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((client._server, client._port))
                
                # 1. Preparar datos según la estructura peticion
                operacion = 1  # OP_UNREGISTER = 1
                usuario = user.encode().ljust(256, b'\x00')  # 256 bytes
                nombre_fichero = b'\x00' * 256  # Campo vacío
                descripcion = b'\x00' * 256      # Campo vacío
                puerto = 0                        # No relevante

                # 2. Empaquetar con struct.pack
                packed_data = struct.pack(
                    "!B256s256s256si",
                    operacion,
                    usuario,
                    nombre_fichero,
                    descripcion,
                    puerto
                )
                
                # 3. Enviar y recibir respuesta
                s.sendall(packed_data)
                response = s.recv(1)
                code = response[0] if response else 2
                if code == 0:
                    print("UNREGISTER OK")
                    return client.RC.OK
                elif code == 1:
                    print("USER DOES NOT EXIST")
                    return client.RC.USER_ERROR
                else:
                    print("UNREGISTER FAIL")
                    return client.RC.ERROR
        except Exception as e:
            print("UNREGISTER FAIL")
            return client.RC.ERROR





    

    @staticmethod
    def connect(user):
        try:
            # 1. Obtener puerto disponible
            temp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            temp_sock.bind(('', 0))
            port = temp_sock.getsockname()[1]
            temp_sock.close()

            # 2. Preparar datos de la petición
            operacion = 2  # OP_CONNECT
            usuario = user.encode().ljust(256, b'\x00')
            nombre_fichero = b'\x00' * 256
            descripcion = b'\x00' * 256
            puerto_network = port  # 2 bytes
            packed_data = struct.pack(
                "!B256s256s256sH",  # H = unsigned short (2 bytes)
                operacion,
                usuario,
                nombre_fichero,
                descripcion,
                puerto_network
                )

            # 4. Enviar al servidor
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((client._server, client._port))
                s.sendall(packed_data)
                response = s.recv(1)
                code = response[0] if response else 3
                
                if code == 0:
                    client._connected_user = user
                    print("CONNECT OK")
                    return client.RC.OK
                else:
                    print("CONNECT FAIL")
                    return client.RC.ERROR

        except Exception as e:
            print(f"CONNECT FAIL: {str(e)}")
            return client.RC.ERROR





    

    @staticmethod
    def disconnect(user):
        try:
            # 1. Preparar datos de la petición (misma estructura que connect)
            operacion = 3  # OP_DISCONNECT
            usuario = user.encode().ljust(256, b'\x00')
            nombre_fichero = b'\x00' * 256  # Campo vacío pero necesario
            descripcion = b'\x00' * 256     # Campo vacío pero necesario
            puerto = 0  # No se usa en disconnect, pero es parte de la estructura

            # 2. Empaquetar todos los campos (igual que en connect)
            packed_data = struct.pack(
                "!B256s256s256sH",  # Mismo formato: B + 3*256s + H
                operacion,
                usuario,
                nombre_fichero,
                descripcion,
                puerto
            )

            # 3. Enviar y recibir respuesta
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((client._server, client._port))
                s.sendall(packed_data)
                response = s.recv(1)
                code = response[0] if response else 3

                if code == 0:
                    if client._server_socket:
                        client._server_socket.close()
                        client._listener_thread = None
                    client._connected_user = None
                    print("DISCONNECT OK")
                    return client.RC.OK
                elif code == 1:
                    print("DISCONNECT FAIL, USER DOES NOT EXIST")
                elif code == 2:
                    print("DISCONNECT FAIL, USER NOT CONNECTED")
                else:
                    print("DISCONNECT FAIL")
                return client.RC.ERROR
        except Exception as e:
            print(f"DISCONNECT FAIL: {str(e)}")
            return client.RC.ERROR



    @staticmethod
    def publish(fileName, description):
        try:
            if not client._connected_user:
                print("PUBLISH FAIL, USER NOT CONNECTED")
                return client.RC.ERROR

            # 1. Preparar datos de la petición (misma estructura que connect/disconnect)
            operacion = 4  # OP_PUBLISH (ajusta el código según tu servidor)
            usuario = client._connected_user.encode().ljust(256, b'\x00')
            nombre_fichero = fileName.encode().ljust(256, b'\x00')
            descripcion_pub = description.encode().ljust(256, b'\x00')
            puerto = 0  # No se usa en publish, pero es parte de la estructura

            # 2. Empaquetar todos los campos
            packed_data = struct.pack(
                "!B256s256s256sH",  # Mismo formato: B + 3*256s + H
                operacion,
                usuario,
                nombre_fichero,
                descripcion_pub,
                puerto
            )
            
            # 3. Enviar y recibir respuesta
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((client._server, client._port))
                s.sendall(packed_data)
                response = s.recv(1)
                code = response[0] if response else 4  # 4 = Error desconocido

                if code == 0:
                    print("PUBLISH OK")
                    return client.RC.OK
                elif code == 1:
                    print("PUBLISH FAIL, USER DOES NOT EXIST")
                elif code == 2:
                    print("PUBLISH FAIL, USER NOT CONNECTED")
                elif code == 3:
                    print("PUBLISH FAIL, CONTENT ALREADY PUBLISHED")
                else:
                    print("PUBLISH FAIL")
                return client.RC.ERROR

        except Exception as e:
            print(f"PUBLISH FAIL: {str(e)}")
            return client.RC.ERROR



    @staticmethod
    def delete(fileName):
        try:
            if not client._connected_user:
                print("DELETE FAIL, USER NOT CONNECTED")
                return client.RC.ERROR

            # 1. Preparar datos de la petición (misma estructura)
            operacion = 5  # OP_DELETE (ajusta el código según tu servidor)
            usuario = client._connected_user.encode().ljust(256, b'\x00')
            nombre_fichero = fileName.encode().ljust(256, b'\x00')
            descripcion = b'\x00' * 256  # Campo vacío pero necesario
            puerto = 0  # No se usa en delete, pero es parte de la estructura

            # 2. Empaquetar todos los campos
            packed_data = struct.pack(
                "!B256s256s256sH",  # Mismo formato: B + 3*256s + H
                operacion,
                usuario,
                nombre_fichero,
                descripcion,
                puerto
            )

            # 3. Enviar y recibir respuesta
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((client._server, client._port))
                s.sendall(packed_data)
                response = s.recv(1)
                code = response[0] if response else 4  # 4 = Error desconocido

                if code == 0:
                    print("DELETE OK")
                    return client.RC.OK
                elif code == 1:
                    print("DELETE FAIL, USER DOES NOT EXIST")
                elif code == 2:
                    print("DELETE FAIL, USER NOT CONNECTED")
                elif code == 3:
                    print("DELETE FAIL, CONTENT NOT PUBLISHED")
                else:
                    print("DELETE FAIL")
                return client.RC.ERROR

        except Exception as e:
            print(f"DELETE FAIL: {str(e)}")
            return client.RC.ERROR




    @staticmethod

    def  listusers() :

        try:
            if not client._connected_user:
                print("LIST_USERS FAIL, USER NOT CONNECTED")
                return client.RC.ERROR

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((client._server, client._port))
                s.sendall(b'LIST_USERS\0' + client._connected_user.encode() + b'\0')
                response = s.recv(1)
                if not response or response[0] != 0:
                    print("LIST_USERS FAIL")
                    return client.RC.ERROR

                num_users = int(s.recv(1024).split(b'\0')[0].decode())
                print("LIST_USERS OK")
                for _ in range(num_users):
                    user_data = s.recv(1024).split(b'\0')
                    print("{} {} {}".format(user_data[0].decode(), user_data[1].decode(), user_data[2].decode()))
                return client.RC.OK
        except Exception as e:
            print("LIST_USERS FAIL")
            return client.RC.ERROR



    @staticmethod

    def  listcontent(user) :

        try:
            if not client._connected_user:
                print("LIST_CONTENT FAIL, USER NOT CONNECTED")
                return client.RC.ERROR

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((client._server, client._port))
                s.sendall(b'LIST_CONTENT\0' + client._connected_user.encode() + b'\0' + user.encode() + b'\0')
                response = s.recv(1)
                code = response[0] if response else 4
                if code == 0:
                    num_files = int(s.recv(1024).split(b'\0')[0].decode())
                    print("LIST_CONTENT OK")
                    for _ in range(num_files):
                        file_data = s.recv(1024).split(b'\0')
                        print("{}: {}".format(file_data[0].decode(), file_data[1].decode()))
                    return client.RC.OK
                elif code == 3:
                    print("LIST_CONTENT FAIL, REMOTE USER DOES NOT EXIST")
                else:
                    print("LIST_CONTENT FAIL")
                return client.RC.ERROR
        except Exception as e:
            print("LIST_CONTENT FAIL")
            return client.RC.ERROR



    @staticmethod

    def  getfile(user,  remote_FileName,  local_FileName) :

        try:
            # Get user info via LIST_USERS
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((client._server, client._port))
                s.sendall(b'LIST_USERS\0' + client._connected_user.encode() + b'\0')
                response = s.recv(1)
                if not response or response[0] != 0:
                    print("GET_FILE FAIL")
                    return client.RC.ERROR

                num_users = int(s.recv(1024).split(b'\0')[0].decode())
                target = None
                for _ in range(num_users):
                    data = s.recv(1024).split(b'\0')
                    if data[0].decode() == user:
                        target = (data[1].decode(), int(data[2].decode()))
                        break
                if not target:
                    print("USER NOT FOUND")
                    return client.RC.USER_ERROR

            # Connect to target user
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as fs:
                fs.connect(target)
                fs.sendall(b'GET_FILE\0' + remote_file.encode() + b'\0')
                response = fs.recv(1)
                if not response or response[0] != 0:
                    print("GET_FILE FAIL")
                    return client.RC.ERROR

                size = int(fs.recv(1024).split(b'\0')[0].decode())
                received = 0
                with open(local_file, 'wb') as f:
                    while received < size:
                        data = fs.recv(min(4096, size - received))
                        if not data:
                            break
                        f.write(data)
                        received += len(data)
                if received == size:
                    print("GET_FILE OK")
                    return client.RC.OK
                else:
                    os.remove(local_file)
                    print("GET_FILE FAIL")
                    return client.RC.ERROR
        except Exception as e:
            print("GET_FILE FAIL")
            return client.RC.ERROR



    # *

    # **

    # * @brief Command interpreter for the client. It calls the protocol functions.

    @staticmethod

    def shell():



        while (True) :

            try :

                command = input("c> ")

                line = command.split(" ")

                if (len(line) > 0):



                    line[0] = line[0].upper()



                    if (line[0]=="REGISTER") :

                        if (len(line) == 2) :

                            client.register(line[1])

                        else :

                            print("Syntax error. Usage: REGISTER <userName>")



                    elif(line[0]=="UNREGISTER") :

                        if (len(line) == 2) :

                            client.unregister(line[1])

                        else :

                            print("Syntax error. Usage: UNREGISTER <userName>")



                    elif(line[0]=="CONNECT") :

                        if (len(line) == 2) :

                            client.connect(line[1])

                        else :

                            print("Syntax error. Usage: CONNECT <userName>")

                    

                    elif(line[0]=="PUBLISH") :

                        if (len(line) >= 3) :

                            #  Remove first two words

                            description = ' '.join(line[2:])

                            client.publish(line[1], description)

                        else :

                            print("Syntax error. Usage: PUBLISH <fileName> <description>")



                    elif(line[0]=="DELETE") :

                        if (len(line) == 2) :

                            client.delete(line[1])

                        else :

                            print("Syntax error. Usage: DELETE <fileName>")



                    elif(line[0]=="LIST_USERS") :

                        if (len(line) == 1) :

                            client.listusers()

                        else :

                            print("Syntax error. Use: LIST_USERS")



                    elif(line[0]=="LIST_CONTENT") :

                        if (len(line) == 2) :

                            client.listcontent(line[1])

                        else :

                            print("Syntax error. Usage: LIST_CONTENT <userName>")



                    elif(line[0]=="DISCONNECT") :

                        if (len(line) == 2) :

                            client.disconnect(line[1])

                        else :

                            print("Syntax error. Usage: DISCONNECT <userName>")



                    elif(line[0]=="GET_FILE") :

                        if (len(line) == 4) :

                            client.getfile(line[1], line[2], line[3])

                        else :

                            print("Syntax error. Usage: GET_FILE <userName> <remote_fileName> <local_fileName>")



                    elif(line[0]=="QUIT") :

                        if (len(line) == 1) :

                            break

                        else :

                            print("Syntax error. Use: QUIT")

                    else :

                        print("Error: command " + line[0] + " not valid.")

            except Exception as e:

                print("Exception: " + str(e))



    # *

    # * @brief Prints program usage

    @staticmethod

    def usage() :

        print("Usage: python3 client.py -s <server> -p <port>")





    # *

    # * @brief Parses program execution arguments

    @staticmethod

    def  parseArguments(argv) :

        parser = argparse.ArgumentParser()

        parser.add_argument('-s', type=str, required=True, help='Server IP')

        parser.add_argument('-p', type=int, required=True, help='Server Port')

        args = parser.parse_args()



        if (args.s is None):

            parser.error("Usage: python3 client.py -s <server> -p <port>")

            return False



        if ((args.p < 1024) or (args.p > 65535)):

            parser.error("Error: Port must be in the range 1024 <= port <= 65535");

            return False;

        

        client._server = args.s

        client._port = args.p



        return True





    # ******************** MAIN *********************

    @staticmethod

    def main(argv) :

        if (not client.parseArguments(argv)) :

            client.usage()

            return



        #  Write code here

        client.shell()

        print("+++ FINISHED +++")

    



if __name__=="__main__":

    client.main([])