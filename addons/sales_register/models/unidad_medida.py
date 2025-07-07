from odoo import models, fields

class UnidadMedida(models.Model):
    _name = 'sales.unidad_medida'
    _description = 'Unidad de Medida'

    name = fields.Char(string='Unidad', required=True)

    _sql_constraints = [
        ('unidad_unique', 'unique(name)', 'La unidad ya existe.'),
    ]