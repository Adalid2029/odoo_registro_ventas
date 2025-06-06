from odoo import models, fields, api

class Categoria(models.Model):
    _name = 'sales.categoria'
    _description = 'Categorías de productos para ventas'
    _rec_name = 'nombre'

    nombre = fields.Char(string='Nombre', required=True, size=100)
    descripcion = fields.Text(string='Descripción')
    
    # Campos de auditoría automáticos en Odoo
    # create_date y write_date se crean automáticamente
    
    def name_get(self):
        """Personaliza cómo se muestra el registro en campos de selección"""
        result = []
        for record in self:
            result.append((record.id, record.nombre))
        return result