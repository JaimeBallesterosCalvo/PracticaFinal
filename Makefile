# Compilador y flags
CC = gcc
CFLAGS = -Wall -Wextra -pthread -I.
PYTHON = python3

# Nombres de los ejecutables
SERVER_EXEC = servidor
CLIENT_EXEC = cliente.py

# Archivos fuente y cabeceras
SERVER_SRCS = Servidor.c operaciones.c comm.c
SERVER_OBJS = $(SERVER_SRCS:.c=.o)
HEADERS = comm.h msg.h operaciones.h

.PHONY: all clean server client run_server run_client

all: server client

server: $(SERVER_EXEC)

$(SERVER_EXEC): $(SERVER_OBJS)
	$(CC) $(CFLAGS) -o $@ $^

%.o: %.c $(HEADERS)
	$(CC) $(CFLAGS) -c $< -o $@

client:
	@echo "El cliente es un script Python, no necesita compilación"
	@echo "Ejecutar con: $(PYTHON) $(CLIENT_EXEC) -s <servidor> -p <puerto>"

clean:
	rm -f $(SERVER_EXEC) $(SERVER_OBJS)
	@echo "Limpieza completada"

run_server: server
	./$(SERVER_EXEC) -p 8080

run_client: client
	$(PYTHON) $(CLIENT_EXEC) -s localhost -p 8080