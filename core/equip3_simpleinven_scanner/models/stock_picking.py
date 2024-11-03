# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT


class Picking(models.Model):
    _inherit = "stock.picking"

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
            domain = []

            if self.env.user.company_id.sudo().sh_stock_barcode_mobile_type == 'barcode':
                search_mls = self.move_ids_without_package.filtered(
                    lambda ml: ml.product_id.barcode == self.sh_stock_barcode_mobile)
                domain = [("barcode", "=", self.sh_stock_barcode_mobile)]

            elif self.env.user.company_id.sudo().sh_stock_barcode_mobile_type == 'int_ref':
                search_mls = self.move_ids_without_package.filtered(
                    lambda ml: ml.product_id.default_code == self.sh_stock_barcode_mobile)
                domain = [("default_code", "=", self.sh_stock_barcode_mobile)]

            elif self.env.user.company_id.sudo().sh_stock_barcode_mobile_type == 'sh_qr_code':
                search_mls = self.move_ids_without_package.filtered(
                    lambda ml: ml.product_id.sh_qr_code == self.sh_stock_barcode_mobile)
                domain = [("sh_qr_code", "=", self.sh_stock_barcode_mobile)]

            elif self.env.user.company_id.sudo().sh_stock_barcode_mobile_type == 'all':
                search_mls = self.move_ids_without_package.filtered(
                    lambda ml: ml.product_id.barcode == self.sh_stock_barcode_mobile or ml.product_id.default_code == self.sh_stock_barcode_mobile)
                domain = ["|", "|",
                          ("default_code", "=", self.sh_stock_barcode_mobile),
                          ("barcode", "=", self.sh_stock_barcode_mobile),
                          ("sh_qr_code", "=", self.sh_stock_barcode_mobile),
                          ]
            if search_mls:
                for move_line in search_mls:
                    if move_line.show_details_visible:
                        if self.env.user.company_id.sudo().sh_stock_bm_is_notify_on_fail:
                            message = _(
                                CODE_SOUND_FAIL + 'You can not scan product item for Detailed Operations directly here, Pls click detail button (at end each line) and than rescan your product item.')
                            self.env['bus.bus'].sendone(
                                (self._cr.dbname, 'res.partner',
                                 self.env.user.partner_id.id),
                                {'type': 'simple_notification', 'title': _('Failed'), 'message': message, 'sticky': False, 'warning': True})
                        return
                    qty_done = move_line.quantity_done + 1
                    move_line.quantity_done = qty_done
                    if self.env.user.company_id.sudo().sh_stock_bm_is_notify_on_success:
                        self.sh_stock_barcode_mobile = ''
                        message = _(CODE_SOUND_SUCCESS + 'Product: %s Qty: %s') % (
                            move_line.product_id.name, move_line.quantity_done)
                        self.env['bus.bus'].sendone(
                            (self._cr.dbname, 'res.partner',
                             self.env.user.partner_id.id),
                            {'type': 'simple_notification', 'title': _('Succeed'), 'message': message, 'sticky': False, 'warning': False})
            elif self.state in ['assigned', 'draft', 'confirmed']:
                if self.env.user.company_id.sudo().sh_stock_bm_is_add_product:
                    search_product = self.env["product.product"].search(
                        domain, limit=1)
                    if search_product:
                        stock_move_vals = {
                            "name": search_product.name,
                            "product_id": search_product.id,
                            "price_unit": search_product.lst_price,
                            "quantity_done": 1,
                            "location_id": self.location_id.id,
                            "location_dest_id": self.location_dest_id.id
                        }
                        if search_product.uom_id:
                            stock_move_vals.update({
                                "product_uom": search_product.uom_id.id,
                            })

                        self.move_ids_without_package = [(0, 0, stock_move_vals)]
                        if self.env.user.company_id.sudo().sh_stock_bm_is_notify_on_success:
                            self.sh_stock_barcode_mobile = ''
                            message = _(CODE_SOUND_SUCCESS + 'Product: %s Qty: %s') % (
                                search_product.name, 1)
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
                if self.env.user.company_id.sudo().sh_stock_bm_is_notify_on_fail:
                    message = _(
                        CODE_SOUND_FAIL + 'Scanned Internal Reference/Barcode not exist in any product!')
                    self.env['bus.bus'].sendone(
                        (self._cr.dbname, 'res.partner',
                         self.env.user.partner_id.id),
                        {'type': 'simple_notification', 'title': _('Failed'), 'message': message, 'sticky': False, 'warning': True})

                return
        else:
            # failed message here
            if self.env.user.company_id.sudo().sh_stock_bm_is_notify_on_fail:
                message = _(
                    CODE_SOUND_FAIL + 'Scanned Internal Reference/Barcode not exist in any product!')
                self.env['bus.bus'].sendone(
                    (self._cr.dbname, 'res.partner', self.env.user.partner_id.id),
                    {'type': 'simple_notification', 'title': _('Failed'), 'message': message, 'sticky': False, 'warning': True})

            return
