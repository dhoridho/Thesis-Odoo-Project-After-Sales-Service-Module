from odoo import fields,models,api
from odoo.modules.module import get_module_path


class updateIpRules(models.TransientModel):
    _name = 'update.ip.rules'
    
    source = fields.Selection([('database','Database'),('ip_txt','ip.txt')])
    ip_rule_id = fields.Many2one('ip.allowed.rules')
    ip_ids = fields.One2many('update.ip.line','rules_id')
    ip_txt_value = fields.Text()
    
    
    
    @api.onchange('source')
    def _onchange_source(self):
        for data in self:
            print(data.source)
            if data.source == 'database':
                line_ids = []
                for line in data.ip_rule_id.rule_line_ids:
                    line_ids.append((0,0,{'ip':line.name}))
                print(line_ids)
                data.ip_ids = line_ids
            elif data.source == 'ip_txt':
                data.ip_ids = [(6,0,[])]
                module_path = get_module_path('equip3_clonning_prevention')
                fpath = module_path + '/data/'
                ip_txt_value = ""
                with open(fpath+'ip.txt', 'r') as f:
                    contents = f.read()
                    if contents:
                        ip_txt_value = eval(contents)
                data.ip_txt_value = ip_txt_value
                
                    
                    
    
    def update_ip(self):
        if self.source == 'database':
            if self.ip_ids:
                self.ip_rule_id.rule_line_ids = [(6,0,[])]
                new_ip = []
                for line in self.ip_ids:
                    new_ip.append((0,0,{'name':line.ip}))
                
                self.ip_rule_id.rule_line_ids = new_ip
        elif self.source == 'ip_txt':
            module_path = get_module_path('equip3_clonning_prevention')
            fpath = module_path + '/data/'
            with open(fpath+'ip.txt', 'w') as outfile:
                outfile.write(self.ip_txt_value)



class updateIpRulesLine(models.TransientModel):
    _name = 'update.ip.line'
    
    rules_id = fields.Many2one('update.ip.rules')
    ip = fields.Char()
    