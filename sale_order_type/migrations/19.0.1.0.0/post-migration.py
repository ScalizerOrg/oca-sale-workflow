import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Convert route_id Many2one field to route_ids Many2many field."""
    cr.execute(
        """
        INSERT INTO sale_order_type_stock_route_rel (sale_order_type_id, stock_route_id)
        SELECT id, route_id
        FROM sale_order_type
        WHERE route_id IS NOT NULL
        ON CONFLICT DO NOTHING
        """
    )
    _logger.info("sale_order_type: migrated route_id to route_ids (%d rows)", cr.rowcount)
