from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class Operacion(models.Model):
    _name = "sales.operacion"
    _description = "Operaciones de venta"
    _order = "id asc"
    _rec_name = "display_name"

    # CAMPOS EXISTENTES (mantener todos igual)
    currency_id = fields.Many2one(
        "res.currency",
        string="Moneda",
        default=lambda self: self.env.company.currency_id,
    )

    user_id = fields.Many2one(
        "res.users",
        string="Usuario",
        required=True,
        default=lambda self: self.env.user,
    )

    cliente_id = fields.Many2one(
        "res.partner",
        string="Cliente",
        required=True,
        domain=[("is_company", "=", True)],
    )

    categoria_id = fields.Many2one(
        "sales.categoria",
        string="Categoría",
        required=True,
    )

    fecha_entrega = fields.Date(string="Fecha de Entrega")
    nota_remision = fields.Char(string="Nota de Remisión", size=50)
    factura = fields.Char(string="Factura", size=50)
    op = fields.Many2one("sales.op", string="OP")
    producto_id = fields.Many2one("product.product", string="Descripcion")
    unidad = fields.Many2one("sales.unidad_medida", string="Unidad")
    tipo = fields.Many2one("sales.tipo", string="Tipo")
    cantidad_kg = fields.Float(string="Cantidad (Kg)", digits=(10, 2))
    precio_unitario = fields.Float(string="Precio Unitario", digits=(10, 2))

    # CAMPO CALCULADO AUTOMÁTICAMENTE
    total = fields.Float(
        string="Total",
        digits=(10, 2),
        compute="_compute_total",
        store=True,
    )

    # CAMPOS DE PAGO
    fecha_pago = fields.Date(string="Fecha de Pago")
    nro_nota = fields.Integer(string="Número de Nota")
    metodo_pago_id = fields.Many2one("sales.metodo_pago", string="Tipo de Pago")
    observacion = fields.Char(string="Observación", size=250)
    monto_pagado = fields.Float(string="Pagos a cuenta", digits=(10, 2), required=True)

    # CAMPOS CALCULADOS - MODIFICADOS PARA SER ALMACENADOS
    saldo_operacion = fields.Float(
        string="Saldo",
        digits=(10, 2),
        default=0.0,
        help="Deuda pendiente de esta operación",
    )

    saldo_acumulado = fields.Float(
        string="Cuenta Acumulada",
        digits=(10, 2),
        default=0.0,
        help="Anticipo acumulado del cliente",
    )

    display_name = fields.Char(
        string="Nombre",
        compute="_compute_display_name",
    )

    estado_pago = fields.Selection(
        [
            ("CANCELADO", "Cancelado"),
            ("PENDIENTE", "Pendiente"),
            ("ANTICIPO", "Anticipo"),
        ],
        string="Estado de Pago",
        default="PENDIENTE",
    )

    # ========== FUNCIONES COMPUTE BÁSICAS ==========

    @api.depends("cantidad_kg", "precio_unitario")
    def _compute_total(self):
        """Calcula el total de la operación"""
        for record in self:
            record.total = (record.cantidad_kg or 0) * (record.precio_unitario or 0)

    @api.depends("cliente_id", "factura", "create_date")
    def _compute_display_name(self):
        """Genera un nombre descriptivo para la operación"""
        for record in self:
            if record.cliente_id and record.factura:
                record.display_name = f"{record.cliente_id.name} - {record.factura}"
            elif record.cliente_id:
                fecha_str = (
                    record.create_date.strftime("%d/%m/%Y")
                    if record.create_date
                    else "Nueva"
                )
                record.display_name = f"{record.cliente_id.name} - {fecha_str}"
            else:
                record.display_name = f"Operación #{record.id or 'Nueva'}"

    # ========== LÓGICA PRINCIPAL DE SALDOS ==========

    def _recalcular_saldos_posteriores(self):
        """
        Recalcula correctamente los saldos de operación y acumulados del cliente,
        respetando el flujo de deuda acumulada y anticipos.
        """
        if not self.cliente_id:
            _logger.warning("⛔ No hay cliente asignado, no se recalcula saldo.")
            return

        _logger.info(
            f"🔄 Recalculando saldos para cliente ID={self.cliente_id.id} - {self.cliente_id.name}"
        )

        # Obtener todas las operaciones del cliente ordenadas cronológicamente
        operaciones = self.search(
            [("cliente_id", "=", self.cliente_id.id)],
            order="create_date asc, id asc",
        )

        # Variables acumulativas
        deuda_total_pendiente = 0.0  # Suma de todas las deudas no pagadas
        saldo_anticipo = 0.0  # Dinero a favor del cliente (anticipos)

        for operacion in operaciones:
            total_operacion = operacion.total or 0.0
            pago_operacion = operacion.monto_pagado or 0.0

            # Resetear valores para esta operación
            usado_en_deuda_anterior = 0.0
            saldo_operacion = 0.0
            estado_pago = "PENDIENTE"

            # CASO 1: Operación con venta (total > 0)
            if total_operacion > 0:
                # Primero usar anticipos disponibles
                if saldo_anticipo > 0:
                    aplicado_anticipo = min(saldo_anticipo, total_operacion)
                    saldo_anticipo -= aplicado_anticipo
                    total_operacion -= aplicado_anticipo
                    usado_en_deuda_anterior = aplicado_anticipo

                    _logger.info(
                        f"💰 Usando anticipo: {aplicado_anticipo:.2f} para operación {operacion.id}"
                    )

                # Luego aplicar el pago de esta operación
                if pago_operacion >= total_operacion:
                    # Pago completo o exceso
                    exceso = pago_operacion - total_operacion
                    saldo_anticipo += exceso
                    saldo_operacion = 0.0
                    estado_pago = "CANCELADO"

                    if exceso > 0:
                        _logger.info(
                            f"💵 Exceso de pago: {exceso:.2f} queda como anticipo"
                        )
                else:
                    # Pago parcial - queda deuda
                    saldo_operacion = total_operacion - pago_operacion
                    deuda_total_pendiente += saldo_operacion
                    estado_pago = "PENDIENTE"

            # CASO 2: Operación solo de pago (total = 0, pero pago > 0)
            elif pago_operacion > 0:
                # Usar el pago para cancelar deudas anteriores
                if deuda_total_pendiente > 0:
                    aplicado_deuda = min(pago_operacion, deuda_total_pendiente)
                    deuda_total_pendiente -= aplicado_deuda
                    usado_en_deuda_anterior = aplicado_deuda

                    # Si sobra dinero, queda como anticipo
                    exceso = pago_operacion - aplicado_deuda
                    if exceso > 0:
                        saldo_anticipo += exceso
                        estado_pago = "ANTICIPO"
                    else:
                        estado_pago = "CANCELADO"

                    _logger.info(
                        f"💳 Pago aplicado a deuda anterior: {aplicado_deuda:.2f}"
                    )
                else:
                    # No hay deudas, todo queda como anticipo
                    saldo_anticipo += pago_operacion
                    estado_pago = "ANTICIPO"

                saldo_operacion = 0.0

            # CASO 3: Operación sin venta ni pago (registro informativo)
            else:
                saldo_operacion = 0.0
                estado_pago = "CANCELADO"

            # Log detallado del cálculo
            _logger.info(
                f"🧾 Operación ID={operacion.id} | Total={operacion.total:.2f} | "
                f"Pago={pago_operacion:.2f} | Usado en deuda anterior={usado_en_deuda_anterior:.2f} | "
                f"Saldo Acumulado={saldo_anticipo:.2f} | Nuevo Saldo={saldo_operacion:.2f} | "
                f"Estado={estado_pago}"
            )

            # Actualizar la operación directamente (sin triggers)
            self.env.cr.execute(
                """
                UPDATE sales_operacion 
                SET saldo_operacion = %s, saldo_acumulado = %s, estado_pago = %s 
                WHERE id = %s
            """,
                (saldo_operacion, saldo_anticipo, estado_pago, operacion.id),
            )

        # Actualizar operaciones que cambiaron de PENDIENTE a CANCELADO
        self._recalcular_estados_anteriores(operaciones, deuda_total_pendiente)

    def _recalcular_estados_anteriores(self, operaciones, deuda_restante):
        """
        Recalcula los estados de operaciones anteriores que pudieron cambiar
        de PENDIENTE a CANCELADO debido a pagos posteriores.
        """
        # Recorrer operaciones con deuda de atrás hacia adelante
        for operacion in reversed(operaciones):
            if operacion.saldo_operacion > 0 and deuda_restante == 0:
                # Esta operación tenía deuda pero ya fue pagada posteriormente
                self.env.cr.execute(
                    """
                    UPDATE sales_operacion 
                    SET estado_pago = 'CANCELADO'
                    WHERE id = %s
                """,
                    (operacion.id,),
                )
                _logger.info(
                    f"✅ Operación {operacion.id} cambió a CANCELADO (pagada posteriormente)"
                )

    # ========== MÉTODOS DE ESCRITURA/CREACIÓN ==========

    def create(self, vals_list):
        """Al crear una operación, actualiza los saldos del cliente"""
        if not isinstance(vals_list, list):
            vals_list = [vals_list]

        operaciones = super(Operacion, self).create(vals_list)

        for operacion in operaciones:
            if operacion.cliente_id:
                operacion._recalcular_saldos_posteriores()
                operacion._actualizar_saldo_cliente()
        return operaciones

    def write(self, vals):
        """Al modificar una operación, actualiza los saldos del cliente"""
        result = super(Operacion, self).write(vals)

        if any(
            field in vals
            for field in [
                "total",
                "monto_pagado",
                "cliente_id",
                "cantidad_kg",
                "precio_unitario",
            ]
        ):
            clientes_afectados = set()
            for record in self:
                if record.cliente_id:
                    clientes_afectados.add(record.cliente_id.id)

            # Recalcular para cada cliente afectado
            for cliente_id in clientes_afectados:
                operacion_cliente = self.search(
                    [("cliente_id", "=", cliente_id)], limit=1
                )
                if operacion_cliente:
                    operacion_cliente._recalcular_saldos_posteriores()
                    operacion_cliente._actualizar_saldo_cliente()

        return result

    # ========== MÉTODOS AUXILIARES ==========

    def _actualizar_saldo_cliente(self):
        """Actualiza el saldo total del cliente en la tabla sales.saldo_cliente"""
        if not self.cliente_id:
            return

        SaldoCliente = self.env["sales.saldo_cliente"]

        saldo_cliente = SaldoCliente.search(
            [("cliente_id", "=", self.cliente_id.id)],
            limit=1,
        )

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

        return {
            "type": "ir.actions.client",
            "tag": "reload",
        }

    def ver_historial(self):
        """Ver historial de operaciones del cliente"""
        self.ensure_one()

        if not self.cliente_id:
            raise UserError("No se puede mostrar el historial sin un cliente asociado.")

        return {
            "type": "ir.actions.act_window",
            "name": f"Historial del Cliente: {self.cliente_id.name}",
            "res_model": "sales.operacion",
            "view_mode": "tree,form",
            "domain": [("cliente_id", "=", self.cliente_id.id)],
            "context": {
                "default_cliente_id": self.cliente_id.id,
                "search_default_group_cliente": 1,
            },
            "target": "current",
        }
