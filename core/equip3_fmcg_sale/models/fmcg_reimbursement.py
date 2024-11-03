from odoo import models,fields,api,_
from dateutil.relativedelta import relativedelta
from datetime import date, datetime, timedelta
from odoo.exceptions import UserError, ValidationError
from odoo import tools
import base64

class CustomerTarget(models.Model):
    _inherit = 'customer.target'

    def name_get(self):
        res = super().name_get()
        res = []
        for record in self:
            name = record.name
            if record.res_name:
                name = name + " - " + record.res_name
            res.append((record.id, name))
        return res

class FmcgReimbursement(models.Model):
    _name = 'fmcg.reimbursement'

    name = fields.Char(string='Number', default='New', copy=False, readonly=True)
    vendor_id = fields.Many2one('res.partner', string="Vendor", domain="[('is_vendor','=',True)]", required=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    created_by = fields.Many2one('res.users',default=lambda self:self.env.user)
    creation_date = fields.Datetime(string='Creation Date', default=datetime.today())
    customer_reward_ids = fields.One2many('customer.reward.line', 'reimbursement_id', string="Customer Reward")
    state = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
    ], string='Status', required=True, readonly=True, copy=False,
        default='draft')
    order_line_ids = fields.One2many('reimbursement.order.line', 'reimbursement_id', string="Order Line")
    total_amount = fields.Float("Total", compute='_compute_total_amount_and_voucher', store=True)
    invoice_count = fields.Integer(compute="_compute_invoice", string='Bill Count', copy=False, default=0)
    invoice_ids = fields.One2many('account.move', 'reimbursement_id', string='Invoices')
    cust_target_id = fields.Many2one('customer.target', string="Customer Target", required=True)
    partner_id = fields.Many2one('res.partner', related='vendor_id', store=True)

    def _compute_invoice(self):
        for rec in self:
            rec.invoice_count = len(rec.invoice_ids)

    def action_view_invoices(self):
        action = {
            'name': _('Invoices'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'target': 'current',
            'domain': [('id','in',self.invoice_ids.ids)]
        }
        return action

    @api.depends('customer_reward_ids.voucher_id')
    def _compute_total_amount_and_voucher(self):
        for rec in self:
            amount = 0
            voucher_ids = []
            if rec.customer_reward_ids:
                for line in rec.customer_reward_ids:
                    if line.voucher_id.id not in voucher_ids:
                        voucher_ids.append(line.voucher_id.id)
                    else:
                        raise ValidationError("Voucher has been selected!")
                    amount += line.reward_amount
            rec.write({
                'total_amount': amount,
            })

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        res.update({
            'order_line_ids': [
                (0,0, {
                    'sequence': 1,
                    'product_template_id': self.env.ref('equip3_fmcg_sale.product_claim_promo').id,
                    'product_uom_qty': 1,
                    'price_unit': 0,
                    'price_total': 0
                })]
        })
        return res

    @api.model_create_multi
    def create(self, vals):
        vals[0]['name'] = self.env['ir.sequence'].next_by_code('seq.fmcg.claim.to.principle')
        res = super().create(vals)
        return res

    def action_confirm(self):
        for rec in self:
            if rec.customer_reward_ids:
                for line in rec.customer_reward_ids:
                    if line.voucher_id:
                        line.voucher_id.write({
                            'is_claimed': True
                        })
            rec.state = 'confirmed'
            rec.create_refund()

    def create_refund(self):
        for rec in self:
            invoice_line_data = []
            inv_obj = self.env['account.move']
            for line in rec.order_line_ids:
                invoice_line_data.append((0, 0, {
                    'product_id': self.env['product.product'].search([('product_tmpl_id','=',line.product_template_id.id)]).id,
                    'account_id': line.product_template_id.categ_id.property_account_income_categ_id.id,
                    'analytic_tag_ids': self.env.user.analytic_tag_ids.ids,
                    'price_unit': line.price_unit,
                    'quantity': 1, }))
            invoice = inv_obj.create({
                'ref': rec.name,
                'reimbursement_id': rec.id,
                'move_type': 'in_refund',
                'partner_id': rec.vendor_id.id,
                'invoice_date': date.today(),
                'date': date.today(),
                'invoice_line_ids': invoice_line_data,
            })
            print("%s" % invoice.name)

    def cron_reset_sequence_fmcg_reimbursement(self):
        if date.today().day == 1:
            sequence = self.env['ir.sequence'].search([('code', '=', 'seq.fmcg.claim.to.principle')])
            sequence.number_next_actual = 1

    @api.onchange('cust_target_id')
    def set_cust_reward_line(self):
        for rec in self:
            if rec.cust_target_id:
                line_ids = []
                used_voucher = rec.cust_target_id.customer_voucher_ids.filtered(lambda x: x.is_claimed == False and x.state == 'used')
                if used_voucher:
                    for line in used_voucher:
                        line_ids.append((0, 0, {'customer_id': line.customer_id.id, 'voucher_id': line.id, 'reward_type': line.reward_type, 'reward_amount': line.reward_amount})),
                if line_ids:
                    rec.customer_reward_ids = [(6, 0, [])]
                    rec.customer_reward_ids = line_ids

    def send_email(self):
        ''' Opens a wizard to compose an email, with relevant mail template loaded by default '''
        self.ensure_one()
        claim_report = self.env.ref('equip3_fmcg_sale.action_print_report_claim_to_principle')
        render_report = claim_report.sudo()._render_qweb_pdf(self.ids, None)
        data_record = base64.b64encode(render_report[0])
        ir_values = {
            'name': 'Claim to Principle - ' + self.name + '.pdf',
            'type': 'binary',
            'datas': data_record,
            'store_fname': data_record,
            'mimetype': 'application/pdf',
            'res_model': 'fmcg.reimbursement',
        }
        claim_report_attachment_id = self.env['ir.attachment'].sudo().create(ir_values)
        template_id = self.env.ref('equip3_fmcg_sale.email_template_claim_to_principle_new')
        template_id.attachment_ids = [(5, 0, 0)]
        template_id.attachment_ids = [(4, claim_report_attachment_id.id)]
        lang = self.env.context.get('lang')
        ctx = {
            'default_model': 'fmcg.reimbursement',
            'default_res_id': self.id,
            'default_use_template': bool(template_id),
            'default_template_id': template_id.id,
            'default_composition_mode': 'comment',
            'default_partner_ids': [(6, 0, self.vendor_id.ids)],
            'mark_so_as_sent': True,
            'force_email': True,
            'res_name': self.name or '',
            'vendor_name': self.vendor_id.name
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }

    def action_print(self):
        template = self.env.ref('equip3_fmcg_sale.action_print_report_claim_to_principle').report_action(self)
        return template

    def _get_street(self, partner):
        self.ensure_one()
        res = {}
        address = ''
        if partner.street:
            address = "%s" % (partner.street)
        if partner.street2:
            address += ", %s" % (partner.street2)
        # reload(sys)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    def _get_address_details(self, partner):
        self.ensure_one()
        res = {}
        address = ''
        if partner.city:
            address = "%s" % (partner.city)
        if partner.state_id.name:
            address += ", %s" % (partner.state_id.name)
        if partner.zip:
            address += ", %s" % (partner.zip)
        if partner.country_id.name:
            address += ", %s" % (partner.country_id.name)
        # reload(sys)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

class CustomerRewardLine(models.Model):
    _name = 'customer.reward.line'

    reimbursement_id = fields.Many2one('fmcg.reimbursement', string="Reimbursement")
    customer_id = fields.Many2one('res.partner', string="Customer", domain="[('is_customer','=',True)]", required=True)
    voucher_id = fields.Many2one('customer.voucher', string="Voucher", domain="[('customer_id','=',customer_id),('is_claimed','=',False),('state','=','used')]")
    reward_type = fields.Selection(string="Reward Type", related='voucher_id.reward_type', store=True, readonly=True)
    reward_amount = fields.Float(string="Reward Amount", related='voucher_id.reward_amount', store=True, readonly=True)

class ReimbursementOrderLine(models.Model):
    _name = 'reimbursement.order.line'

    reimbursement_id = fields.Many2one('fmcg.reimbursement', string="Reimbursement", readonly=True)
    sequence = fields.Integer("No.", readonly=True)
    product_template_id = fields.Many2one('product.template', string="Product", readonly=True)
    name = fields.Char("Description", related='product_template_id.name', store=True)
    product_uom_qty = fields.Float("Quantity", readonly=True)
    product_uom = fields.Many2one(related="product_template_id.uom_id", store=True)
    price_unit = fields.Float("Unit Price", related="reimbursement_id.total_amount", store=True)
    price_total = fields.Float("Total Amount", related="reimbursement_id.total_amount", store=True)

