# Copyright 2015 Oihane Crucelaegui - AvanzOSC
# Copyright 2017 Pierre Faniel - Niboo SPRL (<https://www.niboo.be/>)
# Copyright 2020 Tecnativa - Pedro M. Baeza
# Copyright 2026 Scalizer
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from odoo.tests import Form

from odoo.addons.base.tests.common import BaseCommon


class TestSaleOrderTypeStock(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sale_type_model = cls.env["sale.order.type"]
        cls.partner = cls.env.ref("base.main_partner")
        cls.journal = cls.env["account.journal"].search(
            [("type", "=", "sale")], limit=1
        )
        cls.sequence = cls.env["ir.sequence"].create(
            {
                "name": "Test Sales Order",
                "code": "sale.order",
                "prefix": "TSO",
                "padding": 3,
            }
        )
        cls.warehouse = cls.env["stock.warehouse"].create(
            {"name": "Warehouse Test", "code": "WT"}
        )
        cls.product = cls.env["product.product"].create(
            {"type": "service", "invoice_policy": "order", "name": "Test product"}
        )
        cls.immediate_payment = cls.env.ref("account.account_payment_term_immediate")
        cls.sale_pricelist = cls.env["product.pricelist"].create(
            {"name": "Public Pricelist", "sequence": 1}
        )
        cls.free_carrier = cls.env.ref("account.incoterm_FCA")
        cls.sale_type = cls.sale_type_model.create(
            {
                "name": "Test Sale Order Type",
                "sequence_id": cls.sequence.id,
                "journal_id": cls.journal.id,
                "warehouse_id": cls.warehouse.id,
                "picking_policy": "one",
                "payment_term_id": cls.immediate_payment.id,
                "pricelist_id": cls.sale_pricelist.id,
                "incoterm_id": cls.free_carrier.id,
            }
        )
        cls.partner.sale_type = cls.sale_type
        cls.sale_route = cls.env["stock.route"].create(
            {
                "name": "SO -> Customer",
                "product_selectable": True,
                "sale_selectable": True,
                "rule_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "SO -> Customer",
                            "action": "pull",
                            "picking_type_id": cls.env.ref("stock.picking_type_in").id,
                            "location_src_id": cls.warehouse.lot_stock_id.id,
                            "location_dest_id": cls.env.ref(
                                "stock.stock_location_customers"
                            ).id,
                        },
                    )
                ],
            }
        )
        cls.sale_type_route = cls.sale_type.copy(
            {
                "name": "Test Sale Order Type-1",
                "sequence_id": cls.sequence.id,
                "route_ids": [(6, 0, [cls.sale_route.id])],
            }
        )

    def create_sale_order(self, partner=False):
        sale_form = Form(self.env["sale.order"])
        sale_form.partner_id = partner or self.partner
        with sale_form.order_line.new() as order_line:
            order_line.product_id = self.product
            order_line.product_uom_qty = 1.0
        return sale_form.save()

    def test_sale_order_stock_propagation(self):
        sale_type = self.sale_type
        order = self.create_sale_order()
        self.assertEqual(order.type_id, sale_type)
        self.assertEqual(order.warehouse_id, sale_type.warehouse_id)
        self.assertEqual(order.picking_policy, sale_type.picking_policy)
        self.assertEqual(order.incoterm, sale_type.incoterm_id)

    def test_sale_order_flow_route(self):
        order = self.create_sale_order()
        order.type_id = self.sale_type_route.id
        self.assertEqual(order.type_id.route_ids, order.order_line[0].route_ids)
        sale_line_dict = {
            "product_id": self.product.id,
            "name": self.product.name,
            "product_uom_qty": 2.0,
            "price_unit": self.product.lst_price,
        }
        order.write({"order_line": [(0, 0, sale_line_dict)]})
        self.assertEqual(order.type_id.route_ids, order.order_line[1].route_ids)
