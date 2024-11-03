from odoo import _, models

class WizardForProcessConsi(models.TransientModel):
    _name = 'wizard.for.process.consi'
    _description = 'Wizard for Process Consi'

    def process(self):
        active_model = self.env.context.get('active_model', False)
        if active_model == 'sale.order':
            active_so = self.env['sale.order'].browse(self._context.get('active_id'))
            active_so.state = 'quotation_approved'