odoo.define('equip3_hashmicro_ui.KanbanRenderer', function (require) {
    "use strict";

    var KanbanRenderer = require('web.KanbanRenderer');

    KanbanRenderer.include({
        _renderView: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                if (self.getParent() !== undefined &&
                    self.getParent().getParent() !== undefined &&
                    self.getParent().getParent().getParent() !== undefined &&
                    self.getParent().getParent().getParent().menu !== undefined &&
                    self.state !== undefined && self.state.data !== undefined) {
                    var menu = self.getParent().getParent().getParent().menu;
                    var lastrecordID = menu.lastrecordID;
                    if (lastrecordID !== undefined && lastrecordID !== '') {
                        menu.lastrecordID = '';
                    }
                }
            })
        },
    })
});