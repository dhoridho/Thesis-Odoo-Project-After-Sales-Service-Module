from odoo import models, fields, api



class MainWizard(models.TransientModel):
    _name = 'main.wizard'
    _description = 'Main Wizard'

    # name = fields.Char('Name')
    main_model_id = fields.Many2one('main.model', 'Main Model Ref')

    def action_maju(self):
        self.main_model_id.write({'state_id': self.main_model_id.state_id.id + 1})

    def action_mundur(self):
        self.main_model_id.write({'state_id': self.main_model_id.state_id.id - 1})


