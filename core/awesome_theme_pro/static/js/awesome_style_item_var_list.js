odoo.define('awesome_theme_pro.style_item_var_list', function (require) {
    "use strict";

    var ListRenderer = require('web.ListRenderer');
    var ListController = require('web.ListController');
    var ListView = require('web.ListView');
    var view_registry = require('web.view_registry');

    require('web.EditableListRenderer')

    var tmpRender = ListRenderer.extend({
        _renderRow: function (record, index) {
            var $row = this._super.apply(this, arguments);
            if (this.addTrashIcon) {
                var recordID = $row.data('id')
                var record = self._getRecord(recordID);
                //  if the record is deletable, then disable it
                if (record.data.is_default) {
                    var $lastTD = $row.find('td').last();
                    $lastTD.prop('disabled', true);
                }
            }
            return $row;
        },
    })
    var tmpController = ListController.extend({})

    var AwesometyleItemVarList = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Renderer: tmpRender,
            Controller: tmpController
        }),
        viewType: 'list'
    });

    view_registry.add('awesome_style_item_var_list', AwesometyleItemVarList);

    return AwesometyleItemVarList;
});
