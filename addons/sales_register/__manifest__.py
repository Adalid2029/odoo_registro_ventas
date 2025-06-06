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
    """,
    "data": [
        "security/ir.model.access.csv",
        "data/categoria_data.xml",
        "views/categoria_views.xml",
        "views/metodo_pago_views.xml",
        "views/operacion_views.xml",
        "views/saldo_cliente_views.xml",
        "views/menu_views.xml",
    ],
    "demo": [],
    "installable": True,
    "auto_install": False,
    "application": True,
}
