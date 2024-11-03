odoo.define('sh_activities_management/static/src/models/components/activity_inherit.js', function (require) {
    'use strict';
    const components = {
        Activity: require('mail/static/src/components/activity/activity.js'),
    };
    
    const {
        registerInstancePatchModel,
    } = require('mail/static/src/model/model_core.js');          
    const { patch } = require('web.utils');
    const { attr } = require('mail/static/src/model/model_field.js');
    patch(components.Activity, 'sh_activities_management/static/src/models/components/activity_inherit.js', {

    /**
     * @private
     * @param {MouseEvent} ev
     */
    async _onClickCancelArchive(ev) {
        const superMethod = this._super;
        console.log("......superMethod",superMethod);
        await this.activity.archiveServerRecord();
        this.trigger('reload', { keepChanges: true });
    }
    });

    registerInstancePatchModel('mail.activity', 'sh_activities_management/static/src/models/components/activity_inherit.js', {
        async archiveServerRecord() {        
            await this.async(() => this.env.services.rpc({
                model: 'mail.activity',
                method: 'action_cancel',
                args: [[this.id]],
            })); 
        },
    });
});