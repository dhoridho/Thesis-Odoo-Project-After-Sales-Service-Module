from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero
from odoo.addons.stock.models.stock_rule import ProcurementException
from collections import defaultdict
import logging
_logger = logging.getLogger(__name__)


class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    @api.model
    def run(self, procurements, raise_user_error=True):
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
        if bool(self.env['ir.config_parameter'].sudo().get_param('is_product_service_operation_delivery')):
            def raise_exception(procurement_errors):
                if raise_user_error:
                    dummy, errors = zip(*procurement_errors)
                    raise UserError('\n'.join(errors))
                else:
                    raise ProcurementException(procurement_errors)

            actions_to_run = defaultdict(list)
            procurement_errors = []
            for procurement in procurements:
                procurement.values.setdefault(
                    'company_id', procurement.location_id.company_id)
                procurement.values.setdefault('priority', '0')
                procurement.values.setdefault(
                    'date_planned', fields.Datetime.now())
                if (
                    procurement.product_id.type not in ('consu', 'product') or
                    float_is_zero(
                        procurement.product_qty, precision_rounding=procurement.product_uom.rounding)
                ):
                    if 'sale_line_id' in procurement.values:
                        if not procurement.product_id.is_product_service_operation_delivery:
                            continue
                    else:
                        if not procurement.product_id.is_product_service_operation_receiving:
                            continue
                rule = self._get_rule(
                    procurement.product_id, procurement.location_id, procurement.values)
                if not rule:
                    error = _('No rule has been found to replenish "%s" in "%s".\nVerify the routes configuration on the product.') %\
                        (procurement.product_id.display_name,
                         procurement.location_id.display_name)
                    procurement_errors.append((procurement, error))
                else:
                    action = 'pull' if rule.action == 'pull_push' else rule.action
                    actions_to_run[action].append((procurement, rule))

            if procurement_errors:
                raise_exception(procurement_errors)

            for action, procurements in actions_to_run.items():
                if hasattr(self.env['stock.rule'], '_run_%s' % action):
                    try:
                        getattr(self.env['stock.rule'],
                                '_run_%s' % action)(procurements)
                    except ProcurementException as e:
                        procurement_errors += e.procurement_exceptions
                else:
                    _logger.error(
                        "The method _run_%s doesn't exist on the procurement rules" % action)

            if procurement_errors:
                raise_exception(procurement_errors)
            return True
        else:
            # return super(ProcurementGroup, self).run(procurements, raise_user_error=True)
            return super(ProcurementGroup, self).run(procurements, raise_user_error=raise_user_error)
