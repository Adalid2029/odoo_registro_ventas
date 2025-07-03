# Comandos Docker para Odoo - Actualización del Módulo sales_register

## Información de Contenedores

**Contenedores activos:**

- `odoo_registro_ventas-web-1` - Odoo 18.0 (Puerto 8069)
- `odoo_registro_ventas-db-1` - PostgreSQL 15

## Métodos para Actualizar el Módulo sales_register

### Método 1: Acceso al Shell de Odoo

```bash
# Acceder al shell interactivo de Odoo
docker exec -it odoo_registro_ventas-web-1 bash

# Una vez dentro del contenedor, ejecutar el shell de Odoo
odoo shell -d postgres
# o si tu base de datos tiene otro nombre:
# odoo shell -d odoo
```

# Actualizar el módulo sales_register (con base de datos postgres)

docker exec -it odoo_registro_ventas-web-1 odoo -u sales_register -d postgres

# Actualizar el módulo sales_register (con base de datos odoo)

docker exec -it odoo_registro_ventas-web-1 odoo -u sales_register -d odoo

# Actualizar con parada automática después de la inicialización

docker exec -it odoo_registro_ventas-web-1 odoo -u sales_register -d postgres --stop-after-init

# Detener todos los servicios

docker-compose down

# Iniciar solo la base de datos

docker-compose up -d db

# Esperar que la base de datos esté lista

sleep 10

# Ejecutar actualización del módulo con docker-compose

docker-compose run --rm web odoo -u sales_register -d postgres --stop-after-init

# Iniciar todos los servicios

docker-compose up -d

# Reiniciar solo el contenedor web

docker restart odoo_registro_ventas-web-1

# Luego actualizar el módulo

docker exec -it odoo_registro_ventas-web-1 odoo -u sales_register -d postgres --stop-after-init

# Ver todos los contenedores

docker ps

# Ver solo los contenedores de tu proyecto

docker-compose ps

# Ver logs del contenedor web

docker logs odoo_registro_ventas-web-1

# Ver logs de la base de datos

docker logs odoo_registro_ventas-db-1

# Conectar a PostgreSQL

docker exec -it odoo_registro_ventas-db-1 psql -U odoo -d postgres

# Listar bases de datos disponibles

docker exec -it odoo_registro_ventas-db-1 psql -U odoo -d postgres -c "\l"

# Forzar reinstalación del módulo

docker exec -it odoo_registro_ventas-web-1 odoo -i sales_register -d postgres --stop-after-init

# Verificar logs para errores

docker logs odoo_registro_ventas-web-1 --tail 50

# Reiniciar todos los servicios

docker-compose restart

# O reinicio completo

docker-compose down && docker-compose up -d
