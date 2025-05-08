#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dirent.h>
#include <sys/stat.h>
#include <unistd.h>
#include <pthread.h>
#include "msg.h"
#include <fcntl.h>
#include <errno.h>


#define BASE_DIR "USERS"
#define MAX_PATH 1024
#define MAX_LINE 512

pthread_mutex_t claves_mutex = PTHREAD_MUTEX_INITIALIZER;

/* ------------------ Funciones auxiliares ------------------ */
//esto sirve para crear el directorio base
int create_base_dir() {
    struct stat st = {0};
    if (stat(BASE_DIR, &st) == -1) {
        return mkdir(BASE_DIR, 0700);
    }
    return 0;
}

//verifique si un usario está registrado en el directorio
int user_exists(const char* username) {
    struct stat st;
    char path[MAX_PATH];
    snprintf(path, sizeof(path), "%s/%s", BASE_DIR, username);
    return (stat(path, &st) == 0 && S_ISDIR(st.st_mode));
}

//crea el lugar donde se va a guardar el contenido publicado por el usuario
int create_metadata(const char* username) {
    char path[MAX_PATH];
    snprintf(path, sizeof(path), "%s/%s/metadata.txt", BASE_DIR, username);
    return creat(path, 0644);
}

//comprueba si está conectado el usuario o no
int is_user_connected(const char* username) {
    char path[MAX_PATH];
    snprintf(path, sizeof(path), "%s/%s/connection.txt", BASE_DIR, username);
    return (access(path, F_OK) == 0);
}


/* ------------------ Operaciones principales ------------------ */
//operación de registrarse
int register_user(const char* username) {
    // 0. Crear directorio base USERS si no existe, que este es el general para empezar
    if (create_base_dir() != 0) {
        fprintf(stderr, "[ERROR] No se pudo crear el directorio base 'USERS'\ns> ");
        return 2;
    }

    // 1. Verificar longitud del nombre
    size_t username_len = strlen(username);
    if (username_len >= MAX_USER) {
        fprintf(stderr, "[ERROR] Nombre demasiado largo (%zu caracteres). Máximo permitido: %d\ns> ", username_len, MAX_USER-1);
        fflush(stdout);
        return 2;
    }

    // 2. Verificar si el usuario ya existe
    if (user_exists(username)) {
        fprintf(stderr, "[ERROR] El usuario '%s' ya está registrado\ns> ", username);
        return 1;
    }

    // 3. Crear directorio del usuario dentro de la carpeta USERS
    char path[MAX_PATH];
    snprintf(path, sizeof(path), "%s/%s", BASE_DIR, username);
    fflush(stdout);

    if (mkdir(path, 0700) != 0) {
        fprintf(stderr, "[ERROR] Fallo al crear directorio (%s). Código: %d\ns> ",
                strerror(errno), errno);
        return 2;
    }
    fflush(stdout);

    // 4. Crear metadata
    if (create_metadata(username) == -1) {
        fprintf(stderr, "[ERROR] Fallo al crear metadata para '%s'\ns> ", username);
        // Intentar limpiar el directorio creado
        rmdir(path);
        return 2;
    }

    // 5. Registro completo
    fprintf(stdout, "s> REGISTER OK\ns> ");
    fflush(stdout);

    return 0;
}

//operación de darse de baja
int unregister_user(const char* username) {
    // Crear directorio base USERS si no existe, que este es el general para empezar
    if (create_base_dir() != 0) {
        fprintf(stderr, "[ERROR] No se pudo crear el directorio base 'USERS'\ns> ");
        return 2;
    }

    // Comprueba que el usuario existe en el directorio
    if (!user_exists(username)) {
        fprintf(stderr,"s> USER DOES NOT EXIST\ns> ");
        pthread_mutex_unlock(&claves_mutex);
        return 1;
    }

    // Elimina al usuario del directorio USERS
    char command[MAX_PATH];
    snprintf(command, sizeof(command), "rm -rf %s/%s", BASE_DIR, username);

    if (system(command) != 0) {
        fprintf(stderr,"UNREGISTER FAIL\ns> ");
        return 2;
    }
    fprintf(stdout,"UNREGISTER OK\ns> ");
    fflush(stdout);
    return 0;
}

