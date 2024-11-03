odoo.define('sh_activities_management/static/src/models/components/done_ativity_chatter.js', function (require) {
    'use strict';
    const components = {
        Chatter: require('mail/static/src/components/chatter/chatter.js'),
    };
    const {
        registerFieldPatchModel,       
    } = require('mail/static/src/model/model_core.js');        
    const { patch } = require('web.utils');
    const { attr } = require('mail/static/src/model/model_field.js');
    patch(components.Chatter, 'sh_activities_management/static/src/models/components/done_ativity_chatter.js', {

        toggleDoneActivityBoxVisibility() {               
            this.chatter.update({ isDoneActivityBoxVisible: !this.chatter.isDoneActivityBoxVisible });
        },
        
        /**
         * @private
         *
         */
        _onClickDoneTitle(ev){        
            ev.preventDefault();
            this.toggleDoneActivityBoxVisibility();

        }

    });

    registerFieldPatchModel('mail.chatter', 'sh_activities_management/static/src/models/components/done_ativity_chatter.js', {       
        isDoneActivityBoxVisible: attr({
            default: false,
        }),        
    });          
});