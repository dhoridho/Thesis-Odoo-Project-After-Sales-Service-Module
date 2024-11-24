
from odoo import models, fields, api, _
from psycopg2 import OperationalError
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from odoo.addons.stock.models.stock_quant import StockQuant as BasicStockQuant
from odoo.exceptions import ValidationError


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    forecast_incoming = fields.Float(
        string="Forecast Incoming", compute="_compute_forecast_incoming", store=False)
    forecast_outgoing = fields.Float(
        string="Forecast Outgoing", compute="_compute_forecast_incoming")
    forecast_qty = fields.Float(
        string="Forecasted Quantity", compute="_compute_forecast_incoming")
    move_id = fields.Many2one('stock.move', string='Stock Move')
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain.extend([('quantity', '!=', 0.0)])
        return super(StockQuant, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
    
    @api.constrains("product_id", "quantity")
    def check_negative_qty(self):
        p = self.env["decimal.precision"].precision_get("Product Unit of Measure")
        disallowed_negative = self.env['ir.config_parameter'].sudo().get_param('qty_can_minus', False)
        if not disallowed_negative:
            return

        for quant in self:
            if (
                float_compare(quant.quantity, 0, precision_digits=p) == -1
                and quant.product_id.type == "product"
                and quant.location_id.usage in ["internal", "transit"]
            ):
                msg_add = ""
                if quant.lot_id:
                    msg_add = _(" lot '%s'") % quant.lot_id.name_get()[0][1]
                raise ValidationError(
                    _(
                        "You cannot validate this stock operation because the "
                        "stock level of the product '%s'%s would become negative "
                        "(%s) on the stock location '%s' and negative stock is "
                        "not allowed for this product and/or location."
                    )
                    % (
                        quant.product_id.display_name,
                        msg_add,
                        quant.quantity,
                        quant.location_id.complete_name,
                    )
                )

    @api.model
    def create(self, vals):
        """ Not sure what the purpose of the code here is.
        I just copied and moved it from the old _update_available_quantity
        so it doesn't override the basic code. """
        move_id = self.env.context.get('move_id', False)
        if move_id:
            vals['move_id'] = move_id
        quants = super(StockQuant, self).create(vals)
        if move_id:
            move = self.env['stock.move'].browse(move_id)
            move.package_quant_ids = [(4, quant.id) for quant in quants]
        return quants

    @api.model
    def _update_reserved_quantity_life(self, product_id, location_id, quantity, lot_id=None, package_id=None, owner_id=None, strict=False, boss=None, scheduled_date=None):
        self = self.sudo()
        rounding = product_id.uom_id.rounding
        quants = self.env['stock.quant'].search([('product_id', '=', product_id.id), (
            'location_id', '=', location_id.id)], order='id,lot_id,expire_date ASC')
        reserved_quants = []

        if float_compare(quantity, 0, precision_rounding=rounding) > 0:
            # if we want to reserve
            available_quantity = sum(quants.filtered(lambda q: float_compare(
                q.quantity, 0, precision_rounding=rounding) > 0).mapped('quantity')) - sum(quants.mapped('reserved_quantity'))
            if float_compare(quantity, available_quantity, precision_rounding=rounding) > 0:
                raise UserError(
                    _('It is not possible to reserve more products of %s than you have in stock.', product_id.display_name))
        elif float_compare(quantity, 0, precision_rounding=rounding) < 0:
            # if we want to unreserve
            available_quantity = sum(quants.mapped('reserved_quantity'))
            if float_compare(abs(quantity), available_quantity, precision_rounding=rounding) > 0:
                raise UserError(
                    _('It is not possible to unreserve more products of %s than you have in stock.', product_id.display_name))
        else:
            return reserved_quants

        quant_higher = []
        quant_lower = []
        domain = ['&', '|', ('is_customer', '=', boss.id),
                  ('category_ids', '=', product_id.categ_id.id),
                  ('product_ids', '=',  product_id.id)]
        stock_life = self.env['stock.life'].search(domain)
        date_prior = scheduled_date + \
            relativedelta(days=stock_life.minimum_days)
        for rec in quants:
            if rec.expire_date:
                if rec.expire_date >= date_prior:
                    quant_higher.append(rec)
                    quant_higher.sort(key=lambda x: (
                        x.id, x.lot_id, x.expire_date))
                else:
                    quant_lower.append(rec)
                    quant_lower.sort(key=lambda x: (
                        x.id, x.lot_id, x.expire_date))
            else:
                quant_higher.append(rec)

        if stock_life.restrict_product:
            quants = quant_higher
        else:
            quants = quant_higher + quant_lower

        for quant in quants:
            if float_compare(quantity, 0, precision_rounding=rounding) > 0:
                max_quantity_on_quant = quant.quantity - quant.reserved_quantity
                if float_compare(max_quantity_on_quant, 0, precision_rounding=rounding) <= 0:
                    continue
                max_quantity_on_quant = min(max_quantity_on_quant, quantity)
                quant.reserved_quantity += max_quantity_on_quant
                reserved_quants.append((quant, max_quantity_on_quant))
                quantity -= max_quantity_on_quant
                available_quantity -= max_quantity_on_quant
            else:
                max_quantity_on_quant = min(
                    quant.reserved_quantity, abs(quantity))
                quant.reserved_quantity -= max_quantity_on_quant
                reserved_quants.append((quant, -max_quantity_on_quant))
                quantity += max_quantity_on_quant
                available_quantity += max_quantity_on_quant

            if float_is_zero(quantity, precision_rounding=rounding) or float_is_zero(available_quantity, precision_rounding=rounding):
                break
        return reserved_quants

    def _compute_forecast_incoming(self):
        for record in self:
            record = record.sudo()
            stock_move_ids = self.env['stock.move'].search([('product_id', '=', record.product_id.id),
                                                            ('picking_type_code',
                                                             '=', 'incoming'),
                                                            '|',
                                                            ('location_id', '=',
                                                             record.location_id.id),
                                                            ('location_dest_id', '=',
                                                             record.location_id.id),
                                                            ])
            qty = stock_move_ids.mapped('quantity_done')
            record.forecast_incoming = sum(qty)

            stock_move_ids = self.env['stock.move'].search([('product_id', '=', record.product_id.id),
                                                            ('picking_type_code',
                                                             '=', 'outgoing'),
                                                            '|',
                                                            ('location_id', '=',
                                                             record.location_id.id),
                                                            ('location_dest_id', '=',
                                                             record.location_id.id),
                                                            ])
            qty = stock_move_ids.mapped('quantity_done')
            record.forecast_outgoing = sum(qty)

            record.forecast_qty = record.quantity + \
                (record.forecast_incoming - record.forecast_outgoing)

    def make_update_available_quantity(self):

        """ [FIX] stock: filter quants when updating qty
        See: https://github.com/odoo/odoo/commit/802572ec0583be36e9532cdc8103d07709dcc11d """

        @api.model
        def _update_available_quantity(self, product_id, location_id, quantity, lot_id=None, package_id=None, owner_id=None, in_date=None):
            """ Increase or decrease `reserved_quantity` of a set of quants for a given set of
            product_id/location_id/lot_id/package_id/owner_id.

            :param product_id:
            :param location_id:
            :param quantity:
            :param lot_id:
            :param package_id:
            :param owner_id:
            :param datetime in_date: Should only be passed when calls to this method are done in
                                    order to move a quant. When creating a tracked quant, the
                                    current datetime will be used.
            :return: tuple (available_quantity, in_date as a datetime)
            """
            self = self.sudo()
            quants = self._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=True)
            if lot_id and quantity > 0:
                quants = quants.filtered(lambda q: q.lot_id)

            if location_id.should_bypass_reservation():
                incoming_dates = []
            else:
                incoming_dates = [quant.in_date for quant in quants if quant.in_date and
                                float_compare(quant.quantity, 0, precision_rounding=quant.product_uom_id.rounding) > 0]
            if in_date:
                incoming_dates += [in_date]
            # If multiple incoming dates are available for a given lot_id/package_id/owner_id, we
            # consider only the oldest one as being relevant.
            if incoming_dates:
                in_date = fields.Datetime.to_string(min(incoming_dates))
            else:
                in_date = fields.Datetime.now()

            for quant in quants:
                try:
                    with self._cr.savepoint(flush=False):  # Avoid flush compute store of package
                        self._cr.execute("SELECT 1 FROM stock_quant WHERE id = %s FOR UPDATE NOWAIT", [quant.id], log_exceptions=False)
                        quant.write({
                            'quantity': quant.quantity + quantity,
                            'in_date': in_date,
                        })
                        break
                except OperationalError as e:
                    if e.pgcode == '55P03':  # could not obtain the lock
                        continue
                    else:
                        # Because savepoint doesn't flush, we need to invalidate the cache
                        # when there is a error raise from the write (other than lock-error)
                        self.clear_caches()
                        raise
            else:
                self.create({
                    'product_id': product_id.id,
                    'location_id': location_id.id,
                    'quantity': quantity,
                    'lot_id': lot_id and lot_id.id,
                    'package_id': package_id and package_id.id,
                    'owner_id': owner_id and owner_id.id,
                    'in_date': in_date,
                })
            return self._get_available_quantity(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=False, allow_negative=True), fields.Datetime.from_string(in_date)
        return _update_available_quantity

    @api.model
    def _get_quants_action(self, domain=None, extend=False):
        res = super(StockQuant, self)._get_quants_action(
            domain=domain, extend=extend)
        res.update({
            'name': 'Inventory Report',
            # 'context': {'group_by': 'warehouse_id', 'search_default_on_hand': True},
        })
        if self._is_inventory_mode():
            form_view = self.env.ref('stock.view_stock_quant_form_editable').id
        else:
            form_view = self.env.ref('stock.view_stock_quant_form').id
        if extend:
            res.update({
                'views': [(self.env.ref('stock.view_stock_quant_pivot').id, 'pivot'),
                          (self.env.ref('stock.view_stock_quant_tree').id, 'list'),
                          (form_view, 'form'),
                          (self.env.ref('stock.stock_quant_view_graph').id, 'graph'),],
            }),
        return res

    def _register_hook(self):
        BasicStockQuant._patch_method('_update_available_quantity', self.make_update_available_quantity())
        return super(StockQuant, self)._register_hook()


    @api.model
    def _get_available_lots(self, location_id, product_id):
        """ Get available lots for given location and product. """
        if not location_id or not product_id:
            return []

        quants = self.search([
            ('location_id', '=', location_id),
            ('product_id', '=', product_id),
            ('lot_id', '!=', False),
            ('company_id', '=', self.env.company.id),
        ])
        
        # available_lots = quants.filtered(lambda q: q.available_quantity > 0).mapped('lot_id')
        available_lots = quants.filtered(lambda q: q.available_quantity > 0)
        return available_lots