from odoo import _, api, fields, models
from datetime import datetime, date


class CanselSupplier(models.TransientModel):
    _inherit = 'cancel.supplier.memory'
    
    supplier_ids = fields.Many2many('product.supplierinfo', 'cancel_supplier_rel', 'cancel_id', 'supplier_id', 'Source')
    
    def action_cancel_supplier(self):
        context = self.env.context or {}
        if context.get('is_mass_reject'):
            for product_supplierinfo_id in self.supplier_ids.filtered(lambda r:r.state == 'waiting_approval'):
                user = self.env.user
                param = self.env['ir.config_parameter'].sudo()
                is_vendor_pricelist_approval_email = param.get_param('equip3_purchase_masterdata.is_vendor_pricelist_approval_email')
                is_vendor_pricelist_approval_whatsapp = param.get_param('equip3_purchase_masterdata.is_vendor_pricelist_approval_whatsapp')
                approving_matrix_line = sorted(product_supplierinfo_id.approval_ids.filtered(lambda r:not r.approved), key=lambda r:r.sequence)
                action_id = self.env.ref('product.product_supplierinfo_type_action')
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                url = base_url + '/web#id=' + str(product_supplierinfo_id.id) + '&action='+ str(action_id.id) + '&view_type=form&model=product.supplierinfo'
                rejected_template_id = self.env.ref('equip3_purchase_masterdata.email_template_vendor_pricelist_approval_rejected')
                wa_rejected_template_id = self.env.ref('equip3_purchase_masterdata.whatsapp_vendor_pricelist_template_rejected')
                if approving_matrix_line:
                    matrix_line = approving_matrix_line[0]
                    name = matrix_line.status or ''
                    if name != '':
                        name += "\n • %s: Rejected" % (user.name)
                    else:
                        name += "• %s: Rejected" % (user.name)
                    matrix_line.write({'status': name, 'time_stamp': datetime.now(), 'feedback': self.reason})
                    ctx = {
                        'email_from' : self.env.user.company_id.email,
                        'email_to' : product_supplierinfo_id.request_partner_id.email,
                        'date': date.today(),
                        'url' : url,
                    }
                    if is_vendor_pricelist_approval_email:
                        rejected_template_id.sudo().with_context(ctx).send_mail(product_supplierinfo_id.id, True)
                    if is_vendor_pricelist_approval_whatsapp:
                        phone_num = str(product_supplierinfo_id.request_partner_id.mobile) or str(product_supplierinfo_id.request_partner_id.phone)
                        product_supplierinfo_id._send_qiscus_whatsapp_approval(wa_rejected_template_id,
                                                                                product_supplierinfo_id.request_partner_id,
                                                                                phone_num, url)
                product_supplierinfo_id.write({'state' : 'rejected'})
        else:
            return super(CanselSupplier, self).action_cancel_supplier()
        
    