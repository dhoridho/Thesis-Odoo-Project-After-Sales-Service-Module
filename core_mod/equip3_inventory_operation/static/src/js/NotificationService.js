odoo.define("equip3_inventory_operation.NotificationService", function (require) {
    "use strict";

    var NotificationService = require('web.NotificationService');

    NotificationService.include({
        notify: function (params) {
            let deleteMark = false;
            if (params.message){
                var notifyOnce = params.message.match("NOTIFY_ONCE_");
                if (notifyOnce) {
                    var $mark = $('body').find('.mark_barcode_change');
                    if (!$mark.length){
                        return;
                    }
                    params.message = params.message.replace("NOTIFY_ONCE_", "");
                    deleteMark = true;
                }
            }
            var res = this._super.apply(this, arguments);

            if (deleteMark){
                $('body').find('.mark_barcode_change').remove();
            }

            return res;
        },
    });

});