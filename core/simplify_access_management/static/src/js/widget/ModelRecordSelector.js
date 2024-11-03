odoo.define("advanced_web_domain_widget.ModelRecordSelectorAh", function (require) {
    "use strict";

    var TerabitsRecordSelector = require("advanced_web_domain_widget.ModelRecordSelector");
    
    TerabitsRecordSelector.include({
        _getModelRecordsFromCache: function (model, filters) {
             ;
            var def = undefined
            if (!def) {
                 ;
                var def = this._rpc({
                    model: model,
                    method: 'search_read',
                    kwargs: {
                        domain: [],
                        fields: ['id', 'display_name'],
                    },
                }).then((function (data) {
                    if (data) {
                        this.records = data
                    }
                    if(model == 'res.users'){
                        this.records.push({'id': 0, 'display_name': 'Environment User'})
                    }
                    if(model == 'res.company'){
                        this.records.push({'id': 0, 'display_name': 'Environment Company'})
                    }

                }).bind(this));
            }
            return def.then((function (data) {
            }).bind(this));
        },
    });
});