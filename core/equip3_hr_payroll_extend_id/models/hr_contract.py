# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from lxml import etree

class Contract(models.Model):
    _inherit = 'hr.contract'
    
    @api.model
    def _multi_company_domain(self):
        return [('company_id','=', self.env.company.id)]


    struct_pesangon_id = fields.Many2one('hr.payroll.structure', string='Pesangon Structure',domain=_multi_company_domain)
    other_allowance_1 = fields.Monetary(string='Allowance 1', tracking=True, help="Allowance 1.")
    other_allowance_2 = fields.Monetary(string='Allowance 2', tracking=True, help="Allowance 2.")
    other_allowance_3 = fields.Monetary(string='Allowance 3', tracking=True, help="Allowance 3.")
    other_allowance_4 = fields.Monetary(string='Allowance 4', tracking=True, help="Allowance 4.")
    other_allowance_5 = fields.Monetary(string='Allowance 5', tracking=True, help="Allowance 5.")
    other_allowance_6 = fields.Monetary(string='Allowance 6', tracking=True, help="Allowance 6.")
    other_allowance_7 = fields.Monetary(string='Allowance 7', tracking=True, help="Allowance 7.")
    other_allowance_8 = fields.Monetary(string='Allowance 8', tracking=True, help="Allowance 8.")
    other_allowance_9 = fields.Monetary(string='Allowance 9', tracking=True, help="Allowance 9.")
    other_allowance_10 = fields.Monetary(string='Allowance 10', tracking=True, help="Allowance 10.")
    contract_line_ids = fields.One2many('hr.contract.line','contract_id', string="Contract Line")
    rapel_date = fields.Date('Rapel Date')

    @api.onchange('struct_id')
    def _onchange_struct_id(self):
        selected_struct = self.struct_id
        if selected_struct:
            self.contract_line_ids = [(5, 0, 0)]
            line_ids = []
            if selected_struct.parent_id:
                for rec in selected_struct.parent_id.rule_ids:
                    contract_line = {
                        'name': rec.name,
                        'sequence': rec.sequence,
                        'category': rec.category_id.name,
                        'amount_select': rec.amount_select,
                        'contract_id': self.id,
                        'salary_rule_id': rec.id,
                        'apply_to_overtime_calculation': rec.apply_to_overtime_calculation,
                    }
                    line_ids.append((0, 0, contract_line))

            for rec in selected_struct.rule_ids:
                contract_line = {
                    'name': rec.name,
                    'sequence': rec.sequence,
                    'category': rec.category_id.name,
                    'amount_select': rec.amount_select,
                    'contract_id': self.id,
                    'salary_rule_id': rec.id,
                    'apply_to_overtime_calculation': rec.apply_to_overtime_calculation,
                }
                line_ids.append((0, 0, contract_line))
            self.contract_line_ids = line_ids

    @api.model
    def contract_lines_update(self):
        for contract in self.env['hr.contract'].search([]):
            salary_rules_list = []
            for line in contract.contract_line_ids:
                salary_rule_id = self.env['hr.salary.rule'].search([('id', '=', line.salary_rule_id.id)], limit=1)
                salary_rules_list.append(salary_rule_id.id)
            structure_rule_ids = contract.struct_id.rule_ids.ids
            intersection = set(salary_rules_list).intersection(structure_rule_ids)
            ids_to_delete = set(salary_rules_list).difference(intersection)
            ids_to_add = set(structure_rule_ids).difference(intersection)

            if intersection:
                for line in contract.contract_line_ids:
                    salary_rule_id = self.env['hr.salary.rule'].search([('id', '=', line.salary_rule_id.id)], limit=1)
                    if salary_rule_id.id in intersection:
                        line.write({
                            'sequence': salary_rule_id.sequence
                        })

            if ids_to_delete:
                for line in contract.contract_line_ids:
                    salary_rule_id = self.env['hr.salary.rule'].search([('id', '=', line.salary_rule_id.id)], limit=1)
                    if salary_rule_id.id in ids_to_delete:
                        line.unlink()

            for value in ids_to_add:
                salary_rule_id = self.env['hr.salary.rule'].browse(value)
                vals = {
                    'name': salary_rule_id.name,
                    'sequence': salary_rule_id.sequence,
                    'category': salary_rule_id.category_id.name,
                    'amount_select': salary_rule_id.amount_select,
                    'contract_id': contract.id,
                    'salary_rule_id': salary_rule_id.id,
                    'apply_to_overtime_calculation': salary_rule_id.apply_to_overtime_calculation,
                }
                self.env['hr.contract.line'].create(vals)

class ContractLine(models.Model):
    _name = 'hr.contract.line'
    _description = 'Contract Line'
    _order = 'sequence asc'

    contract_id = fields.Many2one('hr.contract', string="Contract Id")
    salary_rule_id = fields.Many2one('hr.salary.rule', string="Salary Rule")
    sequence = fields.Integer(string="Sequence")
    name = fields.Char('Name')
    category = fields.Char('Category')
    apply_to_overtime_calculation = fields.Boolean('Apply to Overtime Calculation')
    amount_select = fields.Selection([
        ('percentage', 'Percentage (%)'),
        ('fix', 'Fixed Amount'),
        ('code', 'Python Code'),
    ], string='Amount Type', index=True, required=True)
    amount = fields.Float('Amount')

class employee_contract(models.Model):
    _inherit = 'employee.contract'

    rapel_date = fields.Date('Rapel Date', related='contract_id.rapel_date')