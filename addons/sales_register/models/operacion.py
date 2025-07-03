from odoo import models, fields, api
from odoo.exceptions import UserError


class Operacion(models.Model):
    _name = "sales.operacion"
    _description = "Operaciones de venta"
    _order = "create_date desc"
    _rec_name = "display_name"
    currency_id = fields.Many2one(
        "res.currency",
        string="Moneda",
        default=lambda self: self.env.company.currency_id,
    )
    # RELACIONES CON OTROS MÓDULOS DE ODOO
    # ------------------------------------
    user_id = fields.Many2one(
        "res.users", string="Usuario", required=True, default=lambda self: self.env.user
    )
    cliente_id = fields.Many2one(
        "res.partner",
        string="Cliente",
        required=True,
        domain=[("is_company", "=", True)],
    )
    categoria_id = fields.Many2one("sales.categoria", string="Categoría")

    # CAMPOS DE TU BASE DE DATOS - EXACTOS
    # ------------------------------------
    fecha_entrega = fields.Date(string="Fecha de Entrega")
    nota_remision = fields.Char(string="Nota de Remisión", size=50)
    factura = fields.Char(string="Factura", size=50)
    op = fields.Char(string="OP", size=50)  # CHAR como en tu modelo
    producto_id = fields.Many2one("product.product", string="Descripcion")
    unidad = fields.Char(string="Unidad", size=250)
    tipo = fields.Char(string="Tipo", size=250)
    cantidad_kg = fields.Float(string="Cantidad (Kg)", digits=(10, 2))
    precio_unitario = fields.Float(string="Precio Unitario", digits=(10, 2))
    total = fields.Float(
        string="Total", digits=(10, 2), compute="_compute_total", store=True
    )

    fecha_pago = fields.Date(string="Fecha de Pago")
    nro_nota = fields.Integer(string="Número de Nota")  # INTEGER como en tu modelo
    metodo_pago_id = fields.Many2one("sales.metodo_pago", string="Tipo de Pago")
    observacion = fields.Char(string="Observación", size=250)

    # recibo_pago = fields.Char(string="Recibo de Pago", size=50)

    monto_pagado = fields.Float(
        string="Pagos a cuenta", digits=(10, 2), required=True
    )  # COMO EN TU MODELO

    # SALDOS - AGREGANDO FUNCIONALIDAD DE SALDO ACUMULADO
    saldo_operacion = fields.Float(
        string="Saldo",
        digits=(10, 2),
        compute="_compute_saldo_operacion",
        store=True,
    )
    saldo_acumulado = fields.Float(
        string="Cuenta Acumulada",
        digits=(10, 2),
        compute="_compute_saldo_acumulado",
        store=True,
    )

    # CAMPOS CALCULADOS ADICIONALES
    display_name = fields.Char(string="Nombre", compute="_compute_display_name")

    # CAMPO ESTADO DE PAGO - AHORA ALMACENADO
    estado_pago = fields.Selection(
        [("pagado", "Pagado"), ("pendiente", "Pendiente"), ("parcial", "Pago Parcial")],
        string="Estado de Pago",
        compute="_compute_estado_pago",
        store=True,
    )

    @api.depends("cantidad_kg", "precio_unitario")
    def _compute_total(self):
        """Calcula el total de la operación"""
        for record in self:
            record.total = (record.cantidad_kg or 0) * (record.precio_unitario or 0)

    @api.depends("total", "monto_pagado")
    def _compute_saldo_operacion(self):
        """Calcula el saldo pendiente de esta operación"""
        for record in self:
            record.saldo_operacion = (record.total or 0) - (record.monto_pagado or 0)

    @api.depends("cliente_id", "saldo_operacion")
    def _compute_saldo_acumulado(self):
        """Calcula el saldo acumulado del cliente hasta esta operación - CORREGIDO"""
        for record in self:
            if not record.cliente_id:
                record.saldo_acumulado = 0
                continue

            # EVITAR CÁLCULO EN REGISTROS NUEVOS (NewId)
            if not record.id or str(record.id).startswith("NewId"):
                # Para registros nuevos, calcular basándose en operaciones existentes
                operaciones_existentes = self.search(
                    [("cliente_id", "=", record.cliente_id.id)],
                    order="create_date asc, id asc",
                )

                saldo_total = sum(op.saldo_operacion for op in operaciones_existentes)
                # Agregar el saldo de esta operación nueva
                record.saldo_acumulado = saldo_total + record.saldo_operacion
                continue

            # Para registros existentes, calcular normalmente
            operaciones_anteriores = self.search(
                [
                    ("cliente_id", "=", record.cliente_id.id),
                    ("create_date", "<=", record.create_date or fields.Datetime.now()),
                    ("id", "<=", record.id),
                ],
                order="create_date asc, id asc",
            )

            # Sumar todos los saldos de operaciones
            saldo_total = sum(op.saldo_operacion for op in operaciones_anteriores)
            record.saldo_acumulado = saldo_total

    @api.depends("total", "monto_pagado")
    def _compute_estado_pago(self):
        """Determina el estado del pago - AHORA ALMACENADO"""
        for record in self:
            if record.monto_pagado == 0:
                record.estado_pago = "pendiente"
            elif record.monto_pagado >= record.total:
                record.estado_pago = "pagado"
            else:
                record.estado_pago = "parcial"

    @api.depends("cliente_id", "factura", "create_date")
    def _compute_display_name(self):
        """Genera un nombre descriptivo para la operación"""
        for record in self:
            if record.cliente_id and record.factura:
                record.display_name = f"{record.cliente_id.name} - {record.factura}"
            elif record.cliente_id:
                record.display_name = f"{record.cliente_id.name} - {record.create_date.strftime('%d/%m/%Y') if record.create_date else 'Nueva'}"
            else:
                record.display_name = f"Operación #{record.id or 'Nueva'}"

    def create(self, vals_list):
        """Al crear una operación, actualiza los saldos del cliente"""
        # Convertir vals_list a lista si es un diccionario
        if not isinstance(vals_list, list):
            vals_list = [vals_list]

        operaciones = super(Operacion, self).create(vals_list)
        for operacion in operaciones:
            # Primero recalcular saldos acumulados de operaciones posteriores
            operacion._recalcular_saldos_posteriores()
            # Luego actualizar tabla de saldos por cliente
            operacion._actualizar_saldo_cliente()
        return operaciones

    def write(self, vals):
        """Al modificar una operación, actualiza los saldos del cliente"""
        result = super(Operacion, self).write(vals)
        if any(field in vals for field in ["total", "monto_pagado", "cliente_id"]):
            for record in self:
                # Recalcular saldos acumulados de todas las operaciones del cliente
                record._recalcular_saldos_posteriores()
                # Actualizar tabla de saldos por cliente
                record._actualizar_saldo_cliente()
        return result

    def _recalcular_saldos_posteriores(self):
        """Recalcula saldos acumulados de operaciones posteriores del mismo cliente"""
        if not self.cliente_id or not self.id or str(self.id).startswith("NewId"):
            return

        # Buscar TODAS las operaciones del cliente para recalcular
        operaciones_cliente = self.search(
            [("cliente_id", "=", self.cliente_id.id)], order="create_date asc, id asc"
        )

        # Forzar recálculo de saldos acumulados
        for operacion in operaciones_cliente:
            if operacion.id and not str(operacion.id).startswith("NewId"):
                operacion._compute_saldo_acumulado()

    def _actualizar_saldo_cliente(self):
        """Actualiza el saldo total del cliente en la tabla sales.saldo_cliente"""
        if not self.cliente_id:
            return

        SaldoCliente = self.env["sales.saldo_cliente"]
        saldo_cliente = SaldoCliente.search(
            [("cliente_id", "=", self.cliente_id.id)], limit=1
        )

        # Buscar la última operación del cliente para obtener su saldo acumulado final
        ultima_operacion = self.search(
            [("cliente_id", "=", self.cliente_id.id)],
            order="create_date desc, id desc",
            limit=1,
        )

        saldo_total = ultima_operacion.saldo_acumulado if ultima_operacion else 0

        if saldo_cliente:
            saldo_cliente.write(
                {
                    "saldo_total": saldo_total,
                    "fecha_actualizacion": fields.Datetime.now(),
                }
            )
        else:
            SaldoCliente.create(
                {
                    "cliente_id": self.cliente_id.id,
                    "saldo_total": saldo_total,
                    "fecha_actualizacion": fields.Datetime.now(),
                }
            )

    def recalcular_saldos(self):
        """Recalcula los saldos manualmente"""
        for record in self:
            record._recalcular_saldos_posteriores()
            record._actualizar_saldo_cliente()
        return True

    def ver_historial(self):
        """Ver historial de operaciones del cliente"""
        return {
            "type": "ir.actions.act_window",
            "name": "Historial del Cliente",
            "res_model": "sales.operacion",
            "view_mode": "tree,form",
            "domain": [("cliente_id", "=", self.cliente_id.id)],
            "context": {"default_cliente_id": self.cliente_id.id},
        }
