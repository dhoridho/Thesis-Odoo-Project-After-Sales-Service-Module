# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import uuid


class ShSendWhatsappMessage(models.TransientModel):
    _inherit = "sh.base.send.whatsapp.message.wizard"

    purchase_order_id = fields.Many2one(
        'purchase.order', string="Purchase Order")

    def action_send_whatsapp_message(self):
        res = super(ShSendWhatsappMessage,
                    self).action_send_whatsapp_message()
        for rec in self:
            for partner in rec.partner_ids:
                active_ids = self.env.context.get('active_ids')
                active_id = int(active_ids[0])
                sh_message = ""
                if rec.message:
                    sh_message = str(self.message).replace(
                        '*', '').replace('_', '').replace('%0A', '<br/>').replace('%20', ' ').replace('%26', '&')

                if rec.purchase_order_id and rec.purchase_order_id.company_id.purchase_display_in_message:
                    self.env['mail.message'].create({
                    'partner_ids': [(6, 0, partner.ids)],
                    'model': 'purchase.order',
                    'res_id': active_id,
                    'author_id': self.env.user.partner_id.id,
                    'body': sh_message or False,
                    'message_type': 'comment',
                    })
                if partner.mobile:
                    return {
                        'type': 'ir.actions.act_url',
                        'url': "https://web.whatsapp.com/send?l=&phone="+partner.mobile+"&text=" + rec.message.replace('&', '%26'),
                        'target': 'new',
                        'res_id': rec.id,
                    }


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    purchase_url = fields.Text("Url")

    def action_quotation_send_wp(self):

        if not self.partner_id.mobile:
            raise UserError(_("Vendor Mobile Number Not Exist !"))

        '''
        This function opens a window to compose an email, with the edi purchase template message loaded by default
        '''
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']

        template = self.env.ref(
            'sh_all_in_one_purchase_tools.email_template_edi_purchase_custom')
        try:
            compose_form_id = ir_model_data.get_object_reference(
                'mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict(self.env.context or {})

        ctx.update({
            'default_model': 'purchase.order',
            'active_model': 'purchase.order',
            'active_id': self.ids[0],
            'default_res_id': self.ids[0],
            'default_use_template': bool(template.id),
            'default_template_id': template.id,
            'default_composition_mode': 'comment',
            'custom_layout': "mail.mail_notification_paynow",
            'force_email': True,
            'mark_rfq_as_sent': True,
            'default_is_wp': True,
        })
        lang = self.env.context.get('lang')
        if {'default_template_id', 'default_model', 'default_res_id'} <= ctx.keys():
            template = self.env['mail.template'].browse(
                ctx['default_template_id'])
            if template and template.lang:
                lang = template._render_lang([ctx['default_res_id']])[
                    ctx['default_res_id']]

        self = self.with_context(lang=lang)
        if self.state in ['draft', 'sent']:
            ctx['model_description'] = _('Request for Quotation')
        else:
            ctx['model_description'] = _('Purchase Order')

        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    def _get_report_base_filename(self):
        self.ensure_one()
        return '%s' % (self.name)

    report_token = fields.Char("Access Token")

    def _get_token(self):
        """ Get the current record access token """
        if self.report_token:
            return self.report_token
        else:
            report_token = str(uuid.uuid4())
            self.write({'report_token': report_token})
            return report_token

    def get_download_report_url(self):
        url = ''
        if self.id:
            self.ensure_one()
            url = '/download/po/' + '%s?access_token=%s' % (
                self.id,
                self._get_token()
            )
        return url

    text_message = fields.Text(
        "Message", compute="_compute_get_message_detail_po")

    @api.depends('partner_id', 'currency_id', 'company_id')
    def _compute_get_message_detail_po(self):
        if self:
            for rec in self:
                txt_message = ""
                if rec.company_id.purchase_order_information_in_message and rec.partner_id and rec.currency_id and rec.company_id:
                    txt_message += "Dear " + str(rec.partner_id.name)+","+"%0A%0A"+"Here is the order "+'*'+rec.name+'*'+" amounting in "+'*'+str(
                        rec.amount_total)+'*'+""+str(rec.currency_id.symbol)+" from "+rec.company_id.name+"%0A%0A"
                if rec.company_id.purchase_product_detail_in_message:
                    txt_message += "Following is your order details."+"%0A"
                    if rec.order_line:
                        for purchase_line in rec.order_line:
                            if purchase_line.product_id:
                                txt_message += "%0A"+"*"+purchase_line.product_id.display_name+"*"+"%0A"+"*Qty:* "+str(purchase_line.product_qty)+"%0A"+"*Price:* "+str(
                                    purchase_line.price_unit)+""+str(purchase_line.order_id.currency_id.symbol)+"%0A"+"________________________"+"%0A"
                        txt_message += "*"+"Total Amount:"+"*"+"%20" + \
                            str(rec.amount_total)+"" + \
                            str(rec.currency_id.symbol)
                if rec.company_id.po_send_pdf_in_message:
                    base_url = self.env['ir.config_parameter'].sudo(
                    ).get_param('web.base.url')
                    quot_url = "%0A%0A Click here to download Report : %0A" + \
                        base_url+rec.get_download_report_url()
                    self.write(
                        {'purchase_url': base_url+rec.get_download_report_url()})
                    txt_message += quot_url

                if rec.company_id.purchase_signature and rec.env.user.sign:
                    txt_message += "%0A%0A%0A"+str(rec.env.user.sign)
            rec.text_message = txt_message.replace('&', '%26')

    def send_by_whatsapp_direct_to_po(self):
        if self and self.company_id.purchase_display_in_message:
            message = ''
            if self.text_message:
                message = str(self.text_message).replace(
                    '*', '').replace('_', '').replace('%0A', '<br/>').replace('%20', ' ').replace('%26', '&')
            self.env['mail.message'].create({
                                            'partner_ids': [(6, 0, self.partner_id.ids)],
                                            'model': 'purchase.order',
                                            'res_id': self.id,
                                            'author_id': self.env.user.partner_id.id,
                                            'body': message or False,
                                            'message_type': 'comment',
                                            })
        if self.partner_id.mobile:
            return {
                'type': 'ir.actions.act_url',
                'url': "https://web.whatsapp.com/send?l=&phone="+self.partner_id.mobile+"&text=" + self.text_message,
                'target': 'new',
                'res_id': self.id,
            }
        else:
            raise UserError(_("Partner Mobile Number Not Exist"))
