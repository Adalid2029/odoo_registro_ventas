from odoo import models, fields, api

class SaldoCliente(models.Model):
    _name = 'sales.saldo_cliente'
    _description = 'Saldo acumulado por cliente'
    _rec_name = 'cliente_id'

    cliente_id = fields.Many2one('res.partner', string='Cliente', required=True, 
                                domain=[('is_company', '=', True)], ondelete='cascade')
    saldo_total = fields.Float(string='Saldo Total', digits=(10, 2), default=0)
    fecha_actualizacion = fields.Datetime(string='Última Actualización', 
                                         default=fields.Datetime.now)
    
    # Campos relacionados para mostrar información del cliente
    cliente_email = fields.Char(related='cliente_id.email', string='Email Cliente', readonly=True)
    cliente_telefono = fields.Char(related='cliente_id.phone', string='Teléfono Cliente', readonly=True)
    
    # Conteo de operaciones del cliente
    total_operaciones = fields.Integer(string='Total Operaciones', 
                                      compute='_compute_total_operaciones')
    
    # Campo para mostrar el estado del cliente
    estado_cliente = fields.Selection([
        ('al_dia', 'Al Día'),
        ('pendiente', 'Saldo Pendiente'),
        ('adelanto', 'Adelanto')
    ], string='Estado Cliente', compute='_compute_estado_cliente', store=True)
    
    @api.depends('cliente_id')
    def _compute_total_operaciones(self):
        """Cuenta el número total de operaciones del cliente"""
        for record in self:
            if record.cliente_id:
                record.total_operaciones = self.env['sales.operacion'].search_count([
                    ('cliente_id', '=', record.cliente_id.id)
                ])
            else:
                record.total_operaciones = 0

    @api.depends('saldo_total')
    def _compute_estado_cliente(self):
        """Determina el estado general del cliente"""
        for record in self:
            if record.saldo_total == 0:
                record.estado_cliente = 'al_dia'
            elif record.saldo_total > 0:
                record.estado_cliente = 'pendiente'
            else:
                record.estado_cliente = 'adelanto'

    def action_ver_operaciones(self):
        """Acción para ver todas las operaciones del cliente"""
        return {
            'type': 'ir.actions.act_window',
            'name': f'Operaciones de {self.cliente_id.name}',
            'res_model': 'sales.operacion',
            'view_mode': 'list,form',
            'domain': [('cliente_id', '=', self.cliente_id.id)],
            'context': {
                'default_cliente_id': self.cliente_id.id,
                'search_default_cliente_id': self.cliente_id.id
            }
        }
    
    _sql_constraints = [
        ('unique_cliente', 'unique(cliente_id)', 'Ya existe un registro de saldo para este cliente')
    ]