odoo.define('equip3_dashboard_with_ai.IZIViewAnalysis', function (require) {
    'use strict';

    var IZIAutocomplete = require('izi_dashboard.IZIAutocomplete');
    var IZIViewAnalysis = require('izi_dashboard.IZIViewAnalysis');
    var core = require('web.core');
    var _t = core._t;

    IZIViewAnalysis.include({

         _onClickContinueScriptAI: function(ev) {
            var self = this;
            if (self.$editor && self.analysis_id) {
                var cur_pos = self.$editor.getCursorPosition();
                var row = cur_pos.row;
                var col = cur_pos.column;
                var spaces = '';
                for (var i = 0; i < col; i++) {
                    spaces += ' ';
                }
                var previous_code = '';
                var total_line = 0;
                while (row >= 0) {
                    if (previous_code == '') {
                        previous_code = self.$editor.session.getLine(row);
                    } else {
                        var line = self.$editor.session.getLine(row);
                        previous_code = line + '\n' + previous_code;
                    }
                    row--;
                    total_line++;
                    if (total_line > 20)
                        break;
                }
                // row = cur_pos.row + 1;
                // total_line = 0;
                // var maximum_line = self.$editor.session.getLength()
                // var next_code  = '';
                // if (row <= maximum_line)
                //     var next_code = '\n' + self.$editor.session.getLine(row);
                // while (row <= maximum_line) {
                //     var line = self.$editor.session.getLine(row);
                //     next_code = next_code + '\n' + line;
                //     row++;
                //     total_line++;
                //     if (total_line > 5)
                //         break;
                // }
                if (previous_code) {
                    // Instruction to AI
                    var instruction = `You are a code generator. 
                        You will continue the code below.
                        Only answer in ${self.scriptEditorType} syntax!
                        DO NOT ADD ANY OTHER TEXT!
                        DO NOT ANSWER WITH THE PREVIOUS CODE!
                        JUST ANSWER YOUR CODE THAT CONTINUE THIS CODE!
                        ONLY ANSWER WITH 1-2 LINES!
                        \n${previous_code}`
                    self._rpc({
                        model: 'izi.analysis',
                        method: 'action_get_lab_script',
                        args: [self.analysis_id, instruction],
                    }).then(function (result) {
                        if (result.status == 200) {
                            // Insert Answer From AI
                            var code = result.code;
                            var cur_line_code = self.$editor.session.getLine(cur_pos.row);
                            var cur_line_code_trim = cur_line_code.trimStart();
                            if (code.includes(cur_line_code_trim)) {
                                code = code.replace(cur_line_code_trim, '');
                            }
                            self.$editor.session.insert({
                                row: cur_pos.row,
                                column: cur_pos.column,
                            }, code);
                            
                        } else {
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
                    }); 
                }               
            }
        },


        
    });
});