// operaciones.h
#ifndef OPERACIONES_H
#define OPERACIONES_H

#include "msg.h"

int register_user(const char* username);
int unregister_user(const char* username);
int connect_user(const char* username, const char* ip, int puerto);
int disconnect_user(const char* username);
int publish_file(const char* username, const char* filename, const char* descripcion);
int delete_file(const char* username, const char* filename);
int list_users(const char* requesting_user, char* buffer, int buffer_size);
int list_content(const char* requesting_user, const char* target_user, char* buffer, int buffer_size);
int prepare_file_transfer(const char* username, const char* filename, char* datos);
int is_user_connected(const char* username);
int user_exists(const char* username);

extern pthread_mutex_t claves_mutex;
#endif