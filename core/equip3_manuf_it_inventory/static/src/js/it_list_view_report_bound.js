odoo.define('equip3_manuf_it_inventory.ItListViewReportBound', function(require){
    'use strict';

    var viewRegistry = require('web.view_registry');
    var core = require('web.core');
    var QWeb = core.qweb;
    var ItListViewReport = require('equip3_manuf_it_inventory.ItListViewReport');


    var ListControllerReport = ItListViewReport.ListControllerReport.extend({

        events: _.extend({}, ItListViewReport.ListControllerReport.prototype.events, {
            'change .o_document_select': '_onDocumentChange'
        }),

        willStart: function(){
            var self = this;
            var docType;
            if (this.modelName === 'it.inbound.report'){
                docType = '20'
            } else {
                docType = '30'
            }
            var documentProm = this._rpc({
                model: 'ceisa.document.type',
                method: 'search_read',
                domain: [['code', '=', docType]],
                fields: ['id', 'code', 'name']
            }).then(function(result){
                var documentIds = [{id: false, code: '', name: ''}];
                for (var i=0; i < result.length; i++){
                    documentIds.push(result[i]);
                }
                self.documentIds = documentIds;
            });
            return Promise.all([this._super.apply(this, arguments), documentProm]);
        },

        start: function(){
            var self = this;
            return this._super.apply(this, arguments).then(function(){
                var state = self.model.get(self.handle);
                var context = state.getContext();

                self.documentId = self._getActiveDocument(context.document);

                var ItFilters = QWeb.render('ItFiltersDocument', {
                    documentId: self.documentId, 
                    documentIds: self.documentIds
                });
                self.$el.find('.o_cp_it_inventory').append(ItFilters);
            });
        },

        _getActiveDocument: function(documentId){
            for (var i=0; i < this.documentIds.length; i++){
                if (this.documentIds[i].id === documentId){
                    return this.documentIds[i];
                }
            }
            return false;
        },

        _updateFilters: function(key, value){
            var state = this.model.get(this.handle);
            var context = state.getContext();
            context[key] = value;
            var action = this.controlPanelProps.action;
            var domain = [
                ['warehouse_id', '=', context.warehouse ? context.warehouse : false],
                ['doc_type_id', '=', context.document ? context.document : false]
            ];
            if (context.date_from){
                domain.push(['date_done', '>=', context.date_from]);
            }
            if (context.date_to){
                domain.push(['date_done', '<=', context.date_to]);
            }
            return this.do_action({
                name: action.name,
                type: action.type,
                res_model: action.res_model,
                views: action._views,
                search_view_id: action.search_view_id,
                help: action.help,
                target: 'main',
                context: context,
                domain: domain
            }, function (err) {
                return Promise.reject(err);
            });
        },

        _onDocumentChange: function(ev){
            var $target = $(ev.target);
            var documentId = parseInt($target.val());
            if (isNaN(documentId)){
                documentId = false;
            }
            this.documentId = this._getActiveDocument(documentId);
            return this._updateFilters('document', documentId);
        },
    });

    var ListViewReport = ItListViewReport.ListViewReport.extend({
        config: _.extend({}, ItListViewReport.ListViewReport.prototype.config, {
            Controller: ListControllerReport
        }),
    });

    viewRegistry.add('it_list_view_report_bound', ListViewReport);

    return {
        ListControllerReport: ListControllerReport,
        ListViewReport: ListViewReport
    };
});