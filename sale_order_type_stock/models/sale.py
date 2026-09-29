# Copyright 2020 Tecnativa - Pedro M. Baeza
# Copyright 2023 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    # Fields converted to computed writable
    picking_policy = fields.Selection(
        compute="_compute_picking_policy", store=True, readonly=False
    )
    incoterm = fields.Many2one(compute="_compute_incoterm", store=True, readonly=False)

    @api.depends("type_id")
    def _compute_warehouse_id(self):
        res = super()._compute_warehouse_id()
        for order in self.filtered("type_id"):
            order_type = order.type_id
            if order_type.warehouse_id:
                order.warehouse_id = order_type.warehouse_id
        return res

    def _depends_picking_policy(self):
        depends = []
        if hasattr(super(), "_depends_picking_policy"):
            depends = super()._depends_picking_policy()
        depends.append("type_id")
        return depends

    @api.depends(lambda self: self._depends_picking_policy())
    def _compute_picking_policy(self):
        res = None
        if hasattr(super(), "_compute_picking_policy"):
            res = super()._compute_picking_policy()
        for order in self.filtered("type_id"):
            order_type = order.type_id
            if order_type.picking_policy:
                order.picking_policy = order_type.picking_policy
        return res

    @api.depends("type_id")
    def _compute_incoterm(self):
        res = None
        if hasattr(super(), "_compute_incoterm"):
            res = super()._compute_incoterm()
        for order in self.filtered("type_id"):
            order_type = order.type_id
            if order_type.incoterm_id:
                order.incoterm = order_type.incoterm_id
        return res


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    route_ids = fields.Many2many(
        compute="_compute_route_ids", store=True, readonly=False, precompute=True
    )

    @api.depends("order_id.type_id")
    def _compute_route_ids(self):
        res = None
        if hasattr(super(), "_compute_route_ids"):
            res = super()._compute_route_ids()
        for line in self.filtered("order_id.type_id"):
            order_type = line.order_id.type_id
            if order_type.route_ids:
                line.route_ids = order_type.route_ids
        return res
