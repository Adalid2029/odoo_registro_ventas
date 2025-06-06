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
    op = fields.Char(string="OP", size=50)

    categoria_id = fields.Many2one("sales.categoria", string="Categoría")
    cantidad_kg = fields.Float(string="Cantidad (Kg)", digits=(10, 2))
    precio_unitario = fields.Float(string="Precio Unitario", digits=(10, 2))
    total = fields.Float(
        string="Total", digits=(10, 2), compute="_compute_total", store=True
    )

    monto_pagado = fields.Float(string="Monto Pagado", digits=(10, 2), required=True)
    fecha_pago = fields.Date(string="Fecha de Pago")
    nro_nota = fields.Integer(string="Número de Nota")
    metodo_pago_id = fields.Many2one("sales.metodo_pago", string="Método de Pago")
    observacion = fields.Text(string="Observación")

    # SALDOS
    saldo_operacion = fields.Float(
        string="Saldo Operación",
        digits=(10, 2),
        compute="_compute_saldo_operacion",
        store=True,
    )
    saldo_acumulado = fields.Float(string="Saldo Acumulado", digits=(10, 2), default=0)

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
            operacion._actualizar_saldo_cliente()
        return operaciones

    def write(self, vals):
        """Al modificar una operación, actualiza los saldos del cliente"""
        result = super(Operacion, self).write(vals)
        if any(field in vals for field in ["total", "monto_pagado", "cliente_id"]):
            for record in self:
                record._actualizar_saldo_cliente()
        return result

    def _actualizar_saldo_cliente(self):
        """Actualiza el saldo total del cliente en la tabla sales.saldo_cliente"""
        if not self.cliente_id:
            return

        SaldoCliente = self.env["sales.saldo_cliente"]
        saldo_cliente = SaldoCliente.search(
            [("cliente_id", "=", self.cliente_id.id)], limit=1
        )

        # Calcula el saldo total del cliente sumando todas sus operaciones
        operaciones = self.search([("cliente_id", "=", self.cliente_id.id)])
        saldo_total = sum(op.saldo_operacion for op in operaciones)

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
