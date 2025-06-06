from odoo import models, fields, api

class MetodoPago(models.Model):
    _name = 'sales.metodo_pago'
    _description = 'Métodos de pago disponibles'
    _rec_name = 'nombre'

    nombre = fields.Char(string='Nombre', required=True, size=100)
    descripcion = fields.Text(string='Descripción')
    
    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, record.nombre))
        return result