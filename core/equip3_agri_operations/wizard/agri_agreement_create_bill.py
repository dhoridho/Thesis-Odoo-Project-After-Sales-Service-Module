import json
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AgriAgreementCreateBill(models.TransientModel):
    _name = 'agri.agreement.create.bill'
    _description = 'Agreemnt Create Bill'

    agreement_id = fields.Many2one('agri.agreement', required=True)
    line_ids = fields.One2many('agri.agreement.create.bill.line', 'wizard_id', string='Lines')

    @api.onchange('agreement_id')
    def _onchange_agreement_id(self):
        self.line_ids = [(5,)] + [(0, 0, {
            'contract_id': line.id,
            'to_bill_qty': line.to_bill_qty
        }) for line in self.agreement_id.contract_ids.filtered(lambda o: o.can_create_bill)]

    def action_confirm(self):
        self.ensure_one()
        bill_data = []
        for line in self.line_ids:
            bill_data += [{'contract_id': line.contract_id.id, 'to_bill_qty': line.to_bill_qty}]
        self.agreement_id.action_create_bill(bill_data=bill_data)


class AgriAgreementCreateBillLine(models.TransientModel):
    _name = 'agri.agreement.create.bill.line'
    _description = 'Agreemnt Create Bill Line'

    wizard_id = fields.Many2one('agri.agreement.create.bill', required=True, ondelete='cascade')
    contract_id = fields.Many2one('agri.agreement.contract', required=True, string='Agreement Line')
    sequence = fields.Integer(related='contract_id.sequence')
    activity_id = fields.Many2one('crop.activity', related='contract_id.activity_id')
    done_qty = fields.Float(related='contract_id.done_qty')
    billed_qty = fields.Float(related='contract_id.billed_qty', string='Billed')
    to_bill_qty = fields.Float(digits='Product Unit of Measure', string='To Bill')
    uom_id = fields.Many2one('uom.uom', related='contract_id.uom_id')

    @api.constrains('to_bill_qty')
    def _check_to_bill_qty(self):
        for record in self:
            if record.to_bill_qty > record.done_qty - record.billed_qty:
                raise ValidationError(_('Total Billed value cannot be larger than Done Quantity'))
