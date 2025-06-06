from odoo import models, fields, api


class SaldoCliente(models.Model):
    _name = "sales.saldo_cliente"
    _description = "Saldo acumulado por cliente"
    _rec_name = "cliente_id"

    cliente_id = fields.Many2one(
        "res.partner",
        string="Cliente",
        required=True,
        domain=[("is_company", "=", True)],
        ondelete="cascade",
    )
    saldo_total = fields.Float(string="Saldo Total", digits=(10, 2), default=0)
    fecha_actualizacion = fields.Datetime(
        string="Última Actualización", default=fields.Datetime.now
    )

    # Campos relacionados para mostrar información del cliente
    cliente_email = fields.Char(
        related="cliente_id.email", string="Email Cliente", readonly=True
    )
    cliente_telefono = fields.Char(
        related="cliente_id.phone", string="Teléfono Cliente", readonly=True
    )

    # Conteo de operaciones del cliente
    total_operaciones = fields.Integer(
        string="Total Operaciones", compute="_compute_estadisticas_cliente"
    )

    # NUEVOS CAMPOS ESTADÍSTICOS
    total_ventas = fields.Float(
        string="Total Ventas", digits=(10, 2), compute="_compute_estadisticas_cliente"
    )
    total_pagado = fields.Float(
        string="Total Pagado", digits=(10, 2), compute="_compute_estadisticas_cliente"
    )
    ultima_operacion = fields.Date(
        string="Última Operación", compute="_compute_estadisticas_cliente"
    )

    # Estado del cliente basado en saldo
    estado_cliente = fields.Selection(
        [
            ("al_dia", "Al Día"),
            ("pendiente", "Saldo Pendiente"),
            ("adelanto", "Adelanto"),
            ("sin_operaciones", "Sin Operaciones"),
        ],
        string="Estado Cliente",
        compute="_compute_estado_cliente",
        store=True,
    )

    @api.depends("cliente_id")
    def _compute_estadisticas_cliente(self):
        """MEJORADO: Calcula estadísticas completas del cliente"""
        for record in self:
            if not record.cliente_id:
                record.total_operaciones = 0
                record.total_ventas = 0
                record.total_pagado = 0
                record.ultima_operacion = False
                continue

            # Buscar todas las operaciones del cliente
            operaciones = self.env["sales.operacion"].search(
                [("cliente_id", "=", record.cliente_id.id)], order="create_date desc"
            )

            if operaciones:
                record.total_operaciones = len(operaciones)
                record.total_ventas = sum(op.total for op in operaciones)
                record.total_pagado = sum(op.monto_adelanto for op in operaciones)
                record.ultima_operacion = (
                    operaciones[0].create_date.date()
                    if operaciones[0].create_date
                    else False
                )
            else:
                record.total_operaciones = 0
                record.total_ventas = 0
                record.total_pagado = 0
                record.ultima_operacion = False

    @api.depends("saldo_total", "total_operaciones")
    def _compute_estado_cliente(self):
        """NUEVO: Determina el estado general del cliente"""
        for record in self:
            if record.total_operaciones == 0:
                record.estado_cliente = "sin_operaciones"
            elif record.saldo_total == 0:
                record.estado_cliente = "al_dia"
            elif record.saldo_total > 0:
                record.estado_cliente = "pendiente"
            else:
                record.estado_cliente = "adelanto"

    def action_ver_operaciones(self):
        """MEJORADO: Acción para ver todas las operaciones del cliente con saldos acumulados"""
        if not self.cliente_id:
            return {"type": "ir.actions.act_window_close"}

        return {
            "type": "ir.actions.act_window",
            "name": f"Operaciones de {self.cliente_id.name}",
            "res_model": "sales.operacion",
            "view_mode": "list,form",
            "domain": [("cliente_id", "=", self.cliente_id.id)],
            "context": {
                "default_cliente_id": self.cliente_id.id,
                "search_default_cliente_id": self.cliente_id.id,
                "group_by": [],
            },
            "target": "current",
        }

    def action_nueva_operacion(self):
        """NUEVA ACCIÓN: Crear nueva operación para este cliente"""
        if not self.cliente_id:
            return {"type": "ir.actions.act_window_close"}

        return {
            "type": "ir.actions.act_window",
            "name": f"Nueva Operación - {self.cliente_id.name}",
            "res_model": "sales.operacion",
            "view_mode": "form",
            "context": {"default_cliente_id": self.cliente_id.id},
            "target": "new",
        }

    @api.model
    def actualizar_todos_los_saldos(self):
        """MEJORADO: Método para recalcular todos los saldos del sistema"""
        # Obtener todos los clientes que tienen operaciones
        clientes_con_operaciones = self.env["sales.operacion"].read_group(
            domain=[], fields=["cliente_id"], groupby=["cliente_id"]
        )

        for grupo in clientes_con_operaciones:
            cliente_id = grupo["cliente_id"][0]

            # Buscar la última operación del cliente para obtener su saldo acumulado
            ultima_operacion = self.env["sales.operacion"].search(
                [("cliente_id", "=", cliente_id)],
                order="create_date desc, id desc",
                limit=1,
            )

            if ultima_operacion:
                saldo_cliente = self.search([("cliente_id", "=", cliente_id)], limit=1)

                if saldo_cliente:
                    saldo_cliente.write(
                        {
                            "saldo_total": ultima_operacion.saldo_acumulado,
                            "fecha_actualizacion": fields.Datetime.now(),
                        }
                    )
                else:
                    self.create(
                        {
                            "cliente_id": cliente_id,
                            "saldo_total": ultima_operacion.saldo_acumulado,
                            "fecha_actualizacion": fields.Datetime.now(),
                        }
                    )

        return True

    _sql_constraints = [
        (
            "unique_cliente",
            "unique(cliente_id)",
            "Ya existe un registro de saldo para este cliente",
        )
    ]
