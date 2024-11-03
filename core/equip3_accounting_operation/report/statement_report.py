from odoo import fields, models, api, tools
from datetime import date, timedelta

class followUpInvoiceTmp(models.Model):
    _name = "followup.invoice.tmp"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'sequence.mixin']
    _description = ' '

    name = fields.Char(string='Name', default='/')
    date = fields.Date(string='Date',default=fields.Date.context_today)
    partner_id = fields.Many2one('res.partner', 'Customer Name')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id.id)
    overdue_template = fields.Text(string='Overdue Payments Message', compute='_overdue_template')
    move_id = fields.Many2many('account.move', string='Move id')
    total_overdue = fields.Monetary(string="Total Overdue", compute='_calculate_total', store=True, tracking=True)
    

    @api.depends('partner_id')
    def _overdue_template(self):
        if self.id:
            ICP = self.env['ir.config_parameter'].sudo()
            self.overdue_template = ICP.get_param('overdue_template', False)

    @api.depends('move_id')
    def _calculate_total(self):
        for rec in self:
            if rec.move_id:
                total = 0
                for move in rec.move_id:
                    total = total +  move.amount_residual
                rec.total_overdue = total

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

class ReportfollowUpInvoiceTmp(models.AbstractModel):
    _name = 'report.equip3_accounting_operation.report_statement_temp'
    _description = ' '

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['followup.invoice.tmp'].browse(docids)
        return {
            'doc_ids': docs.ids,
            'doc_model': 'followup.invoice.tmp',
            'docs': docs,
        }
