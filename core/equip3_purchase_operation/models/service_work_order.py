from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
import pytz


class ServiceWorkOrder(models.Model):
    _name = 'service.work.order'
    _description = 'Service Work Order'
    _order = 'id desc'

    def _compute_account_moves(self):
        account_move = self.env['account.move']
        for record in self:
            record.account_move_count = account_move.sudo().search_count([('ref', 'ilike', record.name)])

    name = fields.Char(string='Reference', default=lambda self: _(
        'New'), index=True, readonly=True,copy=False)
    partner_id = fields.Many2one(comodel_name='res.partner', string='Vendor',domain="['|',('company_id','=',False),('company_id','=',company_id)]", readonly=True, states={'draft': [('readonly', False)]})
    account_analytic_tag_ids = fields.Many2many(comodel_name='account.analytic.tag', string='Analytic Group', readonly=True, states={'draft': [('readonly', False)]})
    date_planned = fields.Datetime('Schedule Date', readonly=True, states={'draft': [('readonly', False)]})
    deadline_date = fields.Datetime('Deadline')
    origin = fields.Char(string='Source Document')
    company_id = fields.Many2one(comodel_name='res.company', string='Company', readonly=True, states={'draft': [('readonly', False)]})
    branch_id = fields.Many2one(comodel_name='res.branch', string='Branch', default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)], readonly=True, states={'draft': [('readonly', False)]})
    order_line = fields.One2many(comodel_name='service.work.order.line', inverse_name='swo_id', string='Order Line')
    state = fields.Selection(string='State', selection=[('draft', 'draft'), ('confirm', 'On Progress'),('done','Done'),('cancel','Cancel')], default="draft")
    purchase_order_id = fields.Many2one(comodel_name='purchase.order', string='Purchase Order')
    checklist_ids = fields.One2many(comodel_name='service.work.order.checklist', inverse_name='swo_id', string='Checklist', readonly=True, states={'draft': [('readonly', False)],'confirm': [('readonly', False)]})
    purchase_line_milestone_id = fields.Many2one(comodel_name='milestone.contract.template.purchase', string='Milestone PO-Line')
    milestone_name = fields.Char(string='Milestone Name',related="purchase_line_milestone_id.name")
    contract_term = fields.Float(string='Contract Term',related="purchase_line_milestone_id.contract_term")
    progress_paid = fields.Float("Progress Paid")
    move_id = fields.Many2one('account.move', 'Credit Note', readonly=1)
    invoiced = fields.Boolean("Invoiced")
    account_move_count = fields.Integer(compute=_compute_account_moves)

    
    def button_confirm(self):
        self.write({'state':'confirm'})

    def button_done(self):
        self.ensure_one()
        if any(line.state2 not in ('Completed','Cancelled') for line in self.order_line):
            raise ValidationError(_("Please Complete all Service"))

        move_values = []
        for line in self.order_line:
            product_id = line.product_id
            if product_id.categ_id.property_valuation != 'real_time' or product_id.type != 'service':
                continue

            categ_id = product_id.categ_id
            if not categ_id:
                raise ValidationError(_("Please set category for product %s" % product_id.display_name))
            
            journal_id = categ_id.property_stock_journal
            if not journal_id:
                raise ValidationError(_("Please set service journal for product category %s" % categ_id.display_name))

            debit_account_id = categ_id.property_stock_valuation_account_id
            if not debit_account_id:
                raise ValidationError(_("Please set service valuation account for product category %s" % categ_id.display_name))

            credit_account_id = categ_id.property_stock_account_input_categ_id
            if not credit_account_id:
                raise ValidationError(_("Please set service input account for product category %s" % categ_id.display_name))

            ref = '%s %s' % (self.name, product_id.display_name)
            amount = (line.order_line_id.price_subtotal * self.contract_term) / 100
            move_values += [{
                'ref': ref,
                'journal_id': journal_id.id,
                'date': fields.Datetime.now(),
                'move_type': 'entry',
                'company_id': self.company_id and self.company_id.id or self.env.company.id, 
                'branch_id': self.branch_id and self.branch_id.id or self.env.user.branch_id.id,
                'is_from_swo': True,
                'line_ids': [
                    (0, 0, {
                        'name': ref,
                        'ref': ref,
                        'product_id': product_id.id,
                        'product_uom_id': product_id.uom_id.id,
                        'quantity': line.order_line_id.product_qty,
                        'account_id': debit_account_id.id,
                        'debit': amount
                    }),
                    (0, 0, {
                        'name': ref,
                        'ref': ref,
                        'product_id': product_id.id,
                        'product_uom_id': product_id.uom_id.id,
                        'quantity': line.order_line_id.product_qty,
                        'account_id': credit_account_id.id,
                        'credit': amount
                    })
                ],
            }]
        move_ids = self.env['account.move'].create(move_values)
        # move_ids.action_post()
        [move.action_post() for move in move_ids]
        self.write({'state': 'done'})
 
    def button_cancel(self):
        self.write({'state':'cancel'})

    def button_open_whatsapp(self):
        return {'type': 'ir.actions.act_window',
                'name': _('Send Whatsapp Message'),
                'res_model': 'whatsapp.message.wizard',
                'target': 'new',
                'view_mode': 'form',
                'view_type': 'form',
                'context': {'default_template_id': self.env.ref('equip3_purchase_operation.whatsapp_swo_template').id},
                }

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].sudo().next_by_code(
                'service.work.order') or _('New')
        result = super(ServiceWorkOrder, self).create(vals)
        return result

    def unlink(self):
        if any(self.filtered(lambda report: report.state not in ('draft'))):
            raise UserError(
                _('You cannot delete a report which is not draft!'))
        return super(ServiceWorkOrder, self).unlink()

    def action_view_journal_items(self):
        self.ensure_one()
        return {
           'name': _('Journal Items'),
           'view_mode': 'tree,form',
           'res_model': 'account.move',
           'type': 'ir.actions.act_window',
           'domain': [('ref', 'ilike', self.name)]
        }


    
