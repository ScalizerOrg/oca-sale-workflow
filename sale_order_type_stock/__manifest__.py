# Copyright 2015 Carlos Sánchez Cifuentes <csanchez@grupovermon.com>
# Copyright 2015-2016 Oihane Crucelaegui <oihane@avanzosc.com>
# Copyright 2015-2020 Tecnativa - Pedro M. Baeza
# Copyright 2023 Tecnativa - Sergio Teruel
# Copyright 2026 Scalizer
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Sale Order Type Stock",
    "version": "19.0.1.0.0",
    "category": "Sales Management",
    "author": "Grupo Vermon,"
    "AvanzOSC,"
    "Tecnativa,"
    "Agile Business Group,"
    "Niboo,"
    "Scalizer,"
    "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/sale-workflow",
    "license": "AGPL-3",
    "depends": ["sale_order_type", "sale_stock"],
    "data": [
        "views/sale_order_type_view.xml",
    ],
    "post_init_hook": "post_init_hook",
    "auto_install": True,
    "installable": True,
}