//operación de conectarse
//realmente lo que hace es escribir su conexión a un txt que está en el servidor
int connect_user(const char* username, const char* ip, int puerto) {
    // 0. Crear directorio base USERS si no existe, que este es el general para empezar
    if (create_base_dir() != 0) {
        fprintf(stderr, "[ERROR] No se pudo crear el directorio base 'USERS'\ns> ");
        return 2;
    }

    // 1. Verificar si el usuario está registrado
    if (!user_exists(username)) {
        fprintf(stderr,"CONNECT FAIL , USER DOES NOT EXIST\ns> ");
        return 1;
    }

    char path[MAX_PATH];
    snprintf(path, sizeof(path), "%s/%s/connection.txt", BASE_DIR, username);

    // 2. Verificar si ya existe conexión activa
    if (access(path, F_OK) == 0) {
        fprintf(stderr,"USER ALREADY CONNECTED\ns> ");
        return 2;
    }

    FILE *fd;
    if ((fd = fopen(path, "w")) == NULL) {
        fprintf(stderr,"CONNECT FAIL\n s> ");
        return 3;
    }

    fprintf(fd, "%s\n%d", ip, puerto);
    fclose(fd);

    fprintf(stdout,"CONNECT OK\ns> ");
    return 0;
}

//operación de darse de baja
//realmente lo que hace es borrarse de la lista de conexiones
int disconnect_user(const char* username) {
    // 0. Crear directorio base USERS si no existe, que este es el general para empezar
    if (create_base_dir() != 0) {
        fprintf(stderr, "[ERROR] No se pudo crear el directorio base 'USERS'\ns> ");
        return 3;
    }

    //verifica si el usuario existe
    if (!user_exists(username)) {
        fprintf(stderr,"DISCONNECT FAIL, USER DOES NOT EXIST\ns> ");
        return 1;
    }

    // 2. Verificar si el usuario está conectado
    if (!is_user_connected(username)) {
        fprintf(stderr,"DISCONNECT FAIL , USER NOT CONNECTED\ns> ");
        return 2; // USER NOT CONNECTED
    }

    char path[MAX_PATH];
    snprintf(path, sizeof(path), "%s/%s/connection.txt", BASE_DIR, username);

    if (remove(path) != 0) {
        fprintf(stderr,"DISCONNECT FAIL\ns> ");
        return 3;
    }

    fprintf(stdout, "DISCONNECT OK\ns> ");
    return 0;
}

//esta es la acción de publicar un documento
// Función para publicar un documento (sin crear el archivo físicamente)
int publish_file(const char* username, const char* filename, const char* descripcion) {

    // 1. Verificar si el usuario existe
    if (!user_exists(username)) {
        fprintf(stderr, "PUBLISH FAIL, USER DOES NOT EXIST\n");
        return 1;
    }

    // 2. Verificar si el usuario está conectado
    if (!is_user_connected(username)) {
        fprintf(stderr, "PUBLISH FAIL, USER NOT CONNECTED\n");
        return 2;
    }

    // 3. Verificar si el archivo ya está publicado
    char meta_path[MAX_PATH];
    snprintf(meta_path, sizeof(meta_path), "%s/%s/metadata.txt", BASE_DIR, username);

    FILE *meta_fd = fopen(meta_path, "r");
    if (meta_fd) {
        char line[MAX_LINE];
        while (fgets(line, sizeof(line), meta_fd)) {
            char current_file[MAX_FILE];
            if (sscanf(line, "%[^|]", current_file) == 1) {
                if (strcmp(current_file, filename) == 0) {
                    fclose(meta_fd);
                    fprintf(stderr, "PUBLISH FAIL, CONTENT ALREADY PUBLISHED\n");
                    return 3;
                }
            }
        }
        fclose(meta_fd);
    }

    // 4. Registrar en metadata (¡única acción persistente!)
    if ((meta_fd = fopen(meta_path, "a")) == NULL) {
        fprintf(stderr, "PUBLISH FAIL\n");
        return 4;
    }

    fprintf(meta_fd, "%s|%s\n", filename, descripcion);
    fclose(meta_fd);

    fprintf(stdout, "PUBLISH OK\n");
    return 0;
}

