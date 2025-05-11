# -*- coding: utf-8 -*-
import socket
import argparse
import os
import threading
import struct
from enum import Enum
import requests

def obtener_fecha_hora():
    try:
        r = requests.get("http://127.0.0.1:8000/get_time")
        return r.text.strip()
    except:
        return "00/00/0000 00:00:00"


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
    _listening_socket = None
    _listening_thread = None
    _stop_listening = False



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
                target_user = b'\x00' * 256      # Campo vacío
                fecha = obtener_fecha_hora().encode().ljust(20, b'\x00')
                puerto = 0                       # No relevante para REGISTER

                # 2. Empaquetar con struct.pack
                packed_data = struct.pack(
                    "!B256s256s256s256s20sH",
                    operacion,
                    usuario,
                    nombre_fichero,
                    descripcion,
                    target_user,
                    fecha,
                    puerto
                )
                
                # 3. Enviar y recibir respuesta
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
                
                # 1. Preparar datos según estructura peticion
                operacion = 0  # OP_REGISTER = 0
                usuario = user.encode().ljust(256, b'\x00')  # 256 bytes
                nombre_fichero = b'\x00' * 256  # Campo vacío
                descripcion = b'\x00' * 256      # Campo vacío
                target_user = b'\x00' * 256      # Campo vacío
                puerto = 0                       # No relevante para REGISTER

                # 2. Empaquetar con struct.pack
                packed_data = struct.pack(
                    "!B256s256s256s256si",
                    operacion,
                    usuario,
                    nombre_fichero,
                    descripcion,
                    target_user,
                    puerto
                )
                
                # 3. Enviar y recibir respuesta
                s.sendall(packed_data)
                response = s.recv(1)
                code = response[0] if response else 2

            # 2. Cerrar socket de escucha y detener hilo
            if hasattr(client, '_listening_socket') and client._listening_socket:
                client._stop_listening = True
                client._listening_socket.close()
                if client._listening_thread:
                    client._listening_thread.join()
                client._listening_socket = None

            # 3. Manejar respuesta del servidor
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
            print(f"UNREGISTER FAIL")
            return client.RC.ERROR





    

    @staticmethod
    def connect(user):
        try:
            # Cerrar socket existente si hay uno activo
            if client._listening_socket:
                client._stop_listening = True
                client._listening_socket.close()
                client._listening_thread.join()
            # 1. Crear socket de escucha y obtener puerto
            client._listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client._listening_socket.bind(('', 0))
            port = client._listening_socket.getsockname()[1]
            client._listening_socket.listen(5)
            client._stop_listening = False  # Resetear bandera

            # 2. Iniciar hilo de escucha en segundo plano
            def listen_for_transfers():
                while not client._stop_listening:
                    try:
                        conn, addr = client._listening_socket.accept()
                        # 1. Recibir datos empaquetados (operación 8)
                        data = conn.recv(1024)
                        
                        # 2. Desempaquetar (formato debe coincidir con el del cliente)
                        try:
                            unpacked = struct.unpack("!B256s256s", data[:513])  # 1B + 256s + 256s
                            operacion, usuario, nombre_fichero = unpacked
                            usuario = usuario.decode().strip('\x00')
                            nombre_fichero = nombre_fichero.decode().strip('\x00')
                        except Exception as e:
                            print(f"[PEER ERROR] Fallo al desempaquetar: {e}")
                            conn.sendall(bytes([2]))  # Código de error
                            conn.close()
                            continue

                        # 3. Verificar operación GET_FILE (código 8)
                        if operacion == 8:
                            # 4. Buscar archivo localmente
                            if os.path.exists(nombre_fichero):
                                # Enviar código de éxito (0)
                                conn.sendall(bytes([0]))
                                # Enviar tamaño del archivo seguido de \0
                                file_size = os.path.getsize(nombre_fichero)
                                conn.sendall(str(file_size).encode() + b'\x00')
                                # Enviar contenido del archivo
                                with open(nombre_fichero, 'rb') as f:
                                    conn.sendall(f.read())
                            else:
                                # Enviar código de error (1 = archivo no existe)
                                conn.sendall(bytes([1]))
                        else:
                            # Operación no soportada
                            conn.sendall(bytes([2]))
                        conn.close()
                    except (OSError, ConnectionAbortedError) as e:
                        break

            import threading
            client._listening_thread = threading.Thread(target=listen_for_transfers)
            client._listening_thread.daemon = True
            client._listening_thread.start()

            # 3. Enviar petición CONNECT al servidor
            operacion = 2  # OP_CONNECT
            usuario = user.encode().ljust(256, b'\x00')
            nombre_fichero = b'\x00' * 256
            descripcion = b'\x00' * 256
            target_user = b'\x00' * 256
            puerto_network = port  # 2 bytes
            packed_data = struct.pack(
                "!B256s256s256s256sH",  # H = unsigned short (2 bytes)
                operacion,
                usuario,
                nombre_fichero,
                descripcion,
                target_user,
                fecha,
                puerto_network
            )

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((client._server, client._port))
                s.sendall(packed_data)
                response = s.recv(1)
                code = response[0] if response else 3

                if code == 0:
                    client._connected_user = user
                    print("CONNECT OK")
                    return client.RC.OK
                elif code == 1:
                    print("CONNECT FAIL, USER DOES NOT EXIST")
                    return client.RC.USER_ERROR
                elif code == 2:
                    print("USER ALREADY CONNECTED")
                    return client.RC.ERROR
                else:
                    # Si falla, cerrar socket de escucha
                    client._stop_listening = True
                    client._listening_socket.close()
                    print("CONNECT FAIL")
                    return client.RC.ERROR

        except Exception as e:
            print(f"CONNECT FAIL")
            if client._listening_socket:
                client._stop_listening = True
                client._listening_socket.close()
            return client.RC.ERROR





    

    @staticmethod
    def disconnect(user):
        try:
            # 1. Preparar datos de la petición (misma estructura que connect)
            operacion = 3  # OP_DISCONNECT
            usuario = user.encode().ljust(256, b'\x00')
            nombre_fichero = b'\x00' * 256  # Campo vacío pero necesario
            descripcion = b'\x00' * 256     # Campo vacío pero necesario
            target_user = b'\x00' * 256
            fecha = obtener_fecha_hora().encode().ljust(20, b'\x00')
            puerto = 0  # No se usa en disconnect, pero es parte de la estructura

            # 2. Empaquetar todos los campos (igual que en connect)
            packed_data = struct.pack(
                "!B256s256s256s256s20sH",  # Mismo formato: B + 3*256s + H
                operacion,
                usuario,
                nombre_fichero,
                descripcion,
                target_user,
                fecha,
                puerto
            )

            # 3. Enviar y recibir respuesta
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((client._server, client._port))
                s.sendall(packed_data)
                response = s.recv(1)
                code = response[0] if response else 3

                if code == 0:
                    # Eliminar referencia a _server_socket (no usado)
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
            print(f"DISCONNECT FAIL")
            return client.RC.ERROR



    @staticmethod
    def publish(fileName, description):
        try:
            if not client._connected_user:
                print("PUBLISH FAIL, USER NOT CONNECTED")
                return client.RC.ERROR
            
            # Validación de longitud en el cliente antes de enviar
            try:
                fileName_bytes = fileName.encode()
                description_bytes = description.encode()

                # Comprobar longitud del nombre de archivo
                if len(fileName_bytes) > 256:
                    print("PUBLISH FAIL")
                    return client.RC.ERROR

                # Comprobar longitud de la descripción
                if len(description_bytes) > 256:
                    print("PUBLISH FAIL")
                    return client.RC.ERROR

            except UnicodeEncodeError:
                print("PUBLISH FAIL")
                return client.RC.ERROR

            # 1. Preparar datos de la petición (misma estructura que connect/disconnect)
            operacion = 4  # OP_PUBLISH (ajusta el código según tu servidor)
            usuario = client._connected_user.encode().ljust(256, b'\x00')
            nombre_fichero = fileName.encode().ljust(256, b'\x00')
            descripcion_pub = description.encode().ljust(256, b'\x00')
            target_user = b'\x00' * 256  # Campo vacío pero necesario
            fecha = obtener_fecha_hora().encode().ljust(20, b'\x00')
            puerto = 0  # No se usa en publish, pero es parte de la estructura

            # 2. Empaquetar todos los campos
            packed_data = struct.pack(
                "!B256s256s256s256s20sH",  # Mismo formato: B + 3*256s + H
                operacion,
                usuario,
                nombre_fichero,
                descripcion_pub,
                target_user,
                fecha,
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
            print(f"PUBLISH FAIL")
            return client.RC.ERROR



    @staticmethod
    def delete(fileName):
        try:
            if not client._connected_user:
                print("DELETE FAIL, USER NOT CONNECTED")
                return client.RC.ERROR
            
            # Validación de longitud en el cliente antes de enviar
            try:
                fileName_bytes = fileName.encode()

                # Comprobar longitud del nombre de archivo
                if len(fileName_bytes) > 256:
                    print("DELETE FAIL")
                    return client.RC.ERROR

            except UnicodeEncodeError:
                print("PUBLISH FAIL")
                return client.RC.ERROR

            # 1. Preparar datos de la petición (misma estructura)
            operacion = 5  # OP_DELETE (ajusta el código según tu servidor)
            usuario = client._connected_user.encode().ljust(256, b'\x00')
            nombre_fichero = fileName.encode().ljust(256, b'\x00')
            descripcion = b'\x00' * 256  # Campo vacío pero necesario
            target_user = b'\x00' * 256  # Campo vacío pero necesario
            fecha = obtener_fecha_hora().encode().ljust(20, b'\x00')
            puerto = 0  # No se usa en delete, pero es parte de la estructura

            # 2. Empaquetar todos los campos
            packed_data = struct.pack(
                "!B256s256s256s256s20sH",  # Mismo formato: B + 3*256s + H
                operacion,
                usuario,
                nombre_fichero,
                descripcion,
                target_user,
                fecha,
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
    def listusers():
        try:
            if not client._connected_user:
                print("LIST_CONTENT FAIL, USER NOT CONNECTED")
                return client.RC.ERROR
        
            # Preparar datos de la operación
            operacion = 6  # OP_LIST_USERS
            usuario = client._connected_user.encode().ljust(256, b'\x00')
            nombre_fichero = b'\x00' * 256
            descripcion = b'\x00' * 256
            target_user = b'\x00' * 256  # Campo vacío pero necesario
            fecha = obtener_fecha_hora().encode().ljust(20, b'\x00')
            puerto = 0

            packed_data = struct.pack(
                "!B256s256s256s256s20sH",
                operacion,
                usuario,
                nombre_fichero,
                descripcion,
                target_user,
                fecha, 
                puerto
            )

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((client._server, client._port))

                s.sendall(packed_data)

                # Leer respuesta (1 byte código + 4 bytes num_elementos + 4096 bytes datos)
                expected_len = 1 + 4 + 4096
                respuesta_data = b''
                while len(respuesta_data) < expected_len:
                    chunk = s.recv(expected_len - len(respuesta_data))
                    if not chunk:
                        return client.RC.ERROR
                    respuesta_data += chunk

                # Extraer campos
                codigo = respuesta_data[0]
                num_elementos = int.from_bytes(respuesta_data[1:5], byteorder='big')
                raw_datos = respuesta_data[5:5+4096]

                # Para ver exactamente qué trozo de datos estás intentando decodificar:
                try:
                    datos = raw_datos.split(b'\0', 1)[0].decode('utf-8', errors='ignore')
                except Exception as e:
                    print(f"LIST_USERS FAIL")
                    datos = ""

                if codigo == 0:
                    print("LIST_USERS OK")
                    if num_elementos == 0:
                        print("No hay usuarios conectados")
                    else:
                        # Parsear datos (formato: "LIST_USERS OK\nuser1 ip puerto\n...")
                        lines = datos.split('\n')
                        if lines and lines[0] == "LIST_USERS OK":
                            for line in lines[1:]:  # Ignorar la cabecera
                                if line.strip():
                                    print(line)
                        else:
                            print(f"LIST_USERS FAIL")

                    return client.RC.OK
                elif codigo == 1:
                    print("LIST_USERS FAIL , USER DOES NOT EXIST")
                    return client.RC.ERROR

                elif codigo == 2:
                    print("LIST_USERS FAIL , USER NOT CONNECTED")
                    return client.RC.ERROR

                else:
                    print("LIST_USERS FAIL")
                    return client.RC.ERROR

        except Exception as e:
            print(f"LIST_USERS FAIL")
            return client.RC.ERROR



    @staticmethod
    def listcontent(user):
        try:
            if not client._connected_user:
                print("LIST_CONTENT FAIL, USER NOT CONNECTED")
                return client.RC.ERROR

            # Empaquetar datos como en listusers
            operacion = 7  # OP_LIST_CONTENT (suponiendo código correcto)
            usuario = client._connected_user.encode().ljust(256, b'\x00')
            nombre_fichero = b'\x00' * 256
            descripcion = b'\x00' * 256
            target_user = user.encode().ljust(256, b'\x00')
            fecha = obtener_fecha_hora().encode().ljust(20, b'\x00')
            puerto = 0

            packed_data = struct.pack(
                "!B256s256s256s256s20sH",
                operacion,
                usuario,
                nombre_fichero,
                descripcion,
                target_user,
                fecha,
                puerto
            )

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((client._server, client._port))
                s.sendall(packed_data)

                # Recibir respuesta estructurada (1 byte código + 4 bytes num_elementos + 4096 datos)
                respuesta_data = s.recv(1 + 4 + 4096)
                if len(respuesta_data) < 1 + 4:
                    print("LIST_CONTENT FAIL")
                    return client.RC.ERROR

                codigo = respuesta_data[0]
                num_elementos = int.from_bytes(respuesta_data[1:5], byteorder='big')
                datos = respuesta_data[5:5+4096].split(b'\0', 1)[0].decode('utf-8')

                if codigo != 0:
                    if codigo == 3:
                        print("LIST_CONTENT FAIL, REMOTE USER DOES NOT EXIST")
                    else:
                        print(f"LIST_CONTENT FAIL")
                    return client.RC.ERROR

                print("LIST_CONTENT OK")
                if num_elementos == 0:
                    print("No hay archivos")
                else:
                    lines = datos.split('\n')
                    if lines and lines[0] == "LIST_CONTENT OK":
                        # Saltar la primera línea ("LIST_CONTENT OK") 
                        # y mostrar solo los nombres de fichero
                        for line in lines[1:]:
                            if line.strip():
                                print(line.strip())  # Elimina espacios en blanco alrededor
                    else:
                        print("LIST_CONTENT FAIL")
                
                return client.RC.OK

        except Exception as e:
            print(f"LIST_CONTENT FAIL")
            return client.RC.ERROR



    @staticmethod
    def getfile(user, remote_file_name, local_file_name):
        try:
            # Paso 1: Obtener IP y puerto del usuario objetivo usando LIST_USERS
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((client._server, client._port))
                
                # Empaquetar petición LIST_USERS según protocolo
                operacion = 6  # OP_LIST_USERS
                usuario = client._connected_user.encode().ljust(256, b'\x00')
                nombre_fichero = b'\x00' * 256
                descripcion = b'\x00' * 256
                target_user = b'\x00' * 256  # Campo vacío pero necesario
                puerto = 0

                packed_data = struct.pack(
                    "!B256s256s256s256sH",
                    operacion,
                    usuario,
                    nombre_fichero,
                    descripcion,
                    target_user,
                    puerto
                )
                s.sendall(packed_data)
                
                
                 # Leer respuesta
                response = s.recv(1)
                if response[0] != 0:
                    print("GET_FILE FAIL")
                    return client.RC.ERROR
                
                # Leer número de usuarios y datos (igual que en listusers)
                num_users = int.from_bytes(s.recv(4), byteorder='big')

                # Leer 4096 bytes de datos (como en listusers)
                raw_data = s.recv(4096)

                # Decodificar y procesar igual que listusers
                try:
                    data_str = raw_data.split(b'\0', 1)[0].decode('utf-8', errors='ignore')
                except Exception as e:
                    return client.RC.ERROR

                lines = data_str.split('\n')
                
                target_ip, target_port = None, None
                if lines and lines[0] == "LIST_USERS OK":
                    for line in lines[1:]:  # Ignorar cabecera
                        if line.strip() == "":
                            continue
                        parts = line.split()
                        if len(parts) < 3:
                            continue
                        current_user, ip, port_str = parts[0], parts[1], parts[2]
                        if current_user == user:
                            target_ip = ip
                            target_port = int(port_str)
                            break
                
                if not target_ip:
                    print(f"GET_FILE FAIL)")
                    return client.RC.USER_ERROR

            # Paso 2: Conectar al cliente objetivo y solicitar archivo
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as fs:
                fs.connect((target_ip, target_port))
                # Enviar comando GET FILE con formato empaquetado
                # Enviar comando GET FILE con formato empaquetado CORREGIDO
                operacion = 8  # Código 8
                usuario = client._connected_user.encode().ljust(256, b'\x00')
                nombre_fichero = remote_file_name.encode().ljust(256, b'\x00')

                # !B (1 byte) + 256s (usuario) + 256s (nombre_fichero)
                packed_data = struct.pack(
                    "!B256s256s",  # <-- Solo los campos necesarios
                    operacion,
                    usuario,
                    nombre_fichero
                )
                fs.sendall(packed_data)
                
                # Leer código de respuesta
                response_code = fs.recv(1)
                if not response_code or response_code[0] != 0:
                    if response_code and response_code[0] == 1:
                        print("GET_FILE FAIL (Archivo no existe)")
                    else:
                        print("GET_FILE FAIL , FILE NOT EXIST")
                    return client.RC.ERROR
                
                # Leer tamaño del archivo (cadena hasta \0)
                size_buffer = b''
                while True:
                    chunk = fs.recv(1)
                    if chunk == b'\0':
                        break
                    size_buffer += chunk
                file_size = int(size_buffer.decode())
                
                # Recibir contenido del archivo
                received = 0
                with open(local_file_name, 'wb') as f:
                    while received < file_size:
                        data = fs.recv(min(4096, file_size - received))
                        if not data:
                            break
                        f.write(data)
                        received += len(data)
                
                # Verificar integridad
                if received == file_size:
                    print("GET_FILE OK")
                    return client.RC.OK
                else:
                    os.remove(local_file_name)
                    print("GET_FILE FAIL")
                    return client.RC.ERROR

        except Exception as e:
            print(f"GET_FILE FAIL: {str(e)}")
            if os.path.exists(local_file_name):
                os.remove(local_file_name)
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