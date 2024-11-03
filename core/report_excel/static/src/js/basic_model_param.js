odoo.define('report_excel.BasicModelParam', function (require) {
"use strict";

var BasicModel = require('web.BasicModel');
var Domain = require('report_excel.DomainParam');
var type_mapping = {
	    "char": "",
	    "integer": 0,
	    "float": 0.0,
	    "many2one": "",
	    "many2many": "",
	    "date": "2000-01-01",
	    "datetime": "2000-01-01 12:39:55",
	    "boolean": false,
	};
BasicModel.include({
	_fetchSpecialDomainParam: function (record, fieldName, fieldInfo) {
		var self = this;
        var context = record.getContext({fieldName: fieldName});
        var domainModel = fieldInfo.options.model;
        if (record.data.hasOwnProperty(domainModel)) {
            domainModel = record._changes && record._changes[domainModel] || record.data[domainModel];
        }
        var domainValue = record._changes && record._changes[fieldName] || record.data[fieldName] || [];
        var evalContextParam = this._getEvalContext(record);
        var domainValueArr = [Domain.prototype.stringToArray(domainValue, evalContextParam)];
        var params_arr_all = new Array();
        var params_all =  ("" + evalContextParam.report_excel_param_content).split(';');
        var i_split = ''
    	var n = 0
    	for (var i = 1 ; i < params_all.length ; i++) {
    		i_split = ("" + params_all[i-1]).split(',');
        	params_arr_all[i-1] = i_split
        }	                
        for (var i = 1 ; i <= domainValueArr[0].length ; i++) {
    		if (domainValueArr[0][i-1] instanceof Array){
    			var value_split = ("" + domainValueArr[0][i-1][2]).split(/\(([^)]+)\)/);
    			var param = value_split[0] === 'param' ? true : false;
    			if (param){
    				for (var k in params_arr_all) {
    					if ( params_arr_all[k][0] == domainValueArr[0][i-1][2]) {
    						domainValueArr[0][i-1][1] = "=";
    						domainValueArr[0][i-1][2] = type_mapping[params_arr_all[k][2]];
    					}
    				}
    			}
		   }
	   }
        var domainValueParam = Domain.prototype.arrayToString(domainValueArr[0]);
        var hasChanged = this._saveSpecialDataCache(record, fieldName, {
        	context: context,
        	domainModel: domainModel,
        	domainValue: domainValueParam,
        });
        if (!hasChanged) {
            return Promise.resolve();
        } else if (!domainModel) {
            return Promise.resolve({
                model: domainModel,
                nbRecords: 0,
            });
        }
        return new Promise(function (resolve) {
            var evalContext = self._getEvalContext(record);
            self._rpc({
                model: domainModel,
                method: 'search_count',
                args: [Domain.prototype.stringToArray(domainValueParam, evalContext)],                
                context: context
            })
            .then(function (nbRecords) {
                resolve({
                    model: domainModel,
                    nbRecords: nbRecords,
                });
            })
            .guardedCatch(function (reason) {
                var e = reason.event;
                e.preventDefault(); 
                resolve({
                    model: domainModel,
                    nbRecords: 0,
                });
            });
        });
    },	
    _fetchSpecialData: function (record, options) {
        var self = this;
        var specialFieldNames = [];
        var fieldNames = (options && options.fieldNames) || record.getFieldNames();
    	if (record && record.model && record.model === "report.excel.section" && fieldNames.indexOf( 'domain' ) == -1 ) {
        	fieldNames.push( 'domain' )
        }
        return Promise.all(_.map(fieldNames, function (name) {
            var viewType = (options && options.viewType) || record.viewType;
            var fieldInfo = record.fieldsInfo[viewType][name] || {};
            var Widget = fieldInfo.Widget;
            if (Widget && Widget.prototype.specialData) {
                return self[Widget.prototype.specialData](record, name, fieldInfo).then(function (data) {
                    if (data === undefined) {
                        return;
                    }
                    record.specialData[name] = data;
                    specialFieldNames.push(name);
                });
            }
        })).then(function () {
            return specialFieldNames;
        });
    },    
  });
});
