odoo.define('equip3_manuf_masterdata.DynamicO2MUnlink', function (require) {
"use strict";

var ListRenderer = require('web.ListRenderer');

ListRenderer.include({
    _renderRow: function (record, index) {
        var $row = this._super.apply(this, arguments);
        if (this.addTrashIcon && 'trash-icon' in this.arch.attrs){
            var condition = this.arch.attrs['trash-icon'].replace('$', 'record.data.');
            var conditionMeet = eval(condition);
            if (!conditionMeet){
                $row.children('td.o_list_record_remove').replaceWith('<td/>');
            }
        }
        return $row;
    },
});
});