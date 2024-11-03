import time
from odoo import fields, models, api
from odoo.exceptions import ValidationError, Warning
from odoo.tools.translate import _
from datetime import datetime, timedelta
# from mx.DateTime import RelativeDateTime, now, DateTime, localtime
# import string
# import mx.DateTime as dt


class agent_commission_invoice(models.Model):
    _name = "agent.commission.invoice"
    _description = "Agent Commision Invoice"


    @api.model
    def create(self, vals):
        # function overwrites create method and auto generate request no.
        # print('In create ---- of agent.commission.invoice')
        # print("\nvals of invoice.... ", vals)
        vals['name'] = self.env['ir.sequence'].next_by_code(
            'agent.commission.invoice')
        # print(vals['name'], "----vals['name']")
        self.write({'name': vals['name']})
        # print("\n..Write.. ")
        res = super(agent_commission_invoice, self).create(vals)
        # print("reseeeeeeees", res)
        commission = self.create_commission(res)
        if commission:
            print("Successfull")
        else:
            raise Warning("No Commission Line for this Agent !!!")
        return res



    def check_obj(self, vals):
        # search for the book_id, if present already
        flag = 0
        quot_objj = self.env['agent.commission.invoice.line'].search(
            [('book_id', '=', self.vals)])
        # print("quot_objj********", quot_objj)
        for objj in quot_objj:
            try:
                objj_browse = self.env[
                    'agent.commission.invoice.line'].browse(objj)
                # print(objj_browse.commission_line_id.id, "------objj_browse")

                obj_id = objj_browse.commission_line_id.id
                try:
                    if obj_id:
                        objj_state = self.env[
                            'agent.commission.invoice'].browse(obj_id)
                        # print(objj_state.state, "objj_state.state")
                        if objj_state.state == "draft" or objj_state.state == "confirm":
                            flag = 1
                    else:
                        print("No record++++++")
                except:
                    print("an error")

            except:
                print("No commission_line_id")

        if flag == 1:
            return False
        else:
            return True


    def create_commission(self, vals):
        # print("Partner _id", vals.partner_id.id)
        reservation_obj = self.env['hotel.reservation'].search([(
            'via', '=', 'agent'), ('agent_id', '=', vals.partner_id.id), ('invoiced', '=', False), ('state', '=', 'done')])

        # print("reservation_obj..............", reservation_obj.ids)

        if reservation_obj:
            for reserv in self.env['hotel.reservation'].browse(reservation_obj.ids):
                com_amt = 0.0
