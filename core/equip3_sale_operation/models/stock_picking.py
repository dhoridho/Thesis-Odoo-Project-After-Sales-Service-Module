from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from odoo.addons.stock.models.stock_rule import ProcurementException
from collections import defaultdict, namedtuple
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare, float_round, float_is_zero
from datetime import datetime, date, timedelta
import logging

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.constrains('sale_id')
    def set_analytic(self):
        for res in self:
           if res.sale_id:
                res.analytic_account_group_ids = res.sale_id.account_tag_ids

    @api.model
    def create(self, vals):
        res = super().create(vals)
        return res

    def write(self, vals):
        if not self.branch_id:
            if self.sale_id:
                vals['branch_id'] = self.sale_id.branch_id.id
        return super().write(vals)

    def is_do_approval_config(self):
        return self.env['ir.config_parameter'].sudo().get_param('is_delivery_order_approval_matrix', False)

    def query_insert_picking(self, vals={}):
        context = dict(self._context or {})
        picking_type_obj = self.env['stock.picking.type']
        sale_person_id = False
        if vals.get('sale_id'):
            sale_person_id = self.env['sale.order'].browse(vals['sale_id']).user_id.id

        user = self.env.user
        company = self.env.company
        now = datetime.now()
        str_now = str(now)
        datetime_now = now.strftime('%Y-%m-%d %H:%M:%S')
        query_create_picking = """
            INSERT INTO stock_picking (create_uid, create_date, write_uid, write_date,
                name, origin, move_type, state, priority, date, location_id, location_dest_id, picking_type_id, partner_id, company_id, is_locked, sale_id, branch_id, journal_cancel, active, operation_warehouse_id,
                immediate_transfer, is_do_request_approval_matrix, sales_person_id
            ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s
            )
            RETURNING id;
        """

        picking_type_id = vals.get('picking_type_id')
        picking_type = picking_type_obj.browse(picking_type_id)
        name = '/'
        if picking_type.sequence_id:
            name = picking_type.sequence_id.next_by_id()

        values_create_picking = [
            user.id,
            str_now,
            user.id,
            str_now,

            name,
            vals.get('origin') or None,
            vals.get('move_type') or None,
            'draft',
            '0',
            datetime_now,
            vals['location_id'],
            vals['location_dest_id'],
            vals['picking_type_id'],
            vals.get('partner_id') or None,
            vals.get('company_id') or company.id,
            True,
            vals.get('sale_id'),
            vals.get('branch_id') or None,
            False,
            True,
            picking_type.warehouse_id.id,

            False,
            self.is_do_approval_config(),
            sale_person_id
            ]
        # try:
        #     with self.env.cr.savepoint():
        self.env.cr.execute(query_create_picking, values_create_picking)
        picking_id = self.env.cr.fetchone()[0]
        picking = self.env['stock.picking'].browse(picking_id)
        # picking._compute_do_approving_matrix_lines()
        return picking


class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.model
    def create(self, vals):
        res = super(StockMove, self).create(vals)
        if res.sale_line_id:
            if res.sale_line_id.order_id.is_single_delivery_date:
                res.write({
                    'date': res.sale_line_id.order_id.commitment_date,
                    'date_deadline': res.sale_line_id.order_id.commitment_date
                })
            else:
                res.write({
                    'date': res.sale_line_id.multiple_do_date,
                    'date_deadline': res.sale_line_id.multiple_do_date
                })
            res.analytic_account_group_ids = res.sale_line_id.account_tag_ids
        if res.sale_line_id:
            res.branch_id = res.sale_line_id.branch_id.id
        return res

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
        is_product_service_operation_delivery = False
        for line in procurements:
            is_product_service_operation_delivery = line.product_id.is_product_service_operation_delivery
        # if not bool(self.env['ir.config_parameter'].sudo().get_param('is_product_service_operation_delivery')) and is_product_service_operation_delivery:
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
                        procurement.product_id.type not in ('consu', 'product') or
                        float_is_zero(procurement.product_qty, precision_rounding=procurement.product_uom.rounding)
                ):
                    continue
            else:
                product_template = procurement.product_id.product_tmpl_id
                product_categ_id = self.env['product.category'].search(
                    [('category_prefix', 'in', ('PRS', 'SRV')), ('stock_type', '=', 'service')]).ids
                if (
                        procurement.product_id.type not in ('consu', 'product','service') or product_template.categ_id.id in product_categ_id or
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
                error = _('No rule has been found to replenish "%s" in "%s".\nVerify the routes configuration on the product.') % \
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
        # else:
        #     #return super(ProcurementGroup, self).run(procurements, raise_user_error=True)
        #     return super(ProcurementGroup, self).run(procurements, raise_user_error=raise_user_error)