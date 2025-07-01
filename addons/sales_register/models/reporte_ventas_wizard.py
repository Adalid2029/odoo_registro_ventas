from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class ReporteVentasWizard(models.TransientModel):
    _name = "sales.reporte.ventas.wizard"
    _description = "Wizard para Reporte de Ventas"

    # CAMPOS DEL WIZARD
    fecha_inicio = fields.Date(
        string="Fecha Inicio",
        required=True,
        default=lambda self: fields.Date.today().replace(day=1),
    )
    fecha_fin = fields.Date(
        string="Fecha Fin", required=True, default=fields.Date.today
    )

    tipo_reporte = fields.Selection(
        [
            ("venta", "Ventas"),
            ("compra", "Compras"),
            ("nota_remision", "Notas de Remisión"),
        ],
        string="Tipo de Reporte",
        default="venta",
        required=True,
    )

    estado_pago = fields.Selection(
        [
            ("todos", "Todos"),
            ("pagado", "Pagados"),
            ("pendiente", "Pendientes"),
            ("parcial", "Pagos Parciales"),
        ],
        string="Estado de Pago",
        default="todos",
        required=True,
    )

    @api.constrains("fecha_inicio", "fecha_fin")
    def _check_fechas(self):
        """Validar fechas"""
        for record in self:
            if record.fecha_inicio > record.fecha_fin:
                raise UserError(
                    "La fecha de inicio debe ser menor o igual a la fecha de fin."
                )

    def generar_reporte_pdf(self):
        """Genera el reporte PDF - VERSIÓN SIMPLIFICADA"""
        self.ensure_one()

        try:
            # VERIFICAR QUE EXISTAN OPERACIONES EN EL SISTEMA
            todas_operaciones = self.env["sales.operacion"].search([])
            if not todas_operaciones:
                raise UserError("No hay operaciones registradas en el sistema.")

            # LOG DE DEBUG (opcional)
            _logger.info(
                f"Generando reporte: {self.tipo_reporte} del {self.fecha_inicio} al {self.fecha_fin}"
            )

            # El template se encargará de filtrar y procesar los datos
            return self.env.ref("sales_register.action_report_ventas").report_action(
                self
            )

        except Exception as e:
            _logger.error("Error generando reporte: %s", str(e))
            raise UserError(f"Error al generar el reporte: {str(e)}")
