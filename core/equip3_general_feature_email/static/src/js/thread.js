odoo.define('equip3_general_feature_email.thread', function (require){
    "use strict";

    const {
        registerInstancePatchModel,
        registerFieldPatchModel,
    } = require('mail/static/src/model/model_core.js');
    const { many2one } = require('mail/static/src/model/model_field.js');
    const threadJS = require('mail/static/src/models/thread/thread.js');

    registerInstancePatchModel('mail.thread', 'equip3_general_feature_email/static/src/js/thread.js', {

        /**
         * Compute an url string that can be used inside a href attribute
         *
         * @override
         */
        _computeUrl() {
            const baseHref = this.env.session.url('/web');
            if (this.model === 'mail.channel') {
                return `${baseHref}#action=mail.action_discuss&active_id=${this.model}_${this.id}`;
            }
            var url = `${baseHref}#model=${this.model}&id=${this.id}`
            if(this.messages && this.messages.length > 0){
                if(this.messages[0].action_id_position){
                    url += '&view_type=form&action='+this.messages[this.messages.length-1].action_id_position
                }
            }
            return url;
        }

    });

});
