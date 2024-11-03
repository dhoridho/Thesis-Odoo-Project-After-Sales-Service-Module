odoo.define('sh_activities_management/static/src/models/components/done_activity.js', function (require) {
    'use strict';    
    var Chatter = require('mail/static/src/components/chatter/chatter.js');
    
    Chatter.components={
        Activity: require('mail/static/src/components/activity/activity.js'),    
        ActivityBox: require('mail/static/src/components/activity_box/activity_box.js'),
        AttachmentBox: require('mail/static/src/components/attachment_box/attachment_box.js'),
        ChatterTopbar: require('mail/static/src/components/chatter_topbar/chatter_topbar.js'),
        Composer: require('mail/static/src/components/composer/composer.js'),
        ThreadView: require('mail/static/src/components/thread_view/thread_view.js'),
    }        
    });