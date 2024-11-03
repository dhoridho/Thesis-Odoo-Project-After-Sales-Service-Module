odoo.define('sh_activities_management/static/src/models/components/thread_inherit.js', function (require) {
    'use strict';       
    const {
        registerInstancePatchModel,       
    } = require('mail/static/src/model/model_core.js');    
    
    registerInstancePatchModel('mail.thread', 'sh_activities_management/static/src/models/components/thread_inherit.js', {
        async refreshActivities() {
            if (!this.hasActivities) {
                return;
            }
            if (this.isTemporary) {
                return;
            }
            // A bit "extreme", may be improved
            const [{ activity_ids: newActivityIds }] = await this.async(() => this.env.services.rpc({
                model: this.model,
                method: 'read',
                args: [this.id, ['activity_ids']]
            }, { shadow: true }));
            const activitiesData = await this.async(() => this.env.services.rpc({
                model: 'mail.activity',
                method: 'activity_format',
                args: [newActivityIds]
            }, { shadow: true }));
            const activities = this.env.models['mail.activity'].insert(activitiesData.map(
                activityData => this.env.models['mail.activity'].convertData(activityData)
            ));            
            const doneactivitiesData = await this.async(() => this.env.services.rpc({
                model: 'mail.activity',
                method: 'doneactivity_format',
                args: [newActivityIds, this['id'], this['model']]
            }, { shadow: true }));
            const doneactivities = this.env.models['mail.activity'].insert(doneactivitiesData.map(
                activityData => this.env.models['mail.activity'].convertData(activityData)
            ));            
            this.update({ activities: [['replace', doneactivities]] });
        }
    
    });
    
});
    
