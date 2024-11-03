odoo.define('equip3_sale_operation.FormRenderer', function (require) {
"use strict";

    var FormRenderer = require('web.FormRenderer');

    FormRenderer.include({
        confirmChange: function (state, id, fields, ev) {
            var self = this;
            return this._super.apply(this, arguments).then(function(result) {
                if (self.state !== undefined &&
                    self.state.model !== undefined &&
                    self.state.model === "sale.order" &&
                    fields !== undefined &&
                    fields.includes('brand') &&
                    self.state.data !== undefined &&
                    self.state.data.order_line !== undefined &&
                    self.state.data.order_line.data.length) {
                    var brand = self.state.data.brand;
                    _.each(self.state.data.order_line.data, function(line) {
                        var brand_ids = line.data['brand_ids'].res_ids;
                        if (!brand || (brand && brand.data !== undefined &&
                            !brand_ids.includes(brand.data.id))) {
                            $('tr[data-id="'+ line.id +'"]').find('.o_list_record_remove').click();
                        }
                    });
                }
            });
        },
    });

});