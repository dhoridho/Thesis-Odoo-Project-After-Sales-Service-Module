odoo.define('equip3_hr_recruitment_extend.letter_preview_button', function(require) {
    "use strict";

    var BasicFields = require('web.basic_fields');
    var core = require('web.core');
    var FormController = require('web.FormController');
    var rpc = require('web.rpc');

    BasicFields.FieldBinaryFile.include({
        events: _.extend({}, BasicFields.FieldBinaryFile.prototype.events, {
            'click .preview_button': "ks_onAttachmentView",
        }),

        _renderReadonly: function() {
            var self = this;
            self._super.apply(this, arguments);
            if (!self.res_id) {
                self.$el.css('cursor', 'not-allowed');
            } else {
                self.$el.css('cursor', 'pointer');
                self.$el.attr('title', 'Download');
                this.$('.ks_binary_file_preview').hide();
            }

            if (self.model === 'hr.offering.request.line' && self.name == 'attachment' && self.viewType === 'form' && self.formatType === 'binary') {
                var letter = rpc.query({
                    model: 'hr.offering.request.line',
                    method: 'search_read',
                    args: [[['id','=',self.res_id]], ['id', 'uploaded_type']]
                }).then(function(result) {
                    if (result.length > 0){
                        var mno = result[0]
                        debugger;
                        var uploaded_type = mno.uploaded_type
                        if (uploaded_type !== false){
                            if(uploaded_type == 'application/pdf' || uploaded_type == 'image/jpeg' || uploaded_type == 'image/png'){
                                self.$el.append(core.qweb.render("ks_preview_button_extend"))
                            }else{
                                debugger;
                            }
                        }
                    }
                });
            }
        },
    });

    
});
