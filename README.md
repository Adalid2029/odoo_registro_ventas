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
odoo shell -d odoo
# o si tu base de datos tiene otro nombre:
# odoo shell -d odoo
```

# Actualizar el módulo sales_register (con base de datos postgres)

docker exec -it odoo_registro_ventas-web-1 odoo -u sales_register -d odoo

# Actualizar el módulo sales_register (con base de datos odoo)

docker exec -it odoo_registro_ventas-web-1 odoo -u sales_register -d odoo

# Actualizar con parada automática después de la inicialización

docker exec -it odoo_registro_ventas-web-1 odoo -u sales_register -d odoo --stop-after-init

# Detener todos los servicios

docker compose down

# Iniciar solo la base de datos

docker compose up -d db

# Esperar que la base de datos esté lista

sleep 10

# Ejecutar actualización del módulo con docker compose

docker compose run --rm web odoo -u sales_register -d odoo --stop-after-init

# Iniciar todos los servicios

docker compose up -d

# Reiniciar solo el contenedor web

docker restart odoo_registro_ventas-web-1

# Luego actualizar el módulo

docker exec -it odoo_registro_ventas-web-1 odoo -u sales_register -d odoo --stop-after-init

# Ver todos los contenedores

docker ps

# Ver solo los contenedores de tu proyecto

docker compose ps

# Ver logs del contenedor web

docker logs odoo_registro_ventas-web-1

# Ver logs de la base de datos

docker logs odoo_registro_ventas-db-1

# Conectar a PostgreSQL

docker exec -it odoo_registro_ventas-db-1 psql -U odoo -d odoo

# Listar bases de datos disponibles

docker exec -it odoo_registro_ventas-db-1 psql -U odoo -d odoo -c "\l"

# Forzar reinstalación del módulo

docker exec -it odoo_registro_ventas-web-1 odoo -i sales_register -d odoo --stop-after-init

# Verificar logs para errores

docker logs odoo_registro_ventas-web-1 --tail 50

# Reiniciar todos los servicios

docker compose restart

# O reinicio completo

docker compose down && docker compose up -d

docker logs odoo_registro_ventas-web-1 --tail 0 &> /dev/null
docker exec -it odoo_registro_ventas-web-1 sh -c "truncate -s 0 /var/log/odoo/odoo.log" 2>/dev/null || true
docker exec -it odoo_registro_ventas-web-1 odoo -d odoo --uninstall-module sales_register --stop-after-init --log-level=warn
docker exec -it odoo_registro_ventas-web-1 odoo -i sales_register -d odoo --stop-after-init --log-level=warn

docker exec -it odoo_registro_ventas-web-1 odoo -u sales_register -d odoo --stop-after-init
docker exec -it odoo_registro_ventas-web-1 odoo shell -d odoo
select id, currency_id, user_id, cliente_id, categoria_id, producto_id, metodo_pago_id, create_uid, write_uid, factura, op, unidad, tipo, observacion, estado_pago, fecha_entrega, fecha_pago, cantidad_kg, precio_unitario, total, monto_pagado, saldo_operacion, saldo_acumulado from sales_operacion order by id;

docker exec -t odoo_registro_ventas-db-1 pg_dump -U odoo -d odoo -F c -f /tmp/odoo.backup
docker exec -it odoo_registro_ventas-db-1 ls -lh /tmp
docker cp odoo_registro_ventas-db-1:/tmp/odoo.backup ./odoo.backup
