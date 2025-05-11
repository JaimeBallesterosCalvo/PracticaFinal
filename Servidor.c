#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <signal.h>
#include <pthread.h>
#include "comm.h" //lo usamos para crear socket TCP (socket(), bind(), listen())
#include "operaciones.h"
#include <ifaddrs.h>

// Esta es la función para implementar el Ctrl +C
void limpiar_y_salir(int signum) {
    (void)signum;
    printf("\nSERVIDOR: Capturada señal SIGINT (Ctrl+C). Finalizando...\n");
    pthread_mutex_destroy(&claves_mutex);
    printf("SERVIDOR: Mutex destruido.\n");
    exit(0);
}

void *atender_cliente(void *arg) {
    int client_fd = *(int *)arg;
    free(arg);

    peticion p;
    respuesta r;
    int user_count;
    memset(&r, 0, sizeof(r)); // se inicializa la respuesta con valores 0

    // 1. Recibir petición y hacer unmarshalling
    if (recvMessage(client_fd, (char *)&p, sizeof(peticion)) < 0) {
        perror("Error en recvMessage");
        close(client_fd);
        return NULL;
    }

    // Unmarshalling de campos de 4 bytes (puerto)
    p.puerto = ntohs(p.puerto);

    // Mapear código de operación a string
    const char *op_str;
    switch (p.operacion) {
        case OP_REGISTER:    op_str = "REGISTER"; break;
        case OP_UNREGISTER:  op_str = "UNREGISTER"; break;
        case OP_CONNECT:     op_str = "CONNECT"; break;
        case OP_DISCONNECT:  op_str = "DISCONNECT"; break;
        case OP_PUBLISH:     op_str = "PUBLISH"; break;
        case OP_DELETE:      op_str = "DELETE"; break;
        case OP_LIST_USERS:  op_str = "LIST_USERS"; break;
        case OP_LIST_CONTENT:op_str = "LIST_CONTENT"; break;
        default:             op_str = "UNKNOWN"; break;
    }

    // Mostrar operación y usuario
    printf("OPERATION %s FROM %s\n", op_str, p.usuario);
    fflush(stdout);

    // 2. Obtener IP del cliente para mandarla en algún lado
    struct sockaddr_in client_addr;
    socklen_t addr_len = sizeof(client_addr);
    getpeername(client_fd, (struct sockaddr*)&client_addr, &addr_len);
    char client_ip[INET_ADDRSTRLEN];
    inet_ntop(AF_INET, &client_addr.sin_addr, client_ip, INET_ADDRSTRLEN);

    fflush(stdout);

    // 3. Procesar la operación
    switch(p.operacion) {
        case OP_REGISTER:
            pthread_mutex_lock(&claves_mutex);
            r.codigo = register_user(p.usuario);
            if (r.codigo != 0) {
                fprintf(stderr, "Error en register_user()\n");
            }
            pthread_mutex_unlock(&claves_mutex);
            break;

        case OP_UNREGISTER:
            pthread_mutex_lock(&claves_mutex);
            r.codigo = unregister_user(p.usuario);
            if (r.codigo != 0) {
                fprintf(stderr, "Error en unregister_user()\n");
            }
            pthread_mutex_unlock(&claves_mutex);
            break;

        case OP_CONNECT:
            pthread_mutex_lock(&claves_mutex);
            r.codigo = connect_user(p.usuario, client_ip, p.puerto);
            if (r.codigo != 0) {
                fprintf(stderr, "Error en connect_user()\n");
            }
            pthread_mutex_unlock(&claves_mutex);
            break;

        case OP_DISCONNECT:
            pthread_mutex_lock(&claves_mutex);
            r.codigo = disconnect_user(p.usuario);
            if (r.codigo != 0) {
                fprintf(stderr, "Error en disconnect_user()\n");
            }
            pthread_mutex_unlock(&claves_mutex);
            break;

        case OP_PUBLISH:
            pthread_mutex_lock(&claves_mutex);
            r.codigo = publish_file(p.usuario, p.nombre_fichero, p.descripcion);
            if (r.codigo != 0) {
                fprintf(stderr, "Error en publish_file()\n");
            }
            pthread_mutex_unlock(&claves_mutex);
            break;

        case OP_DELETE:
            pthread_mutex_lock(&claves_mutex);
            r.codigo = delete_file(p.usuario, p.nombre_fichero);
            if (r.codigo != 0) {
                fprintf(stderr, "Error en delete_file()\n");
            }
            pthread_mutex_unlock(&claves_mutex);
            break;

        case OP_LIST_USERS:
            pthread_mutex_lock(&claves_mutex);
            user_count = list_users(p.usuario, r.datos, sizeof(r.datos));
            if (user_count < 0) {
                r.codigo = -user_count; // Convierte códigos negativos a positivos
                r.num_elementos = 0;
            } else {
                r.codigo = 0;
                r.num_elementos = htonl(user_count);
                fprintf(stdout, "LIST_USERS OK\n");
            }
            pthread_mutex_unlock(&claves_mutex);
            break;

        case OP_LIST_CONTENT:
            pthread_mutex_lock(&claves_mutex);
            int content_count = list_content(p.usuario, p.target_user, r.datos, sizeof(r.datos));
            if (content_count < 0) { // Si usaras códigos de error negativos
                r.codigo = -content_count;
                r.num_elementos = 0;
            } else {
                r.codigo = 0;
                r.num_elementos = htonl(content_count);
                fprintf(stdout, "LIST_CONTENT OK\n");
            }
            pthread_mutex_unlock(&claves_mutex);
            break;

        default:
            r.codigo = -1;
            fprintf(stderr, "Operación desconocida: %d\n", p.operacion);
            break;
    }

    // 4. Marshalling de campos
    r.num_elementos = htonl(r.num_elementos);

    // 5. Enviar respuesta
    if (sendMessage(client_fd, (char *)&r, sizeof(respuesta)) < 0) {
        perror("Error en sendMessage");
    }

    close(client_fd);
    return NULL;
}

