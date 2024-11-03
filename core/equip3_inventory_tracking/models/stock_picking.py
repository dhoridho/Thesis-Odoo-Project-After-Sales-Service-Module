
from odoo import _, api, fields, models
from datetime import datetime, date, timedelta
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_expired_tranfer = fields.Boolean(
        string="Expired Transfer", default=False, compute='_compute_expired', search='_search_expired')
    is__expired_tranfer = fields.Boolean(
        string="Expired Transfer", default=False)

    def _search_expired(self, operator, value):
        self._cr.execute(
            'SELECT sp.id FROM stock_picking sp LEFT JOIN stock_move sm ON (sm.picking_id = sp.id) WHERE sm.exp_date <= Now() GROUP BY sp.id')
        ids = [r[0] for r in self._cr.fetchall()]
        if (operator == '=' and value is True) or (operator == '!=' and value is False):
            return [('id', 'in', ids)]
        return [('id', 'not in', ids)]

    @api.depends('move_ids_without_package', 'move_ids_without_package.exp_date')
    def _compute_expired(self):
        now = datetime.now()
        for rec in self:
            is_expired_tranfer = any(
                line.exp_date < now for line in rec.move_ids_without_package if line.exp_date)
            rec.is_expired_tranfer = is_expired_tranfer
            rec.is__expired_tranfer = is_expired_tranfer

    def _action_done(self):
        res = super(StockPicking, self)._action_done()
        for rec in self:
            if rec.state != "done":
                continue
            for move in rec.move_ids_without_package.filtered(lambda m: m.package_type and m.package_type.packages_barcode_prefix and m.package_type.current_sequence):
                digit = move.package_type.digits
                current_seq = move.package_type.packages_barcode_prefix + \
                    move.package_type.current_sequence
                new_seq = int(move.package_type.current_sequence) + 1
                move.package_type.current_sequence = str(new_seq).zfill(digit)
                move.move_line_nosuggest_ids.mapped('result_package_id').write(
                    {'barcode_packaging': current_seq})
        return res

    @api.onchange('sh_stock_barcode_mobile')
    def _onchange_sh_stock_barcode_mobile(self):
        if self.sh_stock_barcode_mobile in ['', "", False, None]:
            return
        CODE_SOUND_SUCCESS = ""
        CODE_SOUND_FAIL = ""
        if self.env.user.company_id.sudo().sh_stock_bm_is_sound_on_success:
            CODE_SOUND_SUCCESS = "SH_BARCODE_MOBILE_SUCCESS_"

        if self.env.user.company_id.sudo().sh_stock_bm_is_sound_on_fail:
            CODE_SOUND_FAIL = "SH_BARCODE_MOBILE_FAIL_"

        if not self.picking_type_id:
            if self.env.user.company_id.sudo().sh_stock_bm_is_notify_on_fail:
                message = _(CODE_SOUND_FAIL +
                            'You must first select a Operation Type.')
                self.env['bus.bus'].sendone(
                    (self._cr.dbname, 'res.partner', self.env.user.partner_id.id),
                    {'type': 'simple_notification', 'title': _('Failed'), 'message': message, 'sticky': False, 'warning': True})
            return

        if self and self.state not in ['assigned', 'draft', 'confirmed']:
            selections = self.fields_get()['state']['selection']
            value = next((v[1] for v in selections if v[0]
                          == self.state), self.state)
            if self.env.user.company_id.sudo().sh_stock_bm_is_notify_on_fail:
                message = _(CODE_SOUND_FAIL +
                            'You can not scan item in %s state.') % (value)
                self.env['bus.bus'].sendone(
                    (self._cr.dbname, 'res.partner', self.env.user.partner_id.id),
                    {'type': 'simple_notification', 'title': _('Failed'), 'message': message, 'sticky': False, 'warning': True})
            return
        elif self:
            search_mls = False
            search_barcode = False
            domain = []
            stock_picking_domain = []
            quant_package_id = self.env["stock.quant.package"].search(
                [("barcode_packaging", "=", self.sh_stock_barcode_mobile)], limit=1)
            if quant_package_id:
                move_package_lines = self.move_ids_without_package.filtered(lambda r: r.product_id.id in quant_package_id.quant_ids.mapped(
                    'product_id').ids and r.package_barcode == self.sh_stock_barcode_mobile)
                if move_package_lines:
                    raise ValidationError(
                        _("The Entire Product within the package has been shipped to other location."))
                remaning_products = False
                for line in quant_package_id.quant_ids:
                    move_lines = self.move_ids_without_package.filtered(
                        lambda r: r.product_id.id == line.product_id.id)
                    if move_lines:
                        for move_line in move_lines:
                            if move_line.package_barcode == quant_package_id.barcode_packaging:
                                qty_done = move_line.quantity_done + line.quantity
                                move_line.quantity_done = qty_done
                        if self.env.user.company_id.sudo().sh_stock_bm_is_notify_on_success:
                            self.sh_stock_barcode_mobile = ''
                            message = _(CODE_SOUND_SUCCESS + 'Product: %s Qty: %s') % (
                                move_line.product_id.name, move_line.quantity_done)
                            self.env['bus.bus'].sendone(
                                (self._cr.dbname, 'res.partner',
                                 self.env.user.partner_id.id),
                                {'type': 'simple_notification', 'title': _('Succeed'), 'message': message, 'sticky': False, 'warning': False})
                    else:
                        remaning_products = True
                if remaning_products and self.state in ['assigned', 'draft', 'confirmed']:
                    if self.env.user.company_id.sudo().sh_stock_bm_is_add_product:
                        data = []
                        for line in quant_package_id.quant_ids:
                            quantity = line.quantity
                            existing_move_package_lines = self.env['stock.move'].search(
                                [('package_barcode', '=', self.sh_stock_barcode_mobile), ('product_id', '=', line.product_id.id)])
                            if existing_move_package_lines:
                                existing_qty = sum(
                                    existing_move_package_lines.mapped('quantity_done'))
                                quantity -= existing_qty
                            if quantity > 0:
                                stock_move_vals = {
                                    "name": line.product_id.name,
                                    "product_id": line.product_id.id,
                                    "quantity_done": quantity,
                                    'package_barcode': quant_package_id.barcode_packaging,
                                    "product_uom": line.product_uom_id.id
                                }
                                data.append((0, 0, stock_move_vals))
                        self.move_ids_without_package = data
                        if self.env.user.company_id.sudo().sh_stock_bm_is_notify_on_success:
                            self.sh_stock_barcode_mobile = ''
                            message = _(CODE_SOUND_SUCCESS + 'Product: %s Qty: %s') % (
                                line.product_id.name, 1)
                            self.env['bus.bus'].sendone(
                                (self._cr.dbname, 'res.partner',
                                 self.env.user.partner_id.id),
                                {'type': 'simple_notification', 'title': _('Succeed'), 'message': message, 'sticky': False, 'warning': False})
                            return
                        else:
                            if self.env.user.company_id.sudo().sh_stock_bm_is_notify_on_fail:
                                message = _(
                                    CODE_SOUND_FAIL + 'Scanned Internal Reference/Barcode not exist in any product!')
                                self.env['bus.bus'].sendone(
                                    (self._cr.dbname, 'res.partner',
                                     self.env.user.partner_id.id),
                                    {'type': 'simple_notification', 'title': _('Failed'), 'message': message, 'sticky': False, 'warning': True})
                            return
                    else:
                        if self.env.user.company_id.sudo().sh_stock_bm_is_notify_on_fail:
                            message = _(
                                CODE_SOUND_FAIL + 'Scanned Internal Reference/Barcode not exist in any product!')
                            self.env['bus.bus'].sendone(
                                (self._cr.dbname, 'res.partner',
                                 self.env.user.partner_id.id),
                                {'type': 'simple_notification', 'title': _('Failed'), 'message': message, 'sticky': False, 'warning': True})
                        return
            else:
                return super()._onchange_sh_stock_barcode_mobile()
        else:
            # failed message here
            if self.env.user.company_id.sudo().sh_stock_bm_is_notify_on_fail:
                message = _(
                    CODE_SOUND_FAIL + 'Scanned Internal Reference/Barcode not exist in any product!')
                self.env['bus.bus'].sendone(
                    (self._cr.dbname, 'res.partner', self.env.user.partner_id.id),
                    {'type': 'simple_notification', 'title': _('Failed'), 'message': message, 'sticky': False, 'warning': True})

            return
