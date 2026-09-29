# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class SaleOrderTypology(models.Model):
    _inherit = "sale.order.type"

    warehouse_id = fields.Many2one(
        comodel_name="stock.warehouse", string="Warehouse", check_company=True
    )
    picking_policy = fields.Selection(
        selection=lambda self: self._get_selection_picking_policy(),
        string="Shipping Policy",
        default=lambda self: self.env["sale.order"]
        .default_get(["picking_policy"])
        .get("picking_policy"),
    )
    incoterm_id = fields.Many2one(comodel_name="account.incoterms", string="Incoterm")
    route_ids = fields.Many2many(
        "stock.route",
        string="Routes",
        domain=[("sale_selectable", "=", True)],
        ondelete="restrict",
        check_company=True,
    )

    @api.model
    def _get_selection_picking_policy(self):
        return self.env["sale.order"].fields_get(allfields=["picking_policy"])[
            "picking_policy"
        ]["selection"]
