#ifndef MSG_H
#define MSG_H

#include <stdint.h>
#include <arpa/inet.h>

#define MAX_USER 256
#define MAX_FILE 256
#define MAX_DESC 256
#define MAX_FECHA 20

typedef enum {
    OP_REGISTER,      // 0
    OP_UNREGISTER,    // 1
    OP_CONNECT,       // 2
    OP_DISCONNECT,    // 3
    OP_PUBLISH,       // 4
    OP_DELETE,        // 5
    OP_LIST_USERS,    // 6
    OP_LIST_CONTENT,  // 7
    OP_GET_FILE       // 8
} p2p_operation;

#pragma pack(push, 1)  // Desactiva el padding
typedef struct {
    uint8_t operacion;          // 1 byte
    char usuario[MAX_USER];     // 256 bytes
    char nombre_fichero[MAX_FILE]; // 256 bytes
    char descripcion[MAX_DESC]; // 256 bytes
    char target_user[MAX_USER];     // 256 bytes
    char fecha[MAX_FECHA];     // 20 bytes
    unsigned short puerto;           // 4 bytes (orden de red)
} peticion;
#pragma pack(pop)  // Restaura el padding

#pragma pack(push, 1)  // Desactiva el padding
typedef struct {
    uint8_t codigo;             // 1 bytes
    int32_t num_elementos;      // 4 bytes
    char datos[4096];           // 4096 bytes
} respuesta;
#pragma pack(pop)  // Restaura el padding
#endif
