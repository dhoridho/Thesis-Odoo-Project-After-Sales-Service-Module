from odoo import models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def create_next_lot_and_serial(self, product_qty, expiration_date=False, force_company=False):
        self.ensure_one()

        context = self.env.context.copy()
        if 'default_product_uom_id' in context:
            del context['default_product_uom_id']
        context['force_blank_expiration_date'] = True

        stock_production_lot = self.env['stock.production.lot'].with_context(context)
        company_id = force_company or self.company_id.id or self.env.company.id

        values = {
            'product_id': self.id,
            'company_id': company_id,
            'consumption_qty': product_qty,
            'mrp_consumption_expiration_date': expiration_date
        }

        if not self._is_serial_auto_generate() and not self._is_lot_auto_generate():
            values.update({'name': self.env['ir.sequence'].next_by_code('stock.lot.serial')})
            return stock_production_lot.create(values)

        if self.tracking == 'serial':
            digits = self.digits
            seq_to_update = 'current_sequence'
            current_seq = int(float(self.current_sequence))
        else:
            digits = self.in_digits
            seq_to_update = 'in_current_sequence'
            current_seq = int(float(self.in_current_sequence))

        consumption = self.env['mrp.consumption']
        while True:
            auto_sequence = self.product_tmpl_id._get_next_lot_and_serial(current_sequence=current_seq)
            lot_id = stock_production_lot.search([('name', '=', auto_sequence)])
            if not lot_id:
                break
            current_seq += 1

        if not lot_id:
            values.update({'name': auto_sequence})
            lot_id = stock_production_lot.create(values)

        # update for next sequence
        self.write({seq_to_update: str(current_seq + 1).zfill(digits)})

        return lot_id

    # These methods inherited in equip3_manuf_inventory
    def _is_lot_auto_generate(self):
        self.ensure_one()
        return False

    def _is_serial_auto_generate(self):
        self.ensure_one()
        return False

    def _is_auto_generate(self):
        self.ensure_one()
        return self._is_lot_auto_generate() or self._is_serial_auto_generate()

    def _is_manual_generate(self):
        self.ensure_one()
        return self.tracking in ('serial', 'lot')