#                 amt = self.env['res.currency'].compute(
# reserv.pricelist_id.currency_id.id, vals.pricelist_id.currency_id.id,
# reserv.agent_comm)
                amt = self.pricelist_id.currency_id.compute(reserv.agent_comm,
                                                            reserv.pricelist_id.currency_id,
                                                            round=False)
                com_amt = (float(amt) * vals.commission_percentage) / 100
                # print("comm_amt", com_amt)
                dict = {
                    'name': reserv.name,
                    'book_id': reserv.id,
                    'partner_id': reserv.partner_id.id,
                    'tour_cost': reserv.agent_comm,
                    'commission_amt': com_amt,
                    'commission_percentage': vals.commission_percentage,
                    'commission_line_id': vals.id,
                }
                line_data = True
                record = self.env['agent.commission.invoice.line'].create(dict)
            if line_data:
                return True
            else:
                return False
        else:
            return False


    @api.depends('commission_line')
    def _get_total_amt(self):
        total = 0
        for i in range(0, len(self.commission_line)):
            total = total + self.commission_line[i].commission_amt
        self.total_amt = total



    name = fields.Char("Agent Commission ID",   readonly=True)
    current_date = fields.Date("Date", required=True, readonly=True, default=datetime.now(
    ).strftime('%Y-%m-%d'), states={'draft': [('readonly', False)]})
    partner_id = fields.Many2one("res.partner", "Agent", required=True, readonly=True, states={'draft': [('readonly', False)]})
    commission_line = fields.One2many('agent.commission.invoice.line', 'commission_line_id', 'Invoice Lines')
    agent_invoice_ids = fields.Many2many('account.move', 'booking_agent_invoice_rel', 'booking_agent_id', 'invoice_id', 'Agent Invoices', readonly=True)
    state = fields.Selection([
                            ('draft', 'Draft'),
                            ('confirm', 'Confirmed'),
                            ('invoiced', 'Invoiced'),
                            ('done', 'Done'),
                            ('cancel', 'Canceled'),
    ], 'Status', default='draft', readonly=True)

    commission_percentage = fields.Float("Commission %", required=True, readonly=True,  states={'draft': [('readonly', False)]})
    total_amt = fields.Float(compute="_get_total_amt", method=True, string="Total", store=True)

    recv_acc = fields.Many2one('account.account', string="Expense Account",
                               required=True, readonly=True, states={'draft': [('readonly', False)]})

    pricelist_id = fields.Many2one('product.pricelist', 'Pricelist', required=True, readonly=True, states={'draft': [('readonly', False)]})


    @api.onchange('pricelist_id')
    def onchange_pricelist_id(self):
        if not self.pricelist_id:
            return {}
        if not self.commission_line or self.commission_line == [(6, 0, [])]:
            return {}
        if len(self.commission_line) != 1:
            warning = {
                'title': _('Pricelist Warning!'),
                'message': _('If you change the pricelist of this Commission (and eventually the currency), prices of existing commission lines will not be updated.')
            }
            return {'warning': warning}
        return {}


    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id.commission and self.partner_id:
            self.commission_percentage = self.partner_id.commission
            # print("commisssionnnnnnnn", self.commission_percentage)
            self.pricelist_id = self.partner_id.property_product_pricelist.id
            # print("Pricelist...........", self.partner_id.commission)
        if self.partner_id and not self.partner_id.commission:
            raise Warning(
                "No Commission Percentage is defined for this Agent. Please Configure First !!!")
        if self.ids:
            raise Warning("Cannot change agent at this stage.")

    def confirm_commission(self):
        if not self.commission_line:
            raise Warning("No Commission line for this Agent.")
        else:
            self.write({'state': 'confirm'})
        return True



    # @api.multi
    def done(self):
        for obj in self:
            for invoice in self.agent_invoice_ids:
                if invoice.invoice_payment_state != 'paid':
                    raise Warning("Invoice is not Paid Yet.")
        self.write({'state': 'done'})
        return True


    def make_commission_invoice(self):
        for obj in self:
            acc_id = obj.partner_id.property_account_payable_id.id
            #journal_obj = self.env('account.journal')
            # print("\nacount id ----", acc_id)
            journal_ids = self.env['account.journal'].search([('type', '=', 'purchase')], limit=1)
            # print("\njournal id--", journal_ids)
            journal_id = None
            if journal_ids[0]:
                journal_id = journal_ids[0].id
            # print("Journaaaal id", journal_id)
            type = 'in_invoice'
            inv = {
                'name': obj.name,
                'invoice_origin': obj.name,
                'type': type,
                'ref': "Commission Invoice",
                # 'account_id': acc_id,
                'partner_id': obj.partner_id.id,
                'currency_id': obj.pricelist_id.currency_id.id,
                'journal_id': journal_id,
                # 'amount_tax': 0,
                # 'amount_untaxed': obj.total_amt,
                # 'amount_total': obj.total_amt,
            }
            # print("inv---->", inv)
            inv_id = self.env['account.move'].create(inv)
            inv_id.write({
                'invoice_line_ids': [(0, 0, {

                'name': obj.name,
                'account_id': obj.recv_acc.id,
                'price_unit': obj.total_amt,
                'quantity': 1.0,
                'name': obj.name,
                })]
            })


            # print("fffffffffff",inv_id.invoice_line_ids)
            # record = self.env['account.move.line'].create(il)
            for banq in obj.commission_line:
                self.env['hotel.reservation'].write(
                    {'invoiced': True})
            self._cr.execute(
                 'insert into booking_agent_invoice_rel(booking_agent_id,invoice_id) values (%s,%s)', (obj.id, inv_id.id))
        self.write({'state': 'invoiced'})
        return True



class agent_commission_invoice_line(models.Model):
    _name = "agent.commission.invoice.line"
    _description = " Commision Invoice Line"

    name = fields.Char("Name Inv Lines",   required=True)
    book_id = fields.Many2one(
        "hotel.reservation", "Booking Ref.", required=True)
    partner_id = fields.Many2one("res.partner", "Customer Name", required=True)
    tour_cost = fields.Float('Total Cost', required=True)
    commission_percentage = fields.Float('Commission %', required=True)
    commission_amt = fields.Float("Commission Amount", required=True)
    commission_line_id = fields.Many2one(
        "agent.commission.invoice", "Commission ID")

    
    @api.model
    def create(self, vals):
        # print("vals::::::::::::",vals)
        if not vals.get('name'):
            raise Warning("You cann't create commission line manually.")
        return super(agent_commission_invoice_line, self).create(vals)


    @api.onchange('book_id')
    def on_change_tour_book_id(self):
        result = {}
        self.name = self.book_id.name
        result['name'] = self.book_id.name
        return {'value': result}


    @api.onchange('commission_percentage')
    def on_change_commission_amt(self):
        com_amt = 0.0
        com_amt = (float(self.tour_cost) * self.commission_percentage) / 100
        # print("comm_amt", com_amt)
        self.commission_amt = com_amt