//esta es la operacion para eliminar un archivo
int delete_file(const char* username, const char* filename) {
    // 1. Verificar si el usuario existe
    if (!user_exists(username)) {
        fprintf(stderr, "DELETE FAIL, USER DOES NOT EXIST\n");
        pthread_mutex_unlock(&claves_mutex);
        return 1;
    }

    // 2. Verificar si el usuario está conectado
    if (!is_user_connected(username)) {
        fprintf(stderr, "DELETE FAIL, USER NOT CONNECTED\n");
        return 2;
    }

    // 3. Verificar si el archivo existe en el metadata
    char meta_path[MAX_PATH], temp_path[MAX_PATH];
    snprintf(meta_path, sizeof(meta_path), "%s/%s/metadata.txt", BASE_DIR, username);
    snprintf(temp_path, sizeof(temp_path), "%s/%s/metadata.tmp", BASE_DIR, username);

    int found_in_metadata = 0;
    FILE *meta_fd = fopen(meta_path, "r");
    if (meta_fd) {
        char line[MAX_LINE];
        while (fgets(line, sizeof(line), meta_fd)) {
            char current_file[MAX_FILE];
            if (sscanf(line, "%[^|]", current_file) == 1) {
                if (strcmp(current_file, filename) == 0) {
                    found_in_metadata = 1;
                    break;
                }
            }
        }
        fclose(meta_fd);
    }

    if (!found_in_metadata) {
        fprintf(stderr, "DELETE FAIL, CONTENT NOT PUBLISHED\n");
        return 3;
    }

    // 4. Actualizar metadata (eliminar la entrada)
    meta_fd = fopen(meta_path, "r");
    FILE *temp_fd = fopen(temp_path, "w");
    if (meta_fd == NULL || temp_fd == NULL) {
        if (meta_fd) fclose(meta_fd);
        if (temp_fd) fclose(temp_fd);
        fprintf(stderr, "DELETE FAIL\n");
        return 4;
    }

    char line[MAX_LINE];
    while (fgets(line, sizeof(line), meta_fd)) {
        char current_file[MAX_FILE];
        if (sscanf(line, "%[^|]", current_file) == 1) {
            if (strcmp(current_file, filename) != 0) {
                fputs(line, temp_fd);
            }
        }
    }

    fclose(meta_fd);
    fclose(temp_fd);

    // Reemplazar metadata vieja con la nueva
    remove(meta_path);
    rename(temp_path, meta_path);

    fprintf(stdout, "DELETE OK (solo metadata)\n");
    return 0;
}

//operacion de obtener una lista con todos los usuarios
int list_users(const char* requesting_user, char* buffer, int buffer_size) {
    pthread_mutex_lock(&claves_mutex);

    if (!user_exists(requesting_user) ) {
        fprintf(stderr, "LIST_USERS FAIL , USER DOES NOT EXIST\n");
        pthread_mutex_unlock(&claves_mutex);
        return 1;
    }

    if (!is_user_connected(requesting_user)) {
        fprintf(stderr, "LIST_USERS FAIL , USER NOT CONNECTED \n");
        pthread_mutex_unlock(&claves_mutex);
        return 2;
    }

    DIR *dir;
    struct dirent *ent;
    int count = 0;
    int total_written = 0;

    // Inicializar buffer con el encabezado OK
    int header_written = snprintf(buffer, buffer_size, "LIST_USERS OK\n");
    buffer += header_written;
    buffer_size -= header_written;
    total_written += header_written;

    if ((dir = opendir(BASE_DIR)) == NULL) {
        fprintf(stderr, "LIST_USERS FAIL\n");
        pthread_mutex_unlock(&claves_mutex);
        return 3; // OPERATION FAILED
    }

    while ((ent = readdir(dir)) != NULL && buffer_size > 0) {
        if (ent->d_type == DT_DIR && strcmp(ent->d_name, ".") != 0 && strcmp(ent->d_name, "..") != 0) {
            // Solo listar usuarios conectados
            if (is_user_connected(ent->d_name)) {
                char ip[INET_ADDRSTRLEN];
                int puerto;
                char conn_path[MAX_PATH];
                snprintf(conn_path, sizeof(conn_path), "%s/%s/connection.txt", BASE_DIR, ent->d_name);

                FILE *conn_fd = fopen(conn_path, "r");
                if (conn_fd) {
                    if (fscanf(conn_fd, "%s\n%d", ip, &puerto) == 2) {
                        int written = snprintf(buffer, buffer_size, "%s %s %d\n", ent->d_name, ip, puerto);
                        if (written < 0 || written >= buffer_size) {
                            fclose(conn_fd);
                            closedir(dir);
                            pthread_mutex_unlock(&claves_mutex);
                            fprintf(stderr, "LIST_USERS FAIL\n");
                            return 3; // BUFFER TOO SMALL
                        }
                        buffer += written;
                        buffer_size -= written;
                        total_written += written;
                        count++;
                    }
                    fclose(conn_fd);
                }
            }
        }
    }
    closedir(dir);

    pthread_mutex_unlock(&claves_mutex);

    if (count == 0) {
        // No hay usuarios conectados, pero la operación fue exitosa
        return 0;
    }
    return 0; // SUCCESS
}

