odoo.define('sh_activities_management/static/src/models/components/cancel_activity_chatter.js', function (require) {
    'use strict';
    const components = {
        Chatter: require('mail/static/src/components/chatter/chatter.js'),
    };
    const {
        registerFieldPatchModel,       
    } = require('mail/static/src/model/model_core.js');        
    const { patch } = require('web.utils');
    const { attr } = require('mail/static/src/model/model_field.js');
    patch(components.Chatter, 'sh_activities_management/static/src/models/components/cancel_activity_chatter.js', {

        toggleCancelActivityBoxVisibility() {               
            this.chatter.update({ iscancelActivityBoxVisible: !this.chatter.iscancelActivityBoxVisible });
        },
        
        /**
         * @private
         *
         */
        _onClickCancelTitle(ev){        
            ev.preventDefault();
            this.toggleCancelActivityBoxVisibility();

        }

    });

    registerFieldPatchModel('mail.chatter', 'sh_activities_management/static/src/models/components/cancel_activity_chatter.js', {       
        iscancelActivityBoxVisible: attr({
            default: false,
        }),        
    });          
});