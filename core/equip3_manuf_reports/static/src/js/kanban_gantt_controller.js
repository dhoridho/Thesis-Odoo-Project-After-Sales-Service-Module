odoo.define('equip3_manuf_reports.kanban_gantt_controller', function (require) {
    
    var core = require('web.core');
    var KsGanttController = require('ks_gantt_view.Controller');

    KsGanttController.include({
        start: async function () {
            const promises = [this._super()];
            this.reload()
            await Promise.all(promises);
        },
    });

})