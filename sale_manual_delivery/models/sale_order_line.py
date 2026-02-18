# Copyright 2017 Denis Leemann, Camptocamp SA
# Copyright 2021 Iván Todorovich, Camptocamp SA
# Copyright 2026 Scalizer
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from datetime import timedelta

from odoo import api, fields, models
from odoo.tools import float_compare


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    qty_procured = fields.Float(
        string="Quantity Procured",
        help="Quantity already planned or shipped (stock movements already created)",
        compute="_compute_qty_procured",
        readonly=True,
        store=True,
    )
    qty_to_procure = fields.Float(
        string="Quantity to Procure",
        help="There is Pending qty to add to a delivery",
        compute="_compute_qty_to_procure",
        store=True,
        readonly=True,
    )

    @api.depends(
        "move_ids.state",
        "move_ids.product_uom_qty",
        "move_ids.product_uom",
        "move_ids.location_id",
        "move_ids.location_dest_id",
        "move_ids.location_dest_id.usage",
    )
    def _compute_qty_procured(self):
        """
        Computes the already planned quantities for the given sale order lines,
        based on the existing stock.moves
        """
        for line in self:
            qty_procured = 0
            if line.qty_delivered_method == "stock_move":
                qty_procured = line._get_qty_procurement(previous_product_uom_qty=False)
            line.qty_procured = qty_procured

    @api.depends("product_uom_qty", "qty_procured")
    def _compute_qty_to_procure(self):
        """Computes the remaining quantity to plan on sale order lines"""
        for line in self:
            line.qty_to_procure = line.product_uom_qty - line.qty_procured

    def _prepare_procurement_values(self):
        # Overload to handle manual delivery date planned, date_deadline and route
        # This method ultimately prepares stock.move vals as its result is sent
        # to StockRule._get_stock_move_values.
        # Note: sale_manual_delivery is expected to be a manual.delivery record
        res = super()._prepare_procurement_values()
        manual_delivery = self.env.context.get("sale_manual_delivery")
        if manual_delivery:
            if manual_delivery.date_planned:
                res["date_planned"] = manual_delivery.date_planned
                date_deadline = manual_delivery.date_planned + timedelta(
                    days=self.order_id.company_id.security_lead)
                res["date_deadline"] = date_deadline
            if manual_delivery.route_id:
                res["route_ids"] = manual_delivery.route_id
        return res

    def _action_launch_stock_rule_manual(self, previous_product_uom_qty=False):
        # Note: sale_manual_delivery is expected to be a manual.delivery record
        """Create procurements based on quantities entered in the wizard."""
        manual_delivery = self.env.context.get("sale_manual_delivery")
        if not manual_delivery:
            return True

        if self.env.context.get("skip_procurement"):
            return True

        precision = self.env["decimal.precision"].precision_get("Product Unit")
        procurements = []
        for line in self:
            line = line.with_company(line.company_id)
            if line.state != "sale" or line.order_id.locked or line.product_id.type != "consu":
                continue

            # Qty comes from the manual delivery wizard
            manual_line = manual_delivery.line_ids.filtered(
                lambda mdl, ln=line: mdl.order_line_id == ln
            )
            manual_qty = manual_line[:1].quantity
            if not manual_qty:
                continue
            remaining = line.product_uom_qty - line._get_qty_procurement(
                previous_product_uom_qty)
            if float_compare(manual_qty, remaining, precision_digits=precision) > 0:
                manual_qty = remaining
            if not manual_qty:
                continue

            references = line.order_id.stock_reference_ids
            if not references:
                self.env['stock.reference'].create(line._prepare_reference_vals())

            values = line._prepare_procurement_values()

            line_uom = line.product_uom_id
            quant_uom = line.product_id.uom_id
            product_qty, procurement_uom = line_uom._adjust_uom_quantities(
                manual_qty, quant_uom
            )
            procurements += line._create_procurements(product_qty, procurement_uom,
                                                      values)

        if procurements:
            self.env["stock.rule"].run(procurements)
        orders = self.mapped("order_id")
        for order in orders:
            pickings_to_confirm = order.picking_ids.filtered(
                lambda p: p.state not in ["cancel", "done"]
            )
            if pickings_to_confirm:
                pickings_to_confirm.action_confirm()
        return True

    def _action_launch_stock_rule(self, previous_product_uom_qty=False):
        # Overload to skip launching stock rules on manual delivery lines
        # We only launch them when this is called from the manual delivery wizard
        # Note: sale_manual_delivery is expected to be a manual.delivery record
        manual_delivery_lines = self.filtered("order_id.manual_delivery")
        lines_to_launch = self - manual_delivery_lines
        return super(SaleOrderLine, lines_to_launch)._action_launch_stock_rule(
            previous_product_uom_qty=previous_product_uom_qty
        )
