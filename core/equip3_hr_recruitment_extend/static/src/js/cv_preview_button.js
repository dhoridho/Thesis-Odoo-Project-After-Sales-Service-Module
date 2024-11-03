odoo.define('equip3_hr_recruitment_extend.cv_preview_button', function(require) {
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

            if (self.model === 'hr.applicant' && self.name == 'file_cv' && self.viewType === 'form' && self.formatType === 'binary') {
                var applications = rpc.query({
                    model: 'hr.applicant',
                    method: 'search_read',
                    args: [[['id','=',self.res_id]], ['id', 'uploaded_cv_type']]
                }).then(function(result) {
                    if (result.length > 0){
                        var mno = result[0]
                        debugger;
                        var cv_type = mno.uploaded_cv_type
                        if (cv_type !== false){
                            if(cv_type == 'application/pdf' || cv_type == 'image/jpeg' || cv_type == 'image/png'){
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
