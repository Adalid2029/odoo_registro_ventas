from odoo import models, fields, api  # Importa las clases base de Odoo
from odoo.exceptions import UserError  # Para mostrar errores al usuario


class Operacion(models.Model):  # Define un modelo/tabla en la base de datos
    _name = "sales.operacion"  # Nombre interno del modelo (nombre de la tabla)
    _description = "Operaciones de venta"  # Descripción del modelo
    _order = "id asc"  # Orden por defecto: más recientes primero
    _rec_name = "display_name"  # Campo que se mostrará como nombre del registro

    # CAMPO MONEDA (relación con tabla de monedas)
    currency_id = fields.Many2one(  # Many2one = relación con otra tabla (foreign key)
        "res.currency",  # Tabla relacionada: res_currency
        string="Moneda",  # Etiqueta que se muestra en la interfaz
        default=lambda self: self.env.company.currency_id,  # Valor por defecto: moneda de la empresa
    )

    # CAMPOS RELACIONALES (foreign keys)
    user_id = fields.Many2one(  # Relación con tabla de usuarios
        "res.users",  # Tabla de usuarios
        string="Usuario",  # Etiqueta
        required=True,  # Campo obligatorio
        default=lambda self: self.env.user,  # Valor por defecto: usuario actual
    )

    cliente_id = fields.Many2one(  # Relación con tabla de contactos/clientes
        "res.partner",  # Tabla de contactos
        string="Cliente",  # Etiqueta
        required=True,  # Campo obligatorio
        domain=[("is_company", "=", True)],  # Filtro: solo empresas, no personas
    )

    categoria_id = fields.Many2one(  # Relación con tabla de categorías
        "sales.categoria",  # Tu tabla personalizada de categorías
        string="Categoría",  # Etiqueta
        required=True,  # Campo obligatorio
    )

    # CAMPOS BÁSICOS DE DATOS
    fecha_entrega = fields.Date(string="Fecha de Entrega")  # Campo tipo fecha
    nota_remision = fields.Char(
        string="Nota de Remisión", size=50
    )  # Campo texto limitado a 50 caracteres
    factura = fields.Char(string="Factura", size=50)  # Campo texto limitado
    # op = fields.Char(string="OP", size=50)  # Campo texto limitado
    op = fields.Many2one('sales.op', string="OP")


    producto_id = fields.Many2one(  # Relación con tabla de productos
        "product.product",  # Tabla de productos de Odoo
        string="Descripcion",  # Etiqueta
    )

    # unidad = fields.Char(string="Unidad", size=250)  # Campo texto
    unidad = fields.Many2one('sales.unidad_medida', string="Unidad")

    # tipo = fields.Char(string="Tipo", size=250)  # Campo texto
    tipo = fields.Many2one('sales.tipo', string="Tipo")  # Relación con tipo de producto
    cantidad_kg = fields.Float(
        string="Cantidad (Kg)", digits=(10, 2)
    )  # Campo decimal: 10 dígitos totales, 2 decimales
    precio_unitario = fields.Float(
        string="Precio Unitario", digits=(10, 2)
    )  # Campo decimal

    # CAMPO CALCULADO AUTOMÁTICAMENTE
    total = fields.Float(
        string="Total",  # Etiqueta
        digits=(10, 2),  # Precisión decimal
        compute="_compute_total",  # Función que calcula este campo automáticamente
        store=True,  # Guardar el resultado en la base de datos (no calcular cada vez)
    )

    # CAMPOS DE PAGO
    fecha_pago = fields.Date(string="Fecha de Pago")  # Campo fecha
    nro_nota = fields.Integer(string="Número de Nota")  # Campo número entero
    
    metodo_pago_id = fields.Many2one(
        "sales.metodo_pago", string="Tipo de Pago"
    )  # Relación con métodos de pago
    observacion = fields.Char(string="Observación", size=250)  # Campo texto
    monto_pagado = fields.Float(
        string="Pagos a cuenta", digits=(10, 2), required=True
    )  # Campo decimal obligatorio

    # CAMPOS CALCULADOS AUTOMÁTICAMENTE
    saldo_operacion = fields.Float(
        string="Saldo",  # Etiqueta
        digits=(10, 2),  # Precisión decimal
        compute="_compute_saldo_operacion",  # Función que calcula automáticamente
        store=True,  # Guardar resultado en base de datos
    )

    saldo_acumulado = fields.Float(
        string="Cuenta Acumulada",  # Etiqueta
        digits=(10, 2),  # Precisión decimal
        compute="_compute_saldo_acumulado",  # Función que calcula automáticamente
        store=True,  # Guardar resultado en base de datos
    )

    # CAMPO CALCULADO PARA NOMBRE DESCRIPTIVO
    display_name = fields.Char(
        string="Nombre",  # Etiqueta
        compute="_compute_display_name",  # Función que calcula automáticamente
        # Sin store=True = se calcula cada vez que se necesita (no se guarda)
    )

    # CAMPO DE SELECCIÓN (dropdown/lista desplegable)
    estado_pago = fields.Selection(
        [  # Lista de opciones: (valor_interno, etiqueta_mostrada)
            ("pagado", "Pagado"),  # Opción 1
            ("pendiente", "Pendiente"),  # Opción 2
            ("parcial", "Pago Parcial"),  # Opción 3
            ("anticipo", "Anticipo"),  # Opción 4
        ],
        string="Estado de Pago",  # Etiqueta del campo
        compute="_compute_estado_pago",  # Función que calcula automáticamente
        store=True,  # Guardar resultado en base de datos
    )

    # FUNCIÓN QUE CALCULA EL TOTAL
    @api.depends(
        "cantidad_kg", "precio_unitario"
    )  # Se ejecuta cuando cambian estos campos
    def _compute_total(self):
        """Calcula el total de la operación"""
        for record in self:  # Para cada registro (si se procesan varios a la vez)
            # Multiplica cantidad por precio (or 0 = si es None/vacío, usar 0)
            record.total = (record.cantidad_kg or 0) * (record.precio_unitario or 0)

    # FUNCIÓN QUE CALCULA EL SALDO
    @api.depends(
        "cliente_id", "total", "monto_pagado"
    )  # Se ejecuta cuando cambian estos campos
    def _compute_saldo_operacion(self):
        """Saldo = balance acumulado real del cliente (mínimo 0)"""
        for record in self:  # Para cada registro
            if not record.cliente_id:  # Si no tiene cliente asignado
                record.saldo_operacion = 0  # Saldo = 0
                continue  # Pasar al siguiente registro

            # CASO 1: REGISTROS NUEVOS (que aún no están guardados)
            if not record.id or str(record.id).startswith("NewId"):
                # Buscar todas las operaciones existentes del mismo cliente
                operaciones_existentes = self.search(
                    [
                        ("cliente_id", "=", record.cliente_id.id)
                    ],  # Filtro: mismo cliente
                    order="create_date asc, id asc",  # Ordenar por fecha ascendente
                )

                # Calcular balance total de operaciones existentes
                balance_total = sum(
                    (op.total or 0)
                    - (op.monto_pagado or 0)  # total - pago para cada operación
                    for op in operaciones_existentes  # Para todas las operaciones
                )

                # Agregar el balance de esta operación nueva
                balance_operacion = (record.total or 0) - (record.monto_pagado or 0)
                balance_final = balance_total + balance_operacion

                # SALDO = máximo 0 (si balance es negativo, saldo = 0)
                record.saldo_operacion = max(0, balance_final)
                continue  # Pasar al siguiente registro

            # CASO 2: REGISTROS EXISTENTES (ya guardados en base de datos)
            # Buscar operaciones anteriores del mismo cliente (incluyendo esta)
            operaciones_anteriores = self.search(
                [
                    ("cliente_id", "=", record.cliente_id.id),  # Mismo cliente
                    (
                        "create_date",
                        "<=",
                        record.create_date or fields.Datetime.now(),
                    ),  # Fecha menor o igual
                    ("id", "<=", record.id),  # ID menor o igual (para mantener orden)
                ],
                order="create_date asc, id asc",  # Ordenar por fecha
            )

            # Calcular balance acumulado hasta esta operación
            balance_total = sum(
                (op.total or 0) - (op.monto_pagado or 0)  # total - pago
                for op in operaciones_anteriores  # Para todas las operaciones anteriores
            )

            # SALDO = balance acumulado (mínimo 0)
            record.saldo_operacion = max(0, balance_total)

    # FUNCIÓN QUE CALCULA LA CUENTA ACUMULADA
    @api.depends("total", "monto_pagado")  # Se ejecuta cuando cambian estos campos
    def _compute_saldo_acumulado(self):
        """Cuenta acumulada = EXCESO de pago en esta operación específica"""
        for record in self:  # Para cada registro
            # Obtener valores (or 0 = si es None/vacío, usar 0)
            total = record.total or 0
            pago = record.monto_pagado or 0

            # CUENTA ACUMULADA = máximo 0 del exceso en ESTA operación
            # Si pago > total, cuenta = pago - total
            # Si pago <= total, cuenta = 0
            record.saldo_acumulado = max(0, pago - total)

    @api.depends("cliente_id", "total", "monto_pagado", "create_date")
    def _compute_estado_pago(self):
        """Estado considerando operaciones anteriores - SIN ERROR"""
        for record in self:
            total = record.total or 0
            pago = record.monto_pagado or 0

            # ✅ CALCULAR SALDO ANTERIOR PARA TODOS LOS CASOS
            if record.cliente_id:
                if not record.id or str(record.id).startswith("NewId"):
                    # Para registros nuevos: buscar todas las operaciones existentes
                    operaciones_anteriores = self.search(
                        [("cliente_id", "=", record.cliente_id.id)],
                        order="create_date asc, id asc",
                    )
                else:
                    # Para registros existentes: buscar operaciones anteriores
                    operaciones_anteriores = self.search(
                        [
                            ("cliente_id", "=", record.cliente_id.id),
                            (
                                "create_date",
                                "<",
                                record.create_date or fields.Datetime.now(),
                            ),
                            ("id", "<", record.id),
                        ],
                        order="create_date asc, id asc",
                    )

                # Calcular saldo pendiente anterior
                saldo_pendiente_anterior = sum(
                    (op.total or 0) - (op.monto_pagado or 0)
                    for op in operaciones_anteriores
                )
            else:
                saldo_pendiente_anterior = 0

            # Calcular balance total = deuda anterior + deuda actual - pago actual
            saldo_actual = max(0, (total + saldo_pendiente_anterior) - pago)

            # 🎯 LÓGICA CORREGIDA PARA EL ESTADO - ORDEN CORRECTO:
            if total == 0 and pago > 0 and saldo_pendiente_anterior == 0:
                record.estado_pago = "anticipo"  # PRIMERO: anticipo sin deuda anterior
            elif saldo_actual == 0:
                record.estado_pago = "pagado"  # SEGUNDO: todo saldado
            elif pago == 0:
                record.estado_pago = "pendiente"  # TERCERO: no pagó nada
            else:
                record.estado_pago = "parcial"  # CUARTO: pago parcial

    # FUNCIÓN QUE CALCULA EL NOMBRE DESCRIPTIVO
    @api.depends(
        "cliente_id", "factura", "create_date"
    )  # Se ejecuta cuando cambian estos campos
    def _compute_display_name(self):
        """Genera un nombre descriptivo para la operación"""
        for record in self:  # Para cada registro
            if record.cliente_id and record.factura:  # Si tiene cliente y factura
                # Formato: "Nombre Cliente - Número Factura"
                record.display_name = f"{record.cliente_id.name} - {record.factura}"
            elif record.cliente_id:  # Si solo tiene cliente (sin factura)
                # Formato: "Nombre Cliente - Fecha"
                fecha_str = (
                    record.create_date.strftime("%d/%m/%Y")
                    if record.create_date
                    else "Nueva"
                )
                record.display_name = f"{record.cliente_id.name} - {fecha_str}"
            else:  # Si no tiene cliente
                # Formato: "Operación #ID"
                record.display_name = f"Operación #{record.id or 'Nueva'}"

    # FUNCIÓN QUE SE EJECUTA AL CREAR NUEVOS REGISTROS
    def create(self, vals_list):
        """Al crear una operación, actualiza los saldos del cliente"""
        if not isinstance(vals_list, list):  # Si vals_list no es una lista
            vals_list = [vals_list]  # Convertirla en lista

        # Llamar al método create original de Odoo para crear los registros
        operaciones = super(Operacion, self).create(vals_list)

        for operacion in operaciones:  # Para cada operación creada
            operacion._recalcular_saldos_posteriores()  # Recalcular saldos
            operacion._actualizar_saldo_cliente()  # Actualizar tabla de saldos
        return operaciones  # Devolver las operaciones creadas

    # FUNCIÓN QUE SE EJECUTA AL MODIFICAR REGISTROS EXISTENTES
    def write(self, vals):
        """Al modificar una operación, actualiza los saldos del cliente"""
        # Llamar al método write original de Odoo para guardar cambios
        result = super(Operacion, self).write(vals)

        # Si se modificaron campos que afectan los saldos
        if any(field in vals for field in ["total", "monto_pagado", "cliente_id"]):
            for record in self:  # Para cada registro modificado
                record._recalcular_saldos_posteriores()  # Recalcular saldos
                record._actualizar_saldo_cliente()  # Actualizar tabla de saldos
        return result  # Devolver el resultado

    # FUNCIÓN AUXILIAR PARA RECALCULAR SALDOS
    def _recalcular_saldos_posteriores(self):
        """Recalcula saldos acumulados de operaciones posteriores del mismo cliente"""
        # Si no tiene cliente, ID, o es un registro nuevo, no hacer nada
        if not self.cliente_id or not self.id or str(self.id).startswith("NewId"):
            return

        # Buscar TODAS las operaciones del mismo cliente
        operaciones_cliente = self.search(
            [("cliente_id", "=", self.cliente_id.id)],  # Filtro: mismo cliente
            order="create_date asc, id asc",  # Ordenar por fecha
        )

        # Recalcular campos computados para todas las operaciones
        for operacion in operaciones_cliente:
            if operacion.id and not str(operacion.id).startswith(
                "NewId"
            ):  # Solo registros existentes
                operacion._compute_saldo_acumulado()  # Recalcular cuenta acumulada
                operacion._compute_saldo_operacion()  # Recalcular saldo

    # FUNCIÓN AUXILIAR PARA ACTUALIZAR TABLA DE SALDOS POR CLIENTE
    def _actualizar_saldo_cliente(self):
        """Actualiza el saldo total del cliente en la tabla sales.saldo_cliente"""
        if not self.cliente_id:  # Si no tiene cliente, no hacer nada
            return

        # Obtener modelo de saldos por cliente
        SaldoCliente = self.env["sales.saldo_cliente"]

        # Buscar si ya existe un registro de saldo para este cliente
        saldo_cliente = SaldoCliente.search(
            [("cliente_id", "=", self.cliente_id.id)],  # Filtro: mismo cliente
            limit=1,  # Solo el primer resultado
        )

        # Buscar la última operación del cliente para obtener su saldo final
        ultima_operacion = self.search(
            [("cliente_id", "=", self.cliente_id.id)],  # Filtro: mismo cliente
            order="create_date desc, id desc",  # Ordenar por fecha descendente (más reciente primero)
            limit=1,  # Solo la primera (más reciente)
        )

        # Obtener el saldo total del cliente (saldo acumulado de la última operación)
        saldo_total = ultima_operacion.saldo_acumulado if ultima_operacion else 0

        if saldo_cliente:  # Si ya existe un registro de saldo para este cliente
            # Actualizar el registro existente
            saldo_cliente.write(
                {
                    "saldo_total": saldo_total,  # Nuevo saldo total
                    "fecha_actualizacion": fields.Datetime.now(),  # Fecha actual
                }
            )
        else:  # Si no existe un registro de saldo para este cliente
            # Crear un nuevo registro
            SaldoCliente.create(
                {
                    "cliente_id": self.cliente_id.id,  # ID del cliente
                    "saldo_total": saldo_total,  # Saldo total
                    "fecha_actualizacion": fields.Datetime.now(),  # Fecha actual
                }
            )

    # FUNCIÓN ACCESIBLE DESDE LA INTERFAZ (botón)
    def recalcular_saldos(self):
        """Recalcula los saldos manualmente"""
        for record in self:  # Para cada registro seleccionado
            record._recalcular_saldos_posteriores()  # Recalcular saldos
            record._actualizar_saldo_cliente()  # Actualizar tabla de saldos

        # Devolver acción para recargar la página
        return {
            "type": "ir.actions.client",  # Tipo de acción: cliente
            "tag": "reload",  # Etiqueta: recargar página
        }

    # FUNCIÓN ACCESIBLE DESDE LA INTERFAZ (botón)
    def ver_historial(self):
        """Ver historial de operaciones del cliente"""
        self.ensure_one()  # Asegurarse de que solo hay un registro seleccionado

        if not self.cliente_id:  # Si no tiene cliente
            # Mostrar error al usuario
            raise UserError("No se puede mostrar el historial sin un cliente asociado.")

        # Devolver acción para abrir nueva ventana con historial del cliente
        return {
            "type": "ir.actions.act_window",  # Tipo: ventana
            "name": f"Historial del Cliente: {self.cliente_id.name}",  # Título de la ventana
            "res_model": "sales.operacion",  # Modelo a mostrar
            "view_mode": "tree,form",  # Vistas: lista y formulario
            "domain": [
                ("cliente_id", "=", self.cliente_id.id)
            ],  # Filtro: mismo cliente
            "context": {  # Contexto (variables adicionales)
                "default_cliente_id": self.cliente_id.id,  # Cliente por defecto al crear nuevos
                "search_default_group_cliente": 1,  # Agrupar por cliente por defecto
            },
            "target": "current",  # Abrir en la ventana actual
        }
