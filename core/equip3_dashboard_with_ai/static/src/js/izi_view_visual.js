odoo.define('equip3_dashboard_with_ai.IZIViewVisual', function (require) {
    'use strict';

    var IZIAutocomplete = require('izi_dashboard.IZIAutocomplete');
    var IZIViewVisual = require('izi_dashboard.IZIViewVisual');
    var core = require('web.core');
    var _t = core._t;

    IZIViewVisual.include({

        _getLabAnalysisText: function (ai_analysis_data) {
            var self = this;
            if (self.analysis_id) {
                self._rpc({
                    model: 'izi.analysis',
                    method: 'action_get_lab_analysis_text',
                    args: [self.analysis_id, ai_analysis_data],
                }).then(function (result) {
                    if (result.status == 200) {
                        if (self.parent.$description) {
                            self.parent.$description.html(result.ai_analysis_text);
                        }
                    } else if (self.index == 0) {
                        if (result.status == 401) {
                            var message_data = 'Your API key has expired. Please contact your administrator';
                            new swal('Need Access', message_data, 'warning');
                            self.do_action({
                                type: 'ir.actions.act_window',
                                name: _t('Need API Access'),
                                target: 'new',
                                res_model: 'izi.lab.api.key.wizard',
                                views: [[false, 'form']],
                                context: {},
                            },{
                                on_close: function(){
                                }
                            });
                        } else
                            var message_data = result.message;
                            var message_data = message_data.replace("odoo", "Hashmicro");
                            var message_data = message_data.replace("Odoo", "Hashmicro");
                            new swal('Error', message_data, 'error');
                    }
                    self.mode = false;
                    self.parent.mode = false;
                })
            }
        },


        
    });
});