int main(int argc, char *argv[]) {
    // Se introduce la condición de que se salga con Ctrl + C
    signal(SIGINT, limpiar_y_salir);

    //se comprueba que el formato para iniciar es el de ./servidor -p <puerto>
    if (argc != 3 || strcmp(argv[1], "-p") != 0) {
        fprintf(stderr, "Uso: %s -p <puerto>\n", argv[0]);
        exit(EXIT_FAILURE);
    }
    //esto además comprueba que el puerto no es un número negativo ni es un puerto inválido y pone al puerto en una variable
    int port = atoi(argv[2]);
    if (port <= 0 || port > 65535) {
        fprintf(stderr, "Error: puerto inválido\n");
        exit(EXIT_FAILURE);
    }

    // Creamos el socket del servidor con comm y lo dejamos listo para aceptar conexiones (socket + bind + listen)
    int server_fd = serverSocket(INADDR_ANY, port, SOCK_STREAM);
    if (server_fd < 0) {
        fprintf(stderr, "Error al iniciar el socket del servidor\n");
        exit(EXIT_FAILURE);
    }

    struct ifaddrs *ifaddr, *ifa;

    if (getifaddrs(&ifaddr) == -1) {
        perror("getifaddrs");
        exit(EXIT_FAILURE);
    }

    char server_ip[INET_ADDRSTRLEN] = "127.0.0.1";  // Valor por defecto

    for (ifa = ifaddr; ifa != NULL; ifa = ifa->ifa_next) {
        if (ifa->ifa_addr == NULL || ifa->ifa_addr->sa_family != AF_INET) {
            continue;
        }

        struct sockaddr_in *addr = (struct sockaddr_in *)ifa->ifa_addr;
        const char *ip = inet_ntoa(addr->sin_addr);

        // Filtrar por nombre de interfaz (ej: eth0 en WSL2)
        if (strcmp(ifa->ifa_name, "eth0") == 0) {
            strncpy(server_ip, ip, sizeof(server_ip));
            break;  // Nos quedamos con la primera coincidencia
        }
    }

    freeifaddrs(ifaddr);

    printf("s> init server %s:%d\n", server_ip, port);
    printf("s> ");
    fflush(stdout);

    while (1) {
        //espera y acepta una nueva conexión
        int client_fd = serverAccept(server_fd);
        if (client_fd < 0) {
            perror("serverAccept");
            continue;
        }

        int *client_fd_ptr = malloc(sizeof(int));
        *client_fd_ptr = client_fd;

        pthread_t hilo;
        pthread_create(&hilo, NULL, atender_cliente, client_fd_ptr);
        pthread_detach(hilo);

    }
    return 0;
}