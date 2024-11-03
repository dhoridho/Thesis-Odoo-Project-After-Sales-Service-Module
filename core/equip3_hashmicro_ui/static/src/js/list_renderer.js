odoo.define('equip3_hashmicro_ui.ListRenderer', function (require) {
    "use strict";

    var ListRenderer = require('web.ListRenderer');

    var DECORATIONS = [
        'decoration-bf',
        'decoration-it',
        'decoration-danger',
        'decoration-info',
        'decoration-muted',
        'decoration-primary',
        'decoration-success',
        'decoration-warning',
        'decoration-danger2',
        'decoration-danger3',
        'decoration-primary2',
        'decoration-primary3',
        'decoration-success2',
        'decoration-success3',
        'decoration-warning2',
        'decoration-warning3',
    ];

    ListRenderer.include({
        init: function (parent, state, params) {
            this._super.apply(this, arguments);
            this.rowDecorations = _.chain(this.arch.attrs)
                .pick(function (value, key) {
                    return DECORATIONS.indexOf(key) >= 0;
                }).mapObject(function (value) {
                    return py.parse(py.tokenize(value));
                }).value();
        },

        _renderView: function() {
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                var $table = self.$('table');
                if ($table){
                    var $optionalColumnToggle = $table.find('i.fa-ellipsis-v');
                    if ($optionalColumnToggle){
                        $optionalColumnToggle.removeClass('fa fa-ellipsis-v');
                        $optionalColumnToggle.addClass('o-hm2-drop_list');
                    }
                }
                if (self.getParent() !== undefined &&
                    self.getParent().getParent() !== undefined &&
                    self.getParent().getParent().getParent() !== undefined &&
                    self.getParent().getParent().getParent().menu !== undefined &&
                    self.state !== undefined && self.state.data !== undefined) {
                    var menu = self.getParent().getParent().getParent().menu;
                    var lastrecordID = menu.lastrecordID;
                    if (lastrecordID !== undefined && lastrecordID !== '') {
                        var record = self.state.data.filter(k => k.res_id == parseInt(lastrecordID));
                        if (record && record.length) {
                            var row = self.$el.find('tr.o_data_row[data-id="' + record[0].id + '"]');
                            if (row && row.length) {
                                setTimeout(
                                function() {
                                    menu.lastrecordID = '';
                                    row.click();
                                }, 1000)
                            }
                        }
                    }
                }
            });
        }
    });
});