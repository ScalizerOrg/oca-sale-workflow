# Copyright 2026 Scalizer
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Convert the legacy ``route_id`` Many2one into the ``route_ids`` Many2many.

    The conversion used to live in a ``sale_order_type`` migration script, but
    the routes now belong to this glue module, which is freshly installed (and
    thus never migrated) on databases coming from an older version. The
    statement is idempotent, so running it again on an already converted
    database is a no-op.
    """
    cr = env.cr
    cr.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'sale_order_type' AND column_name = 'route_id'
        """
    )
    if not cr.fetchone():
        return
    cr.execute(
        """
        INSERT INTO sale_order_type_stock_route_rel (sale_order_type_id, stock_route_id)
        SELECT id, route_id
        FROM sale_order_type
        WHERE route_id IS NOT NULL
        ON CONFLICT DO NOTHING
        """
    )
    _logger.info(
        "sale_order_type_stock: migrated route_id to route_ids (%d rows)", cr.rowcount
    )
