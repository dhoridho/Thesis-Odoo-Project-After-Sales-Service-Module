odoo.define('equip3_construction_hr_operation.list_editable_renderer', function (require) {
    "use strict";


    var ListRenderer = require('web.ListRenderer');

    ListRenderer.include({
        _renderRow: function (record) {
            var self = this;
            var $tr = this._super.apply(this, arguments);
            if (self.__parentedParent.model === 'hr.employee') {
                if (self.state.model === 'construction.project.information') {
                    if ($tr[0].lastChild.className === 'o_list_record_remove') {
                        if (record.data['is_updated'] === true) {
                            // console.log('record', record)
                            // console.log('check', $tr)
                            $tr[0].lastChild.style.display = 'none'
                        }
                    }
                }
            }
            return $tr;
        }
    })
})