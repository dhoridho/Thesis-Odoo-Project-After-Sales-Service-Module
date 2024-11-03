# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from datetime import datetime, date


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    available_quantity_stored = fields.Float(
        'Available Quantity Stored',
        help="On hand quantity which hasn't been reserved on a transfer, in the default unit of measure of the product",
        compute='_compute_available_quantity_stored', store=True)

    @api.depends('quantity', 'reserved_quantity')
    def _compute_available_quantity(self):
        for quant in self:
            quant.available_quantity = quant.quantity - quant.reserved_quantity

    @api.depends('available_quantity')
    def _compute_available_quantity_stored(self):
        for quant in self:
            quant.available_quantity_stored = quant.available_quantity

    def unlink(self):
        ids_to_delete = ','.join(str(i) for i in self.ids)
        res = super().unlink()
        if ids_to_delete:
            query = '''
                SELECT 
                  ru.id AS user_id,
                  COALESCE(ru.stock_quant_unlink_data, '') AS stock_quant_unlink_data
                FROM
                  res_users as ru
                WHERE 
                  ru.active != FALSE	AND ru.share = FALSE
                ORDER BY 
                  user_id asc
            '''
            self.env.cr.execute(query)
            users_data = self.env.cr.dictfetchall()
            for record in users_data:
                user_id = record.get('user_id')
                old_value = record.get('stock_quant_unlink_data')
                if old_value:
                    new_value = old_value + ',' + ids_to_delete
                else:
                    new_value = ids_to_delete
                self._cr.execute("""UPDATE res_users SET stock_quant_unlink_data =%s WHERE id =%s""", (new_value, user_id))
                self._cr.commit()
        return res

    def get_stock_quant_data(self):
        query = '''
            SELECT
                sq.id as quant_id,
                COALESCE(sq.product_id, 0) AS product_id,
                COALESCE(sq.lot_id, 0) AS lot_id,
                COALESCE(spl.name, '') AS lot_name,
                COALESCE(sl.id, 0) AS location_id,
    			COALESCE(sl.complete_name, '') AS location_name,
    			COALESCE(sq.available_quantity_stored, 0.0) AS available_quantity
            FROM
                stock_quant as sq
                LEFT JOIN stock_production_lot spl ON (sq.lot_id = spl.id)
                LEFT JOIN stock_location sl ON (sq.location_id = sl.id)
            WHERE sq.lot_id != 0
            ORDER BY sq.id DESC
            '''
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        self.env.user.stock_quant_date = datetime.now()
        return result

    def get_dynamic_stock_quant_data(self):
        sq_datetime = self.env.user.stock_quant_date or datetime.now()
        query = '''
            SELECT
                sq.id as quant_id,
                COALESCE(sq.product_id, 0) AS product_id,
                COALESCE(sq.lot_id, 0) AS lot_id,
                COALESCE(spl.name, '') AS lot_name,
                COALESCE(sl.id, 0) AS location_id,
    			COALESCE(sl.complete_name, '') AS location_name,
    			COALESCE(sq.available_quantity_stored, 0.0) AS available_quantity
            FROM
                stock_quant as sq
                LEFT JOIN stock_production_lot spl ON (sq.lot_id = spl.id)
                LEFT JOIN stock_location sl ON (sq.location_id = sl.id)
            WHERE sq.lot_id != 0 AND sq.write_date >= '%s' OR sq.create_date >= '%s'
            ORDER BY sq.id DESC
            ''' % (sq_datetime,sq_datetime)
        self.env.cr.execute(query)
        result = self.env.cr.dictfetchall()
        if result:
            self.env.user.stock_quant_date = datetime.now()
        return result

    @api.model
    def _update_reserved_quantity(self, product_id, location_id, quantity, lot_id=None, package_id=None, owner_id=None, strict=False):
        if not self.env.context.get('process_from_app'):
            return super()._update_reserved_quantity(product_id, location_id, quantity, lot_id, package_id, owner_id, strict)
        """ Increase the reserved quantity, i.e. increase `reserved_quantity` for the set of quants
        sharing the combination of `product_id, location_id` if `strict` is set to False or sharing
        the *exact same characteristics* otherwise. Typically, this method is called when reserving
        a move or updating a reserved move line. When reserving a chained move, the strict flag
        should be enabled (to reserve exactly what was brought). When the move is MTS,it could take
        anything from the stock, so we disable the flag. When editing a move line, we naturally
        enable the flag, to reflect the reservation according to the edition.

        :return: a list of tuples (quant, quantity_reserved) showing on which quant the reservation
            was done and how much the system was able to reserve on it
        """
        self = self.sudo()
        rounding = product_id.uom_id.rounding
        quants = self._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id, strict=strict)
        reserved_quants = []

        if float_compare(quantity, 0, precision_rounding=rounding) > 0:
            # if we want to reserve
            available_quantity = sum(quants.filtered(lambda q: float_compare(q.quantity, 0, precision_rounding=rounding) > 0).mapped('quantity')) - sum(quants.mapped('reserved_quantity'))
            if float_compare(quantity, available_quantity, precision_rounding=rounding) > 0:
                if not self.env.context.get('process_from_app'):
                    raise UserError(_('It is not possible to reserve more products of %s than you have in stock.', product_id.display_name))
        elif float_compare(quantity, 0, precision_rounding=rounding) < 0:
            # if we want to unreserve
            available_quantity = sum(quants.mapped('reserved_quantity'))
            if float_compare(abs(quantity), available_quantity, precision_rounding=rounding) > 0:
                if not self.env.context.get('process_from_app'):
                    raise UserError(_('It is not possible to unreserve more products of %s than you have in stock.', product_id.display_name))
        else:
            return reserved_quants

        for quant in quants:
            if float_compare(quantity, 0, precision_rounding=rounding) > 0:
                max_quantity_on_quant = quant.quantity - quant.reserved_quantity
                if not self.env.context.get('process_from_app'):
                    if float_compare(max_quantity_on_quant, 0, precision_rounding=rounding) <= 0:
                        continue
                max_quantity_on_quant = min(max_quantity_on_quant, quantity)
                quant.reserved_quantity += max_quantity_on_quant
                reserved_quants.append((quant, max_quantity_on_quant))
                quantity -= max_quantity_on_quant
                available_quantity -= max_quantity_on_quant
            else:
                max_quantity_on_quant = min(quant.reserved_quantity, abs(quantity))
                quant.reserved_quantity -= max_quantity_on_quant
                reserved_quants.append((quant, -max_quantity_on_quant))
                quantity += max_quantity_on_quant
                available_quantity += max_quantity_on_quant
            if float_is_zero(quantity, precision_rounding=rounding) or float_is_zero(available_quantity, precision_rounding=rounding):
                break
        return reserved_quants