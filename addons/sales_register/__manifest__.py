{
    "name": "Registro de Ventas",
    "version": "1.0.0",
    "depends": ["base", "product", "sale"],
    "author": "Tu Empresa",
    "category": "Sales",
    "license": "LGPL-3",
    "description": """
    Módulo para el registro y seguimiento de operaciones de venta.
    Incluye:
    - Gestión de categorías
    - Métodos de pago
    - Operaciones de venta con saldos
    - Control de saldos por cliente
    - Reportes de ventas en PDF
    """,
    "data": [
        "security/sales_register_security.xml",
        "security/ir.model.access.csv",
        # 1. DATOS INICIALES PRIMERO
        "data/categoria_data.xml",
        # 2. VISTAS DE MODELOS (esto crea los modelos en la base de datos)
        "views/categoria_views.xml",
        "views/metodo_pago_views.xml",
        "views/operacion_views.xml",
        "views/saldo_cliente_views.xml",
        "views/reporte_ventas_wizard_views.xml",
        # 3. REPORTES
        "reports/reporte_ventas_template.xml",
        # 4. SEGURIDAD AL FINAL (después de que los modelos existan)
        # 5. MENÚS AL FINAL DE TODO
        "views/menu_views.xml",
    ],
    "demo": [],
    "installable": True,
    "auto_install": False,
    "application": True,
}
