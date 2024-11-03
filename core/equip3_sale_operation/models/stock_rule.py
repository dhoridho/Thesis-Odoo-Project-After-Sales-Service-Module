
from odoo import _, api, fields, models
from collections import defaultdict
from odoo.exceptions import UserError
from odoo.tools import float_is_zero
from odoo.addons.stock.models.stock_rule import ProcurementException
import logging
_logger = logging.getLogger(__name__)
from odoo.osv import expression


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _get_stock_move_values(self, product_id, product_qty, product_uom, location_id, name, origin, company_id, values):
        res = super(StockRule, self)._get_stock_move_values(product_id, product_qty, product_uom, location_id, name, origin, company_id, values)
        if values.get('multiple_do') and values.get('delivery_address_id', False):
            res.update({'partner_id': values.get('delivery_address_id')})
        res.update({'branch_id': values.get('branch_id', False)})
        if values.get('picking_type_id', False):
            res.update({'picking_type_id': values.get('picking_type_id', False)})
        res.update({'initial_unit_of_measure': product_uom.id})

        return res


class ProcurementGroupInherit(models.Model):
    _inherit = 'procurement.group'

    # @api.model
    # def _get_rule(self, product_id, location_id, values):
    #     """ Find a pull rule for the location_id, fallback on the parent
    #     locations if it could not be found.
    #     """
    #     result = False
    #     so_id = self.env['sale.order.line'].browse(values['sale_line_id']).order_id
    #     if so_id.client_order_ref:
    #         if 'PO' in so_id.client_order_ref:
    #             location_id = self.env['stock.location'].browse(5)
    #     location = location_id
    #     while (not result) and location:
    #         domain = self._get_rule_domain(location, values)
    #         result = self._search_rule(values.get('route_ids', False), product_id, values.get('warehouse_id', False), domain)
    #         location = location.location_id
    #     return result
        
    @api.model
    def run_asset(self, procurements, raise_user_error=True):
        """Fulfil `procurements` with the help of stock rules.

        Procurements are needs of products at a certain location. To fulfil
        these needs, we need to create some sort of documents (`stock.move`
        by default, but extensions of `_run_` methods allow to create every
        type of documents).

        :param procurements: the description of the procurement
        :type list: list of `~odoo.addons.stock.models.stock_rule.ProcurementGroup.Procurement`
        :param raise_user_error: will raise either an UserError or a ProcurementException
        :type raise_user_error: boolan, optional
        :raises UserError: if `raise_user_error` is True and a procurement isn't fulfillable
        :raises ProcurementException: if `raise_user_error` is False and a procurement isn't fulfillable
        """
        context = dict(self.env.context) or {}
        is_product_service_operation_delivery = False
        for line in procurements:
            is_product_service_operation_delivery = line.product_id.is_product_service_operation_delivery

        def raise_exception(procurement_errors):
            if raise_user_error:
                dummy, errors = zip(*procurement_errors)
                raise UserError('\n'.join(errors))
            else:
                raise ProcurementException(procurement_errors)

        actions_to_run = defaultdict(list)
        procurement_errors = []
        for procurement in procurements:
            procurement.values.setdefault('company_id', procurement.location_id.company_id)
            procurement.values.setdefault('priority', '0')
            procurement.values.setdefault('date_planned', fields.Datetime.now())
            if not bool(self.env['ir.config_parameter'].sudo().get_param('is_product_service_operation_delivery')) and is_product_service_operation_delivery:
                if (
                        procurement.product_id.type not in ('consu','product','asset') or
                    float_is_zero(procurement.product_qty, precision_rounding=procurement.product_uom.rounding)
                ):
                    continue
            else:
                product_template = procurement.product_id.product_tmpl_id
                product_categ_id = self.env['product.category'].search(
                    [('category_prefix', 'in', ('PRS', 'SRV')), ('stock_type', '=', 'service')]).ids
                if (
                        procurement.product_id.type not in ('consu', 'product','asset','service') or product_template.categ_id.id in product_categ_id or
                        float_is_zero(procurement.product_qty, precision_rounding=procurement.product_uom.rounding)
                ):
                    continue
                if procurement.product_id.type == 'service' and product_template.categ_id.id not in product_categ_id:
                    if 'sale_line_id' in procurement.values:
                        if not procurement.product_id.is_product_service_operation_delivery:
                            continue
                    else:
                        if not procurement.product_id.is_product_service_operation_receiving:
                            continue
            rule = self._get_rule(procurement.product_id, procurement.location_id, procurement.values)
            if not rule:
                error = _('No rule has been found to replenish "%s" in "%s".\nVerify the routes configuration on the product.') %\
                    (procurement.product_id.display_name, procurement.location_id.display_name)
                procurement_errors.append((procurement, error))
            else:
                action = 'pull' if rule.action == 'pull_push' else rule.action
                actions_to_run[action].append((procurement, rule))

        if procurement_errors:
            raise_exception(procurement_errors)

        for action, procurements in actions_to_run.items():
            if hasattr(self.env['stock.rule'], '_run_%s' % action):
                try:
                    getattr(self.env['stock.rule'], '_run_%s' % action)(procurements)
                except ProcurementException as e:
                    procurement_errors += e.procurement_exceptions
            else:
                _logger.error("The method _run_%s doesn't exist on the procurement rules" % action)

        if procurement_errors:
            raise_exception(procurement_errors)
        return True