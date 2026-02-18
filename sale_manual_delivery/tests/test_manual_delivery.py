# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.sale.tests.common import TestSaleCommon


@tagged("post_install", "-at_install")
class TestSaleStock(TestSaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Use stable partner from TestSaleCommon (no demo xmlid dependency)
        cls.partner = cls.partner_a

        # Stock location
        cls.stock_location = cls.env.ref("stock.stock_location_stock")

        cls.product = cls.env["product.product"].create(
            {
                "name": "Test Delivery Product 1",
                "type": "consu",
                "is_storable": True,
                "uom_id": cls.uom_unit.id,
                "list_price": 100.0,
            }
        )
        cls.product2 = cls.env["product.product"].create(
            {
                "name": "Test Delivery Product 2",
                "type": "consu",
                "is_storable": True,
                "uom_id": cls.uom_unit.id,
                "list_price": 120.0,
            }
        )
        cls.product3 = cls.env["product.product"].create(
            {
                "name": "Test Delivery Product 3",
                "type": "consu",
                "is_storable": True,
                "uom_id": cls.uom_unit.id,
                "list_price": 90.0,
            }
        )

        # Put stock
        cls.env["stock.quant"]._update_available_quantity(
            cls.product, cls.stock_location, 100
        )
        cls.env["stock.quant"]._update_available_quantity(
            cls.product2, cls.stock_location, 100
        )
        cls.env["stock.quant"]._update_available_quantity(
            cls.product3, cls.stock_location, 100
        )

        # Create a basic salesman user (avoid base.user_demo dependency)
        cls.user_demo = cls.env["res.users"].create(
            {
                "name": "Demo Sales User",
                "login": "demo_sales_user",
                "email": "demo_sales_user@example.com",
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            cls.env.ref("base.group_user").id,
                            cls.env.ref("sales_team.group_sale_salesman").id,
                        ],
                    )
                ],
                "company_id": cls.env.company.id,
                "company_ids": [(6, 0, cls.env.company.ids)],
            }
        )

        # Create 2 fixed carriers (avoid delivery demo xmlids)
        delivery_product = cls.env["product.product"].create(
            {
                "name": "Delivery Service",
                "type": "service",
                "uom_id": cls.uom_unit.id,
                "list_price": 10.0,
            }
        )
        cls.carrier1 = cls.env["delivery.carrier"].create(
            {
                "name": "Carrier Fixed 1",
                "delivery_type": "fixed",
                "fixed_price": 10.0,
                "product_id": delivery_product.id,
            }
        )
        cls.carrier2 = cls.env["delivery.carrier"].create(
            {
                "name": "Carrier Fixed 2",
                "delivery_type": "fixed",
                "fixed_price": 20.0,
                "product_id": delivery_product.id,
            }
        )

    def _manual_delivery_wizard(self, records, vals=None):
        vals = vals or {}
        return (
            self.env["manual.delivery"]
            .with_context(active_model=records._name, active_ids=records.ids)
            .create(vals)
        )

    def _deliver_qty(self, picking, qty):
        picking.action_assign()
        picking.move_line_ids.write({"quantity": qty})
        picking.button_validate()

    def test_00_sale_manual_delivery(self):
        """Test SO's manual delivery with a non-admin user."""
        model_user_order = self.env["sale.order"].with_user(self.user_demo)
        order = model_user_order.create(
            {
                "partner_id": self.partner.id,
                "partner_invoice_id": self.partner.id,
                "partner_shipping_id": self.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "name": self.product.name,
                            "product_id": self.product.id,
                            "product_uom_qty": 5.0,
                            "product_uom_id": self.product.uom_id.id,
                            "price_unit": self.product.list_price,
                        },
                    )
                ],
                "manual_delivery": True,
            }
        )
        order.action_confirm()
        self.assertFalse(
            order.picking_ids,
            'No picking should be created for "manual delivery" orders',
        )

        with self.assertRaises(UserError):
            order.write({"manual_delivery": False})

        action = order.action_manual_delivery_wizard()
        self.assertEqual(action["res_model"], "manual.delivery")

        self._manual_delivery_wizard(order).confirm()
        self.assertTrue(order.picking_ids)

        wizard = self._manual_delivery_wizard(order)
        self.assertFalse(wizard.line_ids)
        wizard.confirm()
        self.assertEqual(len(order.picking_ids), 1)

    def test_01_sale_standard_delivery(self):
        """Test SO's standard delivery."""
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "partner_invoice_id": self.partner.id,
                "partner_shipping_id": self.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "name": self.product.name,
                            "product_id": self.product.id,
                            "product_uom_qty": 5.0,
                            "product_uom_id": self.product.uom_id.id,
                            "price_unit": self.product.list_price,
                        },
                    )
                ],
                "manual_delivery": False,
            }
        )
        order.action_confirm()
        self.assertTrue(order.picking_ids)

        pick = order.picking_ids
        self._deliver_qty(pick, 5)

        del_qty = sum(sol.qty_delivered for sol in order.order_line)
        self.assertEqual(del_qty, 5.0)

    def test_02_sale_various_manual_delivery(self):
        """Test partial manual deliveries, no-op deliveries, and over-delivery."""
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "partner_invoice_id": self.partner.id,
                "partner_shipping_id": self.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "name": self.product.name,
                            "product_id": self.product.id,
                            "product_uom_qty": 5.0,
                            "product_uom_id": self.product.uom_id.id,
                            "price_unit": self.product.list_price,
                        },
                    )
                ],
                "manual_delivery": True,
            }
        )
        order.action_confirm()
        self.assertFalse(order.picking_ids)

        wizard = self._manual_delivery_wizard(order)
        wizard.line_ids.write({"quantity": 2.0})
        wizard.confirm()
        self.assertTrue(order.has_pending_delivery)
        self.assertEqual(len(order.picking_ids), 1)

        self._deliver_qty(order.picking_ids, 2)
        del_qty = sum(sol.qty_delivered for sol in order.order_line)
        self.assertEqual(del_qty, 2.0)

        wizard = self._manual_delivery_wizard(order)
        wizard.line_ids.write({"quantity": 0.0})
        wizard.confirm()
        self.assertEqual(len(order.picking_ids), 1)

        wizard = self._manual_delivery_wizard(order)
        with self.assertRaises(UserError):
            wizard.line_ids.write({"quantity": 10.0})
            wizard.confirm()

        wizard = self._manual_delivery_wizard(order)
        wizard.line_ids.write({"quantity": 3.0})
        wizard.confirm()
        self.assertFalse(order.has_pending_delivery)
        self.assertEqual(len(order.picking_ids), 2)

    def test_03_sale_selected_lines(self):
        """Wizard on selected SOLs across multiple SOs."""
        order1 = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "partner_invoice_id": self.partner.id,
                "partner_shipping_id": self.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "name": self.product.name,
                            "product_id": self.product.id,
                            "product_uom_qty": 1.0,
                            "product_uom_id": self.product.uom_id.id,
                            "price_unit": self.product.list_price,
                        },
                    )
                ],
                "manual_delivery": True,
            }
        )
        order2 = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "partner_invoice_id": self.partner.id,
                "partner_shipping_id": self.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "name": self.product2.name,
                            "product_id": self.product2.id,
                            "product_uom_qty": 2.0,
                            "product_uom_id": self.product2.uom_id.id,
                            "price_unit": self.product2.list_price,
                        },
                    )
                ],
                "manual_delivery": True,
            }
        )
        order3 = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "partner_invoice_id": self.partner.id,
                "partner_shipping_id": self.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "name": self.product3.name,
                            "product_id": self.product3.id,
                            "product_uom_qty": 3.0,
                            "product_uom_id": self.product3.uom_id.id,
                            "price_unit": self.product3.list_price,
                        },
                    )
                ],
                "manual_delivery": True,
            }
        )

        order1.action_confirm()
        order2.action_confirm()
        order3.action_confirm()

        some_lines = order1.order_line | order3.order_line
        all_lines = order1.order_line | order2.order_line | order3.order_line

        wizard = self._manual_delivery_wizard(some_lines)
        self.assertEqual(sum(wizard.line_ids.mapped("quantity")), 4.0)
        wizard.confirm()

        self.assertTrue(order3.picking_ids)
        self.assertEqual(len(order3.picking_ids.move_ids), 1)
        self.assertFalse(order2.picking_ids)

        undelivered = self.env["sale.order.line"].search(
            [
                ("qty_to_procure", ">", 0),
                ("state", "=", "sale"),
                ("id", "in", all_lines.ids),
            ]
        )
        self.assertEqual(undelivered, order2.order_line)

    def test_04_sale_multi_delivery(self):
        """Pickings split by date_planned."""
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "partner_invoice_id": self.partner.id,
                "partner_shipping_id": self.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "name": self.product.name,
                            "product_id": self.product.id,
                            "product_uom_qty": 10.0,
                            "product_uom_id": self.product.uom_id.id,
                            "price_unit": self.product.list_price,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": self.product2.name,
                            "product_id": self.product2.id,
                            "product_uom_qty": 10.0,
                            "product_uom_id": self.product2.uom_id.id,
                            "price_unit": self.product2.list_price,
                        },
                    ),
                ],
                "manual_delivery": True,
            }
        )
        order.action_confirm()
        self.assertFalse(order.picking_ids)

        date_now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        wizard = self._manual_delivery_wizard(
            order.order_line[0],
            {"carrier_id": order.carrier_id.id, "date_planned": date_now},
        )
        wizard.line_ids.write({"quantity": 2.0})
        wizard.confirm()

        self.assertEqual(len(order.picking_ids), 1)
        first_picking = order.picking_ids
        self.assertEqual(
            first_picking.scheduled_date.replace(
                hour=0, minute=0, second=0, microsecond=0
            ),
            date_now,
        )

        date_next_week = date_now + relativedelta(weeks=1)
        wizard = self._manual_delivery_wizard(
            order.order_line[1],
            {"carrier_id": order.carrier_id.id, "date_planned": date_next_week},
        )
        wizard.line_ids.write({"quantity": 3.0})
        wizard.confirm()

        self.assertEqual(len(order.picking_ids), 2)
        second_picking = order.picking_ids - first_picking
        self.assertEqual(
            second_picking.scheduled_date.replace(
                hour=0, minute=0, second=0, microsecond=0
            ),
            date_next_week,
        )

        new_date_now = datetime.now()
        wizard = self._manual_delivery_wizard(
            order.order_line[0],
            {"carrier_id": order.carrier_id.id, "date_planned": new_date_now},
        )
        wizard.line_ids.write({"quantity": 5.0})
        wizard.confirm()

        self.assertEqual(len(order.picking_ids), 2)
        self.assertEqual(sum(first_picking.mapped("move_ids.product_uom_qty")), 7)

    def test_05_sale_single_picking(self):
        """Wizard on all SOLs of same SO => single picking."""
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "partner_invoice_id": self.partner.id,
                "partner_shipping_id": self.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "name": self.product.name,
                            "product_id": self.product.id,
                            "product_uom_qty": 1.0,
                            "product_uom_id": self.product.uom_id.id,
                            "price_unit": self.product.list_price,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": self.product2.name,
                            "product_id": self.product2.id,
                            "product_uom_qty": 2.0,
                            "product_uom_id": self.product2.uom_id.id,
                            "price_unit": self.product2.list_price,
                        },
                    ),
                ],
                "manual_delivery": True,
            }
        )
        order.action_confirm()
        wizard = self._manual_delivery_wizard(order.order_line)
        wizard.confirm()
        self.assertEqual(len(order.picking_ids), 1)

    def test_06_sale_multi_carrier(self):
        """Different carrier => different picking. Same carrier => reuse picking."""
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "partner_invoice_id": self.partner.id,
                "partner_shipping_id": self.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "name": self.product.name,
                            "product_id": self.product.id,
                            "product_uom_qty": 10.0,
                            "product_uom_id": self.product.uom_id.id,
                            "price_unit": self.product.list_price,
                        },
                    ),
                ],
                "manual_delivery": True,
                "carrier_id": self.carrier1.id,
            }
        )
        order.action_confirm()

        wizard = self._manual_delivery_wizard(order, {"carrier_id": self.carrier1.id})
        wizard.line_ids.write({"quantity": 2.0})
        wizard.confirm()

        self.assertEqual(len(order.picking_ids), 1)
        first_picking = order.picking_ids
        self.assertEqual(first_picking.carrier_id, order.carrier_id)

        wizard = self._manual_delivery_wizard(order, {"carrier_id": self.carrier2.id})
        wizard.line_ids.write({"quantity": 2.0})
        wizard.confirm()

        self.assertEqual(len(order.picking_ids), 2)
        second_picking = order.picking_ids - first_picking
        self.assertEqual(second_picking.carrier_id, self.carrier2)

        wizard = self._manual_delivery_wizard(order, {"carrier_id": self.carrier1.id})
        wizard.line_ids.write({"quantity": 2.0})
        wizard.confirm()

        self.assertEqual(len(order.picking_ids), 2)
