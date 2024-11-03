from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class SaleOrderReportWizard(models.TransientModel):
    _name = 'construction.sale.order.report.wizard'
    _description = 'Quotation/Sale Order Print Options'

    print_option = fields.Selection(string='Type', selection=[('excel', 'Excel'), ('pdf', 'PDF'),], default = 'excel')
    print_level_option = fields.Selection(string='Level', selection=[('2_level', "2 Levels (Project Scope, Section)"), ('3_level', "3 Levels (Project Scope, Section, Products)"),], default = '2_level')
    print_contract_letter = fields.Boolean(string='Contract Letter',  default=False)
    is_rounding = fields.Boolean(string='Decimal Rounding', default=False)
    sale_order_id = fields.Many2one('sale.order.const', string='Sale Order')

    @api.onchange('print_option')
    def onchange_print_option(self):
        if self.print_option == 'excel':
            self.print_contract_letter = False

    def print_sale_order(self):
        if self.print_option == 'excel':
            return {
                    'type': 'ir.actions.act_url',
                    'url' : '/equip3_construction_sales_operation/sale_order_excel_report/%s' % (self.id),
                    'target': 'new',
                }
        else:
            scope_sect_prod_dict = self.sale_order_id.get_report_data(self.print_level_option)

            datas = {
                'ids': self.ids,
                'model': 'job.estimate',
                'sale_order_id': self.sale_order_id.id,
                'scope_sect_prod_dict': scope_sect_prod_dict,
                'print_contract_letter': self.print_contract_letter,
                'print_level_option': self.print_level_option,
                'is_rounding': self.is_rounding,
            }
            if self.print_contract_letter is True:
                if not self.sale_order_id.contract_template:
                    raise ValidationError(_("You haven't set Contract Template for full contract letter"))
                else:
                    self.sale_order_id.print_on_page()
                    report_id = self.env.ref('equip3_construction_sales_operation.action_report_sale_order')
                    report_id.write({'name': self.sale_order_id.report_title})
                    return report_id.report_action(self, data=datas)
            else:
                report_id = self.env.ref('equip3_construction_sales_operation.action_report_sale_order')
                report_id.write({'name': self.sale_order_id.report_title})
                return report_id.report_action(self, data=datas)
