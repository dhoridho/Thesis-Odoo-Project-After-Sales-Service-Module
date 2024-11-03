from odoo import models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _is_agri_lot_auto_generate(self):
        self.ensure_one()
        return self.tracking == 'lot' and self.is_in_autogenerate

    def _is_agri_serial_auto_generate(self):
        self.ensure_one()
        return self.tracking == 'serial' and self.is_sn_autogenerate

    def _is_agri_auto_generate(self):
        self.ensure_one()
        return self._is_agri_lot_auto_generate() or self._is_agri_serial_auto_generate()

    def _is_agri_manual_generate(self):
        self.ensure_one()
        return (self.tracking == 'serial' and not self.is_sn_autogenerate) or (self.tracking == 'lot' and not self.is_in_autogenerate)

    # it's just _prepare_out_svl_vals with value forced to 0.0
    def _prepare_out_svl_vals_agri_adjustment(self, quantity, company):
        """Prepare the values for a stock valuation layer created by a delivery.

        :param quantity: the quantity to value, expressed in `self.uom_id`
        :return: values to use in a call to create
        :rtype: dict
        """
        self.ensure_one()
        # Quantity is negative for out valuation layers.
        quantity = -1 * quantity
        vals = {
            'product_id': self.id,
            'value': 0,
            'unit_cost': 0,
            'quantity': quantity,
        }
        if self.cost_method in ('average', 'fifo'):
            fifo_vals = self._run_fifo(abs(quantity), company)
            vals['remaining_qty'] = fifo_vals.get('remaining_qty')
            # In case of AVCO, fix rounding issue of standard price when needed.
            if self.cost_method == 'average':
                currency = self.env.company.currency_id
                rounding_error = currency.round(self.standard_price * self.quantity_svl - self.value_svl)
                if rounding_error:
                    # If it is bigger than the (smallest number of the currency * quantity) / 2,
                    # then it isn't a rounding error but a stock valuation error, we shouldn't fix it under the hood ...
                    if abs(rounding_error) <= (abs(quantity) * currency.rounding) / 2:
                        vals['value'] += rounding_error
                        vals['rounding_adjustment'] = '\nRounding Adjustment: %s%s %s' % (
                            '+' if rounding_error > 0 else '',
                            float_repr(rounding_error, precision_digits=currency.decimal_places),
                            currency.symbol
                        )
            if self.cost_method == 'fifo':
                vals.update(fifo_vals)
        return vals