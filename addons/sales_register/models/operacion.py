from odoo import models, fields, api
from odoo.exceptions import UserError


class Operacion(models.Model):
    _name = "sales.operacion"
    _description = "Operaciones de venta"
    _order = "create_date desc"
    _rec_name = "display_name"

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
    producto_id = fields.Many2one("product.product", string="Producto")

    # CAMPOS DE TU BASE DE DATOS
    # --------------------------
    fecha_entrega = fields.Date(string="Fecha de Entrega")
    factura = fields.Char(string="Factura", size=50)
    nota_remision = fields.Char(string="Nota de Remisión", size=50)
    recibo_pago = fields.Char(string="Recibo de Pago", size=50)
    op = fields.Integer(string="OP", size=50)

    categoria_id = fields.Many2one("sales.categoria", string="Categoría")
    cantidad_kg = fields.Float(string="Cantidad (Kg)", digits=(10, 2))
    precio_unitario = fields.Float(string="Precio Unitario", digits=(10, 2))
    total = fields.Float(
        string="Total", digits=(10, 2), compute="_compute_total", store=True
    )

    monto_adelanto = fields.Float(
        string="Monto Adelanto", digits=(10, 2), required=True
    )
    fecha_pago = fields.Date(string="Fecha de Pago")
    nro_nota = fields.Char(string="Número de Nota", size=50)
    metodo_pago_id = fields.Many2one("sales.metodo_pago", string="Método de Pago")
    observacion = fields.Text(string="Observación")

    # SALDOS MEJORADOS CON ACUMULACIÓN
    saldo_operacion = fields.Float(
        string="Saldo Operación",
        digits=(10, 2),
        compute="_compute_saldo_operacion",
        store=True,
    )
    saldo_acumulado = fields.Float(
        string="Saldo Acumulado",
        digits=(10, 2),
        compute="_compute_saldo_acumulado",
        store=True,
    )

    # CAMPOS CALCULADOS ADICIONALES
    display_name = fields.Char(string="Nombre", compute="_compute_display_name")

    # CAMPO ESTADO DE PAGO - AHORA ALMACENADO
    estado_pago = fields.Selection(
        [
            ("adelanto", "Adelanto"),
            ("pendiente", "Pendiente"),
            ("parcial", "Pago Parcial"),
            ("pagado", "Pagado"),  # Agregado estado pagado
        ],
        string="Estado de Pago",
        compute="_compute_estado_pago",
        store=True,
    )

    @api.depends("cantidad_kg", "precio_unitario")
    def _compute_total(self):
        """Calcula el total de la operación"""
        for record in self:
            record.total = (record.cantidad_kg or 0) * (record.precio_unitario or 0)

    @api.depends("total", "monto_adelanto")
    def _compute_saldo_operacion(self):
        """Calcula el saldo pendiente de esta operación"""
        for record in self:
            record.saldo_operacion = (record.total or 0) - (record.monto_adelanto or 0)

    @api.depends("cliente_id", "saldo_operacion", "create_date")
    def _compute_saldo_acumulado(self):
        """NUEVA FUNCIONALIDAD: Calcula el saldo acumulado del cliente hasta esta operación"""
        for record in self:
            if not record.cliente_id:
                record.saldo_acumulado = 0
                continue

            # Buscar todas las operaciones del cliente hasta esta fecha/ID
            # Ordenar por fecha de creación y luego por ID para mantener consistencia
            operaciones_anteriores = self.search(
                [
                    ("cliente_id", "=", record.cliente_id.id),
                    "|",
                    ("create_date", "<", record.create_date or fields.Datetime.now()),
                    "&",
                    ("create_date", "=", record.create_date or fields.Datetime.now()),
                    ("id", "<=", record.id),
                ],
                order="create_date asc, id asc",
            )

            # Sumar todos los saldos de operaciones anteriores (incluyendo esta)
            saldo_total = sum(op.saldo_operacion for op in operaciones_anteriores)
            record.saldo_acumulado = saldo_total

    @api.depends("total", "monto_adelanto")
    def _compute_estado_pago(self):
        """Determina el estado del pago - MEJORADO"""
        for record in self:
            if record.saldo_operacion == 0:
                record.estado_pago = "pagado"
            elif record.monto_adelanto == 0:
                record.estado_pago = "pendiente"
            elif record.monto_adelanto >= record.total:
                record.estado_pago = "adelanto"
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

        # MEJORADO: Recalcular saldos acumulados de operaciones posteriores
        for operacion in operaciones:
            operacion._actualizar_saldo_cliente()
            operacion._recalcular_saldos_posteriores()

        return operaciones

    def write(self, vals):
        """Al modificar una operación, actualiza los saldos del cliente"""
        result = super(Operacion, self).write(vals)
        if any(field in vals for field in ["total", "monto_adelanto", "cliente_id"]):
            for record in self:
                record._actualizar_saldo_cliente()
                record._recalcular_saldos_posteriores()
        return result

    def _recalcular_saldos_posteriores(self):
        """NUEVA FUNCIONALIDAD: Recalcula saldos acumulados de operaciones posteriores del mismo cliente"""
        if not self.cliente_id:
            return

        # Buscar operaciones posteriores del mismo cliente
        operaciones_posteriores = self.search(
            [
                ("cliente_id", "=", self.cliente_id.id),
                "|",
                ("create_date", ">", self.create_date),
                "&",
                ("create_date", "=", self.create_date),
                ("id", ">", self.id),
            ],
            order="create_date asc, id asc",
        )

        # Forzar recálculo de saldos acumulados
        if operaciones_posteriores:
            operaciones_posteriores._compute_saldo_acumulado()

    def _actualizar_saldo_cliente(self):
        """Actualiza el saldo total del cliente en la tabla sales.saldo_cliente"""
        if not self.cliente_id:
            return

        SaldoCliente = self.env["sales.saldo_cliente"]
        saldo_cliente = SaldoCliente.search(
            [("cliente_id", "=", self.cliente_id.id)], limit=1
        )

        # MEJORADO: Usar el saldo acumulado de la última operación
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

    def action_ver_historial_cliente(self):
        """NUEVA ACCIÓN: Ver todas las operaciones del cliente ordenadas cronológicamente"""
        if not self.cliente_id:
            raise UserError("No hay cliente seleccionado")

        return {
            "type": "ir.actions.act_window",
            "name": f"Historial de {self.cliente_id.name}",
            "res_model": "sales.operacion",
            "view_mode": "list,form",
            "domain": [("cliente_id", "=", self.cliente_id.id)],
            "context": {
                "default_cliente_id": self.cliente_id.id,
                "search_default_cliente_id": self.cliente_id.id,
            },
            "target": "current",
        }