//lista para ver el contenido de otra personas
int list_content(const char* requesting_user, const char* target_user, char* buffer, int buffer_size) {
    pthread_mutex_lock(&claves_mutex);

    // 1. Verificar si el usuario que solicita existe
    if (!user_exists(requesting_user)) {
        fprintf(stderr, "LIST_USERS FAIL , USER DOES NOT EXIST\n");
        pthread_mutex_unlock(&claves_mutex);
        return 1; // USER DOES NOT EXIST (usuario que pide)
    }

    // 2. Verificar si el usuario que solicita está conectado
    if (!is_user_connected(requesting_user)) {
        fprintf(stderr, "LIST_CONTENT FAIL , USER NOT CONNECTED\n");
        pthread_mutex_unlock(&claves_mutex);
        return 2; // USER NOT CONNECTED (usuario que pide)
    }

    // 3. Verificar si el usuario objetivo existe
    if (!user_exists(target_user)) {
        fprintf(stderr, "LIST_CONTENT FAIL , REMOTE USER DOES NOT EXIST\n");
        pthread_mutex_unlock(&claves_mutex);
        return 3; // REMOTE USER DOES NOT EXIST
    }

    // Preparar buffer con encabezado
    int written = snprintf(buffer, buffer_size, "LIST_CONTENT OK\n");
    buffer += written;
    buffer_size -= written;
    int count = 0;

    char meta_path[MAX_PATH];
    snprintf(meta_path, sizeof(meta_path), "%s/%s/metadata.txt", BASE_DIR, target_user);

    FILE *meta_fd = fopen(meta_path, "r");
    if (!meta_fd) {
        fprintf(stderr, "LIST_CONTENT FAIL\n");
        pthread_mutex_unlock(&claves_mutex);
        return 4; // OPERATION FAILED
    }

    char line[MAX_LINE];
    while (fgets(line, sizeof(line), meta_fd) && buffer_size > 0) {
        char *separator = strchr(line, '|');
        if (separator) {
            *separator = '\0'; // Separa nombre y descripción
            char *filename = line;
            char *description = separator + 1;

            // Eliminar salto de línea de la descripción
            char *newline = strchr(description, '\n');
            if (newline) *newline = '\0';

            written = snprintf(buffer, buffer_size, "%s: %s\n", filename, description);
            if (written < 0 || written >= buffer_size) {
                fclose(meta_fd);
                fprintf(stderr, "LIST_CONTENT FAIL\n");
                pthread_mutex_unlock(&claves_mutex);
                return 4; // BUFFER TOO SMALL
            }
            buffer += written;
            buffer_size -= written;
            count++;
        }
    }
    fclose(meta_fd);

    pthread_mutex_unlock(&claves_mutex);
    return (count > 0) ? 0 : 0; // 0 = éxito (incluso si count es 0)
}

//preparacion para que un cliente tenga todos los datos para pedir el archico al otro
int prepare_file_transfer(const char* username, const char* filename, char* datos) {
    pthread_mutex_lock(&claves_mutex);

    // Obtener info de conexión
    char conn_path[MAX_PATH], meta_path[MAX_PATH], file_path[MAX_PATH];
    FILE *conn_fd, *meta_fd;
    int puerto;
    char ip[INET_ADDRSTRLEN];

    snprintf(conn_path, sizeof(conn_path), "%s/%s/connection.txt", BASE_DIR, username);
    snprintf(meta_path, sizeof(meta_path), "%s/%s/metadata.txt", BASE_DIR, username);
    snprintf(file_path, sizeof(file_path), "%s/%s/%s", BASE_DIR, username, filename);

    // Verificar existencia
    if (!user_exists(username) || access(file_path, F_OK) != 0) {
        fprintf(stderr, "GET_FILE FAIL , FILE NOT EXIST\n");
        pthread_mutex_unlock(&claves_mutex);
        return 1;
    }

    // Leer datos de conexión
    if ((conn_fd = fopen(conn_path, "r")) == NULL) {
        fprintf(stderr, "GET_FILE FAIL\n");
        pthread_mutex_unlock(&claves_mutex);
        return 2;
    }

    fscanf(conn_fd, "%s\n%d", ip, &puerto);
    fclose(conn_fd);

    // Leer descripción del archivo
    if ((meta_fd = fopen(meta_path, "r")) == NULL) {
        fprintf(stderr, "GET_FILE FAIL\n");
        pthread_mutex_unlock(&claves_mutex);
        return 2;
    }

    char line[MAX_LINE], desc[MAX_DESC] = "";
    while (fgets(line, sizeof(line), meta_fd)) {
        char current_file[MAX_FILE];
        if (sscanf(line, "%[^|]|%[^\n]", current_file, desc) == 2) {
            if (strcmp(current_file, filename) == 0) break;
        }
    }
    fclose(meta_fd);

    // Formatear datos de transferencia
    snprintf(datos, 4096, "%s:%d:%s:%s", ip, puerto, filename, desc);

    pthread_mutex_unlock(&claves_mutex);
    return 0;
}