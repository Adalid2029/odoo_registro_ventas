from odoo import models, fields

class OrdenProduccion(models.Model):
    _name = 'sales.op'
    _description = 'Orden de Producción'

    name = fields.Char(string='OP', required=True)

    _sql_constraints = [
        ('op_unique', 'unique(name)', 'La OP ya existe.'),
    ]