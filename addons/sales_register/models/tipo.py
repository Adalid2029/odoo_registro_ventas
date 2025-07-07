from odoo import models, fields

class Tipo(models.Model):
    # Aqui ingresara Bolsas, Paquetes, Bobinas, etc.
    _name = 'sales.tipo'
    _description = 'Tipo de Producto'

    name = fields.Char(string='Tipo', required=True)

    _sql_constraints = [
        ('tipo_unique', 'unique(name)', 'El tipo ya existe.'),
    ]