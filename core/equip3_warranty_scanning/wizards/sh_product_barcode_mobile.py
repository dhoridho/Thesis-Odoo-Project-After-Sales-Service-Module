from odoo import api, fields, models, _

class ShProductBarcodeMobileWizardInherit(models.TransientModel):
    _inherit = 'sh.product.barcode.mobile.wizard'

    sh_warranty_qr = fields.Char(string='Serial Number')


    @api.onchange('sh_warranty_qr')
    def _onchange_warranty_qr(self):
        
        if self.sh_warranty_qr in ['', "", False, None]:
            return
        

        CODE_SOUND_SUCCESS = ""
        CODE_SOUND_FAIL = ""
        if self.env.user.company_id.sudo().sh_product_bm_is_sound_on_success:
            CODE_SOUND_SUCCESS = "SH_BARCODE_MOBILE_SUCCESS_"

        if self.env.user.company_id.sudo().sh_product_bm_is_sound_on_fail:
            CODE_SOUND_FAIL = "SH_BARCODE_MOBILE_FAIL_"

        if self and self.sh_warranty_qr:

            search_lot = self.env["stock.production.lot"].search([('name','=',self.sh_warranty_qr)], limit=1)
            search_product = self.env["product.warranty"].search([('product_serial_id','=',search_lot.id)], limit=1)
            if search_product:
                if search_product.state == 'new':
                    state = 'New'
                elif search_product.state == 'in_progress':
                    state = 'Under Warranty'
                elif search_product.state == 'invoiced':
                    state = 'Invoiced'
                elif search_product.state == 'to_renew':
                    state = 'To Renew'
                elif search_product.state == 'expired':
                    state = 'Expired'
                else:
                    state = False


                msg = '''<div><h4>
                <img src="/web/image/product.product/%(product_id)s/image_1920" style="width: 250px; height: 250px;" align="right"/>
                Product: <font color="red">%(product)s </font>
                <br/><br/>
                Serial Number: <font color="red">%(serial)s </font>
                <br/><br/>
                Product Category: <font color="red">%(product_category)s </font>
                <br/><br/>
                Warranty Start Date: <font color="red">%(start_date)s </font>
                <br/><br/>
                Warranty End Date: <font color="red">%(end_date)s </font>
                <br/><br/>
                Remaining Warranty Days: <font color="red">%(remaining_days)s </font>
                <br/><br/>
                Sale Order Number: <font color="red">%(sale_order)s </font>
                <br/><br/>
                Delivery Order Number: <font color="red">%(delivery_order)s </font>
                <br/><br/>
                Status: <font color="red">%(status)s </font>
                </h4></div>
                ''' % {
                    'product_id': search_product.product_id.id,
                    'product': search_product.product_id.name,
                    'serial': search_product.product_serial_id.name,
                    'product_category': search_product.product_id.categ_id.name,
                    'start_date': search_product.warranty_create_date,
                    'end_date': search_product.warranty_end_date,
                    'remaining_days': search_product.remaining_warranty_days,
                    'delivery_order': search_product.picking_id.name,
                    'sale_order': search_product.picking_id.origin,
                    'status': state,
                }

                self.post_msg = msg

                if self.env.user.company_id.sudo().sh_product_bm_is_notify_on_success:
                    message = _(CODE_SOUND_SUCCESS +
                                'Product: %s') % (search_product.product_id.name)
                    self.env['bus.bus'].sendone(
                        (self._cr.dbname, 'res.partner',
                         self.env.user.partner_id.id),
                        {'type': 'simple_notification', 'title': _('Succeed'), 'message': message, 'sticky': False, 'warning': False})

            else:
                self.post_msg = False
                if self.env.user.company_id.sudo().sh_product_bm_is_notify_on_fail:
                    message = _(
                        CODE_SOUND_FAIL + 'Scanned QR Code not exist in any product!')
                    self.env['bus.bus'].sendone(
                        (self._cr.dbname, 'res.partner',
                         self.env.user.partner_id.id),
                        {'type': 'simple_notification', 'title': _('Failed'), 'message': message, 'sticky': False, 'warning': True})
