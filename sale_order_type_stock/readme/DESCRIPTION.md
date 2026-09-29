Glue module between `sale_order_type` and `sale_stock`.

It adds the stock related settings to the sale order types: warehouse,
stock routes, shipping policy and incoterm. Those settings are then
propagated to the sale orders (and their lines) using the type.

This module is auto installed when both `sale_order_type` and
`sale_stock` are installed, so that `sale_order_type` itself stays
usable on databases without the Inventory application.