class ServiceWorkOrderLine(models.Model):
    _name = 'service.work.order.line'
    _description = 'Service Work Order Line'

    swo_id = fields.Many2one(comodel_name='service.work.order', string='Service Work Order')
    sequence2 = fields.Char(string='No',readonly=True,copy=False)
    product_id = fields.Many2one(comodel_name='product.product', string='Product', required=True, readonly=True, states={'draft': [('readonly', False)]})
    description = fields.Char(string='Description', readonly=True, states={'draft': [('readonly', False)]})
    initial_demand = fields.Float(string='Initial Demand', readonly=True, states={'draft': [('readonly', False)]})
    remaining = fields.Float(string='Remaining', readonly=True, states={'draft': [('readonly', False)]})
    quantity_done = fields.Float(string='Done', readonly=True, states={'draft': [('readonly', False)],'confirm': [('readonly', False)]})
    state2 = fields.Char(string='State')
    account_analytic_tag_ids = fields.Many2many(comodel_name='account.analytic.tag', string='Analytic Group', readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection(string='SWO State', related="swo_id.state", store=True)
    order_line_id = fields.Many2one('purchase.order.line', string='Purchase Order Line')


    @api.model
    def default_get(self, fields):
        res = super(ServiceWorkOrderLine, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'line_ids' in context_keys:
                if len(self._context.get('line_ids')) > 0:
                    next_sequence = len(self._context.get('line_ids')) + 1
            res.update({'sequence2': next_sequence})
        return res
    
    def btn_check(self):
        for rec in self:
            rec.write({"state2": "Completed"})

    def btn_close(self):
        for rec in self:
            rec.write({"state2": "Cancelled"})
    
class ServiceWorkOrderChecklist(models.Model):
    _name = 'service.work.order.checklist'
    _description = 'Service Work Order Checklist'

    swo_id = fields.Many2one(comodel_name='service.work.order', string='Service Work Order', ondelete="cascade")
    name = fields.Char(string='Name', required=True)
    desc = fields.Char(string='Description')
    state = fields.Selection(string='SWO State', related="swo_id.state", store=True)
    state2 = fields.Char(string='State')
    

    def btn_check(self):
        for rec in self:
            rec.write({"state2": "Completed"})

    def btn_close(self):
        for rec in self:
            rec.write({"state2": "Cancelled"})