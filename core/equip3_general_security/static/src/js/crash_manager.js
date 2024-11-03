odoo.define('equip3_general_security.CrashManager', function (require) {
    "use strict";

    var Dialog = require('web.Dialog');
    
    var CrashManager = Dialog.include({

        init: function (parent, options, error) {
            this._super.apply(this, [parent, options, error]);
            var self = this;

            // Perform the RPC call to get the configuration value
            this._rpc({
                model: 'ir.config_parameter',
                method: 'get_hide_traceback',
                args: [], 
            }).then(function(configValue) {
                // Check the configValue and set the appropriate template
                if (configValue === true && self.template == 'CrashManager.error' ) {
                    self.template = 'CrashManager.errorNew';  // New template
                    self.renderElement();
                } 
                // Re-render the dialog with the new template
               
            });
        },
    });

    return {
        CrashManager: CrashManager
    };
});
