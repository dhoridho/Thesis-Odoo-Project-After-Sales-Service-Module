odoo.define('sh_activities_management.dashboard', function(require) {
    "use strict";
    
    var AbstractAction = require('web.AbstractAction');
	var ajax = require('web.ajax');
	var core = require('web.core');
	var rpc = require('web.rpc');
	var session = require('web.session');
	var web_client = require('web.web_client');
	var _t = core._t;
	var QWeb = core.qweb;
	var prev_selected_modal = '';
    var ActivityDashboardView = AbstractAction.extend({
        events: {
            'click .card_1': 'action_all_activities',
            'click .card_2': 'action_planned_activities',
            'click .card_4': 'action_overdue_activities',
            'click .card_3': 'action_completed_activities',
            'click .card_5': 'action_cancelled_activities',
            'click .popup-action-done':'action_feedback_done',
            'click  .mark-done': 'action_done',
            'click  .mark-cancel': 'action_cancel',
            'click  .mark-unarchive': 'action_unarchive',
            'click .mark-view': 'action_view',
            'click  .mark-edit': 'action_edit',
            'click .mark-origin': 'action_view_origin',
            'change #days': 'render_activity_tbl',
            'change #user_id': 'render_activity_tbl',
            'change #supervisor_id': 'render_activity_tbl',
            'change #start_date': 'render_activity_tbl',
            'change #end_date': 'render_activity_tbl',   
            'change #sh_document_model_id': 'render_activity_tbl',
            'change #sh_record_id': 'render_activity_tbl',   
            'change #activity_type_ids':'render_activity_tbl',
            "click .planned_page_number":'action_planned_paging',
            'click .planned_next_page':'action_planned_next_page',
            'click .planned_previous_page':'action_planned_previous_page',
            "click .all_page_number":'action_all_paging',
            'click .all_next_page':'action_all_next_page',
            'click .all_previous_page':'action_all_previous_page',
            "click .completed_page_number":'action_completed_paging',
            'click .completed_next_page':'action_completed_next_page',
            'click .completed_previous_page':'action_completed_previous_page',
            "click .overdue_page_number":'action_overdue_paging',
            'click .overdue_next_page':'action_overdue_next_page',
            'click .overdue_previous_page':'action_overdue_previous_page',
            "click .cancelled_page_number":'action_cancelled_paging',
            'click .cancelled_next_page':'action_cancelled_next_page',
            'click .cancelled_previous_page':'action_cancelled_previous_page',
        },
        init: function(parent, context) {
            this._super(parent, context);
            var crm_data = [];
            var res = ''
            var self = this;
            if (context.tag == 'activity_dashboard.dashboard') {
            	self._rpc({
                	model: 'activity.dashboard',
                    method: 'get_document_models',
                }).then(function (messagesData) {
                	$('#sh_document_model_ids > option').remove();
                	if (messagesData == false){
                		$('#sh_document_model_id').addClass('o_hidden');
                	}
                	else{
                		_.each(messagesData, function (data) {
                			$("#sh_document_model_ids").append('<option data-id="' + data.id + '" value="' + data.name + '">');
                    	});
                	}
                });
                self._rpc({
                	model: 'activity.dashboard',
                    method: 'sh_get_activity_types',
                }).then(function (messagesData) {
                	$('#activity_type_list > option').remove();
                		_.each(messagesData, function (data) {
                			$("#activity_type_list").append('<option data-id="' + data.id + '" value="' + data.name + '">');
                    	});
                });
					self._rpc({
                    	model: 'activity.dashboard',
                        method: 'get_user_list',
                    })
                    .then(function (messagesData) {
               	$('#sh_crm_db_supervisor_ids > option').remove();
               	$('#sh_crm_db_user_ids > option').remove();
               	session.user_has_group('sh_activities_management.group_activity_supervisor')
                    .then(function (has_group) {
                        if (has_group) {
                        	$('#user_id').removeClass("o_hidden");
                        }
                    });
                session.user_has_group('sh_activities_management.group_activity_manager')
                    .then(function (has_group) {
                        if (has_group) {
                            $('#supervisor_id').removeClass("o_hidden");
                            $('#user_id').removeClass("o_hidden");
                        }
                    });
                        _.each(messagesData, function (data) {
				               	$("#sh_crm_db_supervisor_ids").append('<option data-id="' + data.id + '" value="' + data.name + '">');
				               	$("#sh_crm_db_user_ids").append('<option data-id="' + data.id + '" value="' + data.name + '">');
                        });
                        self.render_activity_tbl();
                    });                   				
            }            
        },
        willStart: function() {
            return $.when(ajax.loadLibs(this), this._super());
            
        },
        start: function() {
            var self = this;
            self.render();
            return this._super();
        },

        render: function() {
            var self = this;
            var crm_dashboard = QWeb.render('activity_dashboard.dashboard', {
                widget: self,
            });
            $(crm_dashboard).prependTo(self.$el);
            return crm_dashboard
        },
        reload: function() {
            location.reload();

        },
        
        action_all_activities: function(event) {
            var self = this;
            var list_value = JSON.parse("[" + $("#all_activity").val() + "]");
            var comma_string = list_value.toString();
            var all_act = comma_string.split(",").map(Number);
  			event.stopPropagation();
            event.preventDefault();
            this._rpc({
                model: 'ir.model.data',
                method: 'xmlid_to_res_model_res_id',
                args: ["sh_activities_management.sh_mail_activity_view_form"],
            })
            .then(function (data) {
            	self.do_action({
                    name: _t("All Activities"),
                    type: 'ir.actions.act_window',
                    res_model: 'mail.activity',
                    view_mode: 'tree,form',
                    view_type: 'form',
                    views: [
                        [false, 'list'],
                        [data[1], 'form']
                    ],
                    domain: [
                        ['id', 'in', all_act],
                        '|',
                        ['active','=',false],
                        ['active','=',true],
                    ],
                    target: 'current'
                }, {

                })
            })
        },
		
		action_completed_activities: function(event) {
            var self = this;
            var list_value = JSON.parse("[" + $("#completed_activity").val() + "]");
            var comma_string = list_value.toString();
            var all_act = comma_string.split(",").map(Number);
  			event.stopPropagation();
            event.preventDefault();
            this._rpc({
                model: 'ir.model.data',
                method: 'xmlid_to_res_model_res_id',
                args: ["sh_activities_management.sh_mail_activity_view_form"],
            })
            .then(function (data) {
            	self.do_action({
                    name: _t("Completed Activities"),
                    type: 'ir.actions.act_window',
                    res_model: 'mail.activity',
                    view_mode: 'tree,form',
                    view_type: 'form',
                    views: [
                        [false, 'list'],
                        [data[1], 'form']
                    ],
                    domain: [
                        ['id', 'in', all_act],
                        '|',
                        ['active','=',false],
                        ['active','=',true],
                    ],
                    target: 'current'
                }, {

                })
            })
        },
        action_cancelled_activities: function(event) {
            var self = this;
            var all_act = [];
            var list_value = JSON.parse("[" + $("#cancel_activity").val() + "]");
            var comma_string = list_value.toString();
            var all_act = comma_string.split(",").map(Number);
  			event.stopPropagation();
            event.preventDefault();
            this._rpc({
                model: 'ir.model.data',
                method: 'xmlid_to_res_model_res_id',
                args: ["sh_activities_management.sh_mail_activity_view_form"],
            })
            .then(function (data) {
            	self.do_action({
                    name: _t("Cancelled Activities"),
                    type: 'ir.actions.act_window',
                    res_model: 'mail.activity',
                    view_mode: 'tree,form',
                    view_type: 'form',
                    views: [
                        [false, 'list'],
                        [data[1], 'form']
                    ],
                    domain: [
                        ['id', 'in', all_act],
                        '|',
                        ['active','=',false],
                        ['active','=',true],
                    ],
                    target: 'current'
                }, {

                })
            })
        },
		
		action_planned_activities: function(event) {
            var self = this;
            var all_act = [];
            var list_value = JSON.parse("[" + $("#planned_activity").val() + "]");
            var comma_string = list_value.toString();
            var all_act = comma_string.split(",").map(Number);
  			event.stopPropagation();
            event.preventDefault();
            this._rpc({
                model: 'ir.model.data',
                method: 'xmlid_to_res_model_res_id',
                args: ["sh_activities_management.sh_mail_activity_view_form"],
            })
            .then(function (data) {
            	self.do_action({
                    name: _t("Planned Activities"),
                    type: 'ir.actions.act_window',
                    res_model: 'mail.activity',
                    view_mode: 'tree,form',
                    view_type: 'form',
                    views: [
                        [false, 'list'],
                        [data[1], 'form']
                    ],
                    domain: [
                        ['id', 'in', all_act],
                    ],
                    target: 'current'
                }, {

                })
            })
        },
		
		action_overdue_activities: function(event) {
            var self = this;
            var list_value = JSON.parse("[" + $("#overdue_activity").val() + "]");
            var comma_string = list_value.toString();
            var all_act = comma_string.split(",").map(Number);
  			event.stopPropagation();
            event.preventDefault();
            this._rpc({
                model: 'ir.model.data',
                method: 'xmlid_to_res_model_res_id',
                args: ["sh_activities_management.sh_mail_activity_view_form"],
            })
            .then(function (data) {
            	self.do_action({
                    name: _t("Overdue Activities"),
                    type: 'ir.actions.act_window',
                    res_model: 'mail.activity',
                    view_mode: 'tree,form',
                    view_type: 'form',
                    views: [
                        [false, 'list'],
                        [data[1], 'form']
                    ],
                    domain: [
                        ['id', 'in', all_act],
                    ],
                    target: 'current'
                }, {

                })
            })
        },

        render_activity_tbl: function(event) {
        	var self = this;
            var date_option = $("#crm_days_filter_list").find("[value='" + $("#days").val() + "']");
			var filter_date = date_option.data("id");
			var user_option = $("#sh_crm_db_user_ids").find("[value='" + $("#user_id").val() + "']");
			var model_option = $("#sh_document_model_ids").find("[value='" + $("#sh_document_model_id").val() + "']");
			var filter_model = model_option.data("id");
            var type_option = $("#activity_type_list").find("[value='" + $("#activity_type_ids").val() + "']");
            var filter_type = type_option.data("id");
			var filter_user = user_option.data("id");
			var start_date = $('#start_date').val();
			var end_date = $('#end_date').val();
			var supervisor_option = $("#sh_crm_db_supervisor_ids").find("[value='" + $("#supervisor_id").val() + "']");
	        var filter_supervisor = supervisor_option.data("id");
			if (prev_selected_modal != filter_model){
				prev_selected_modal = filter_model;
				$('#sh_record_id').val('');
				$('#sh_record_ids > option').remove();
			}
			
			if (filter_date == 'custom')
		{
		 	$('#start_date_div').css("display", "block");
		 	$('#end_date_div').css("display", "block");
		}
		else
		{
			$('#start_date_div').css("display", "none");
		 	$('#end_date_div').css("display", "none");
		 	$('#start_date').val('');			
		 	$('#end_date').val('');
		}    
			//Planned Activity
			var current_page = 1;
			var record_option = $("#sh_record_ids").find("[value='" + $("#sh_record_id").val() + "']");
			var filter_record = record_option.data("id");
			if (filter_model != undefined){
				self._rpc({
	            	model: 'activity.dashboard',
	                method: 'get_document_model_records',
	                args: [filter_model],
	            }).then(function (messagesData) {
	            	if (messagesData == false){
	            		console.log("inside if");
	            		$('#sh_record_id').addClass('o_hidden');
	            	}
	            	else{
	            		$('#sh_record_ids > option').remove();
	            		$('#sh_record_id').removeClass('o_hidden');
	            		_.each(messagesData, function (data) {
	            			$("#sh_record_ids").append('<option data-id="' + data.id + '" value="' + data.name + '">');
	                	});
	            	}
	            });
			}
			else{
				if(filter_model == undefined){
					$('#sh_record_ids > option').remove();
					$('#sh_record_id').addClass('o_hidden');
				}
			}
					self._rpc({
                    	model: 'activity.dashboard',
                        method: 'get_sh_crm_activity_todo_tbl',
     					args: [filter_date, filter_user,start_date,end_date,filter_supervisor,current_page,filter_model,filter_record,filter_type],                        
                        
                    })
                    .then(function (messagesData) {
					$("#js_id_sh_crm_activity_todo_tbl_div").replaceWith( messagesData );
                        				
                    });             				
				
			//All Activity
					self._rpc({
                    	model: 'activity.dashboard',
                        method: 'get_sh_crm_activity_all_tbl',
     					args: [filter_date, filter_user,start_date,end_date,filter_supervisor,current_page,filter_model,filter_record,filter_type],                        
                        
                    })
                    .then(function (messagesData) {
					$("#js_id_sh_crm_activity_all_tbl_div").replaceWith( messagesData );
                        				
                    });
                    
                    
            //Completed Activity
					self._rpc({
                    	model: 'activity.dashboard',
                        method: 'get_sh_crm_activity_completed_tbl',
     					args: [filter_date, filter_user,start_date,end_date,filter_supervisor,current_page,filter_model,filter_record,filter_type],                        
                        
                    })
                    .then(function (messagesData) {
					$("#js_id_sh_crm_activity_completed_tbl_div").replaceWith( messagesData );
                        				
                    });
                    
            //Overdue Activity
					self._rpc({
                    	model: 'activity.dashboard',
                        method: 'get_sh_crm_activity_overdue_tbl',
     					args: [filter_date, filter_user,start_date,end_date,filter_supervisor,current_page,filter_model,filter_record,filter_type],                        
                        
                    })
                    .then(function (messagesData) {
					$("#js_id_sh_crm_activity_overdue_tbl_div").replaceWith( messagesData );
                        				
                    });
			//cancelled activity
					this._rpc({
                    	model: 'activity.dashboard',
                        method: 'get_sh_crm_activity_cancelled_tbl',
     					args: [filter_date, filter_user,start_date,end_date,filter_supervisor,current_page,filter_model,filter_record,filter_type],                        
                        
                    })
                    .then(function (messagesData) {
					$("#js_id_sh_crm_activity_cancelled_tbl_div").replaceWith( messagesData );
                        				
                    });
            //activity counts
				self._rpc({
                    	model: 'activity.dashboard',
                        method: 'get_sh_crm_activity_planned_count_tbl',
     					args: [filter_date, filter_user,start_date,end_date,filter_supervisor,filter_model,filter_record,filter_type],                        
                        
                    })
                    .then(function (messagesData) {
					$("#js_id_sh_crm_activity_all_count_tbl_div").replaceWith( messagesData );
                        				
                    });
            
        },

        action_done: function(e) {
        	var $el = $(e.target).parents('tr').find("#h_v").attr("value")
            var activity_id = parseInt($el)
            $('#popup_activity_id').val(activity_id);
        	$('#activity_feedback').val('');
        	$('.modal').modal('show');
        },
        
        action_feedback_done: function(e) {
        	var self = this;
        	var str_activity_id = $('#popup_activity_id').val();
        	var activity_id = parseInt(str_activity_id);
          var today = new moment().utc().format();
          event.stopPropagation();
          event.preventDefault();
          this._rpc({
              model: 'mail.activity',
              method: 'action_done_from_popup',
              args: [activity_id,$('#activity_feedback').val()],
          }).then(function(data) {
        	  self.render_activity_tbl();
        	  $(".modal").modal('hide');
          });
        },
        
        action_cancel: function(e) {
        	var self = this;
        	var $el = $(e.target).parents('tr').find("#h_v").attr("value")
            var activity_id = parseInt($el)
          var today = new moment().utc().format();
          event.stopPropagation();
          event.preventDefault();
          this._rpc({
              model: 'mail.activity',
              method: 'action_cancel',
              args: [activity_id],
          }).then(function(data) {
        	  self.render_activity_tbl();
          });
        },
        action_unarchive: function(e) {
        	var self = this;
        	var $el = $(e.target).parents('tr').find("#h_v").attr("value")
            var activity_id = parseInt($el)
          var today = new moment().utc().format();
          event.stopPropagation();
          event.preventDefault();
          this._rpc({
              model: 'mail.activity',
              method: 'unarchive',
              args: [activity_id,true],
          }).then(function(data) {
        	  self.render_activity_tbl();
          });
        },
        action_view: function(e) {
            var self = this;
            var today = new moment().utc().format();
            event.stopPropagation();
            event.preventDefault();
            var $el = $(e.target).parents('tr').find("#h_v").attr("value")
            var activity_id = parseInt($el)
            this._rpc({
                model: 'ir.model.data',
                method: 'xmlid_to_res_model_res_id',
                args: ["sh_activities_management.sh_mail_activity_view_form"],
            })
            .then(function (data) {
            	self.do_action({
                    name: _t("Activity"),
                    type: 'ir.actions.act_window',
                    res_model: 'mail.activity',
                    view_mode: 'tree,form',
                    view_type: 'form',
                    views: [
                        [false, 'list'],
                        [data[1], 'form']
                    ],
                    domain: [
                        ['id', '=',activity_id ],
                        '|',
                        ['active', '=',true ],
                        ['active', '=',false ],
                    ],
                    target: 'current'
                }, {

                })
            })
        },
        action_edit: function (e) {
            var self = this;
            var today = new moment().utc().format();
            event.stopPropagation();
            event.preventDefault();
            var $el = $(e.target).parents("tr").find("#h_v").attr("value");
            var activity_id = parseInt($el);
            this._rpc({
                model: "ir.model.data",
                method: "xmlid_to_res_model_res_id",
                args: ["sh_activities_management.sh_mail_activity_type_view_form_inherit"],
            }).then(function (data) {
                self.do_action(
                    {
                        name: _t("Activity"),
                        type: "ir.actions.act_window",
                        res_model: "mail.activity",
                        res_id:activity_id,
                        views: [
                        	[data[1], "form"],
                            [false, "list"],
                        ],
                        domain: [["id", "=", activity_id]],
                        target: "new",
                    },
                    {}
                );
            });
        },
        action_planned_paging: function(ev) {
        	var self = this;
        	ev.stopPropagation();
        	var current_page = $(ev.currentTarget).find(".planned_current_page_value").attr("data-value")
        	var filter_date = $("#crm_days_filter_list").children("option:selected").val();
            var filter_user = $("#sh_crm_db_user_id").children("option:selected").val();
            var filter_supervisor = $("#sh_crm_db_supervisor_id").children("option:selected").val();
            var filter_model = $('#sh_document_model_id').children("option:selected").val();
            var filter_record = $('#sh_record_id').children("option:selected").val();
            var type_option = $("#activity_type_list").find("[value='" + $("#activity_type_ids").val() + "']");
            console.log("....................type_option...........",type_option);
            var filter_type = type_option.data("id");
            console.log("....................filter_type...........",filter_type);
            var start_date = $("#start_date").val();
            var end_date = $("#end_date").val();
            this._rpc({
                model: "activity.dashboard",
                method: "get_sh_crm_activity_todo_tbl",
                args: [filter_date, filter_user, start_date, end_date, filter_supervisor,current_page,filter_model,filter_record,filter_type],
            }).then(function (messagesData) {
                $("#js_id_sh_crm_activity_todo_tbl_div").replaceWith(messagesData);
            });
        },
        action_planned_next_page: function(ev) {
        	var self = this;
        	ev.stopPropagation();
        	var current_page = parseInt($(ev.currentTarget).attr("data-planned-current-page")) + 1;
        	var filter_date = $("#crm_days_filter_list").children("option:selected").val();
            var filter_user = $("#sh_crm_db_user_id").children("option:selected").val();
            var filter_supervisor = $("#sh_crm_db_supervisor_id").children("option:selected").val();
            var filter_model = $('#sh_document_model_id').children("option:selected").val();
            var filter_record = $('#sh_record_id').children("option:selected").val();
            var type_option = $("#activity_type_list").find("[value='" + $("#activity_type_ids").val() + "']");
            var filter_type = type_option.data("id");
            var start_date = $("#start_date").val();
            var end_date = $("#end_date").val();
			this._rpc({
                model: "activity.dashboard",
                method: "get_sh_crm_activity_todo_tbl",
                args: [filter_date, filter_user, start_date, end_date, filter_supervisor,current_page,filter_model,filter_record,filter_type],
            }).then(function (messagesData) {
                $("#js_id_sh_crm_activity_todo_tbl_div").replaceWith(messagesData);
            });
        },
        action_planned_previous_page: function(ev) {
        	var self = this;
        	ev.stopPropagation();
        	var current_page = parseInt($(ev.currentTarget).attr("data-planned-previous-page")) - 1;
        	var filter_date = $("#crm_days_filter_list").children("option:selected").val();
            var filter_user = $("#sh_crm_db_user_id").children("option:selected").val();
            var filter_supervisor = $("#sh_crm_db_supervisor_id").children("option:selected").val();
            var filter_model = $('#sh_document_model_id').children("option:selected").val();
            var filter_record = $('#sh_record_id').children("option:selected").val();
            var type_option = $("#activity_type_list").find("[value='" + $("#activity_type_ids").val() + "']");
            var filter_type = type_option.data("id");
            var start_date = $("#start_date").val();
            var end_date = $("#end_date").val();
            this._rpc({
                model: "activity.dashboard",
                method: "get_sh_crm_activity_todo_tbl",
                args: [filter_date, filter_user, start_date, end_date, filter_supervisor,current_page,filter_model,filter_record,filter_type],
            }).then(function (messagesData) {
                $("#js_id_sh_crm_activity_todo_tbl_div").replaceWith(messagesData);
            });
        },
        action_all_paging: function(ev) {
        	var self = this;
        	ev.stopPropagation();
        	var current_page = $(ev.currentTarget).find(".all_current_page_value").attr("data-value")
        	var filter_date = $("#crm_days_filter_list").children("option:selected").val();
            var filter_user = $("#sh_crm_db_user_id").children("option:selected").val();
            var filter_supervisor = $("#sh_crm_db_supervisor_id").children("option:selected").val();
            var filter_model = $('#sh_document_model_id').children("option:selected").val();
            var filter_record = $('#sh_record_id').children("option:selected").val();
            var type_option = $("#activity_type_list").find("[value='" + $("#activity_type_ids").val() + "']");
            var filter_type = type_option.data("id");
            var start_date = $("#start_date").val();
            var end_date = $("#end_date").val();
            this._rpc({
                model: "activity.dashboard",
                method: "get_sh_crm_activity_all_tbl",
                args: [filter_date, filter_user, start_date, end_date, filter_supervisor,current_page,filter_model,filter_record,filter_type],
            }).then(function (messagesData) {
                $("#js_id_sh_crm_activity_all_tbl_div").replaceWith(messagesData);
            });
        },
        action_all_next_page: function(ev) {
        	var self = this;
        	ev.stopPropagation();
        	var current_page = parseInt($(ev.currentTarget).attr("data-all-current-page")) + 1;
        	var filter_date = $("#crm_days_filter_list").children("option:selected").val();
            var filter_user = $("#sh_crm_db_user_id").children("option:selected").val();
            var filter_supervisor = $("#sh_crm_db_supervisor_id").children("option:selected").val();
            var filter_model = $('#sh_document_model_id').children("option:selected").val();
            var filter_record = $('#sh_record_id').children("option:selected").val();
            var type_option = $("#activity_type_list").find("[value='" + $("#activity_type_ids").val() + "']");
            var filter_type = type_option.data("id");
            var start_date = $("#start_date").val();
            var end_date = $("#end_date").val();
            this._rpc({
                model: "activity.dashboard",
                method: "get_sh_crm_activity_all_tbl",
                args: [filter_date, filter_user, start_date, end_date, filter_supervisor,current_page,filter_model,filter_record,filter_type],
            }).then(function (messagesData) {
                $("#js_id_sh_crm_activity_all_tbl_div").replaceWith(messagesData);
            });
        },
        action_all_previous_page: function(ev) {
        	var self = this;
        	ev.stopPropagation();
        	var current_page = parseInt($(ev.currentTarget).attr("data-all-previous-page")) - 1;
        	var filter_date = $("#crm_days_filter_list").children("option:selected").val();
            var filter_user = $("#sh_crm_db_user_id").children("option:selected").val();
            var filter_supervisor = $("#sh_crm_db_supervisor_id").children("option:selected").val();
            var filter_model = $('#sh_document_model_id').children("option:selected").val();
            var filter_record = $('#sh_record_id').children("option:selected").val();
            var type_option = $("#activity_type_list").find("[value='" + $("#activity_type_ids").val() + "']");
            var filter_type = type_option.data("id");
            var start_date = $("#start_date").val();
            var end_date = $("#end_date").val();
            this._rpc({
                model: "activity.dashboard",
                method: "get_sh_crm_activity_all_tbl",
                args: [filter_date, filter_user, start_date, end_date, filter_supervisor,current_page,filter_model,filter_record,filter_type],
            }).then(function (messagesData) {
                $("#js_id_sh_crm_activity_all_tbl_div").replaceWith(messagesData);
            });
        },
        action_completed_paging: function(ev) {
        	var self = this;
        	ev.stopPropagation();
        	var current_page = $(ev.currentTarget).find(".completed_current_page_value").attr("data-value")
        	var filter_date = $("#crm_days_filter_list").children("option:selected").val();
            var filter_user = $("#sh_crm_db_user_id").children("option:selected").val();
            var filter_supervisor = $("#sh_crm_db_supervisor_id").children("option:selected").val();
            var filter_model = $('#sh_document_model_id').children("option:selected").val();
            var filter_record = $('#sh_record_id').children("option:selected").val();
            var type_option = $("#activity_type_list").find("[value='" + $("#activity_type_ids").val() + "']");
            var filter_type = type_option.data("id");
            var start_date = $("#start_date").val();
            var end_date = $("#end_date").val();
            this._rpc({
                model: "activity.dashboard",
                method: "get_sh_crm_activity_completed_tbl",
                args: [filter_date, filter_user, start_date, end_date, filter_supervisor,current_page,filter_model,filter_record,filter_type],
            }).then(function (messagesData) {
                $("#js_id_sh_crm_activity_completed_tbl_div").replaceWith(messagesData);
            });
        },
        action_completed_next_page: function(ev) {
        	var self = this;
        	ev.stopPropagation();
        	var current_page = parseInt($(ev.currentTarget).attr("data-completed-current-page")) + 1;
        	var filter_date = $("#crm_days_filter_list").children("option:selected").val();
            var filter_user = $("#sh_crm_db_user_id").children("option:selected").val();
            var filter_supervisor = $("#sh_crm_db_supervisor_id").children("option:selected").val();
            var filter_model = $('#sh_document_model_id').children("option:selected").val();
            var filter_record = $('#sh_record_id').children("option:selected").val();
            var type_option = $("#activity_type_list").find("[value='" + $("#activity_type_ids").val() + "']");
            var filter_type = type_option.data("id");
            var start_date = $("#start_date").val();
            var end_date = $("#end_date").val();
            this._rpc({
                model: "activity.dashboard",
                method: "get_sh_crm_activity_completed_tbl",
                args: [filter_date, filter_user, start_date, end_date, filter_supervisor,current_page,filter_model,filter_record,filter_type],
            }).then(function (messagesData) {
                $("#js_id_sh_crm_activity_completed_tbl_div").replaceWith(messagesData);
            });
        },
        action_completed_previous_page: function(ev) {
        	var self = this;
        	ev.stopPropagation();
        	var current_page = parseInt($(ev.currentTarget).attr("data-completed-previous-page")) - 1;
        	var filter_date = $("#crm_days_filter_list").children("option:selected").val();
            var filter_user = $("#sh_crm_db_user_id").children("option:selected").val();
            var filter_supervisor = $("#sh_crm_db_supervisor_id").children("option:selected").val();
            var filter_model = $('#sh_document_model_id').children("option:selected").val();
            var filter_record = $('#sh_record_id').children("option:selected").val();
            var type_option = $("#activity_type_list").find("[value='" + $("#activity_type_ids").val() + "']");
            var filter_type = type_option.data("id");
            var start_date = $("#start_date").val();
            var end_date = $("#end_date").val();
            this._rpc({
                model: "activity.dashboard",
                method: "get_sh_crm_activity_completed_tbl",
                args: [filter_date, filter_user, start_date, end_date, filter_supervisor,current_page,filter_model,filter_record,filter_type],
            }).then(function (messagesData) {
                $("#js_id_sh_crm_activity_completed_tbl_div").replaceWith(messagesData);
            });
        },
        action_overdue_paging: function(ev) {
        	var self = this;
        	ev.stopPropagation();
        	var current_page = $(ev.currentTarget).find(".overdue_current_page_value").attr("data-value")
        	var filter_date = $("#crm_days_filter_list").children("option:selected").val();
            var filter_user = $("#sh_crm_db_user_id").children("option:selected").val();
            var filter_supervisor = $("#sh_crm_db_supervisor_id").children("option:selected").val();
            var filter_model = $('#sh_document_model_id').children("option:selected").val();
            var filter_record = $('#sh_record_id').children("option:selected").val();
            var type_option = $("#activity_type_list").find("[value='" + $("#activity_type_ids").val() + "']");
            var filter_type = type_option.data("id");
            var start_date = $("#start_date").val();
            var end_date = $("#end_date").val();
            this._rpc({
                model: "activity.dashboard",
                method: "get_sh_crm_activity_overdue_tbl",
                args: [filter_date, filter_user, start_date, end_date, filter_supervisor,current_page,filter_model,filter_record,filter_type],
            }).then(function (messagesData) {
                $("#js_id_sh_crm_activity_overdue_tbl_div").replaceWith(messagesData);
            });
        },
        action_overdue_next_page: function(ev) {
        	var self = this;
        	ev.stopPropagation();
        	var current_page = parseInt($(ev.currentTarget).attr("data-overdue-current-page")) + 1;
        	var filter_date = $("#crm_days_filter_list").children("option:selected").val();
            var filter_user = $("#sh_crm_db_user_id").children("option:selected").val();
            var filter_supervisor = $("#sh_crm_db_supervisor_id").children("option:selected").val();
            var filter_model = $('#sh_document_model_id').children("option:selected").val();
            var filter_record = $('#sh_record_id').children("option:selected").val();
            var type_option = $("#activity_type_list").find("[value='" + $("#activity_type_ids").val() + "']");
            var filter_type = type_option.data("id");
            var start_date = $("#start_date").val();
            var end_date = $("#end_date").val();
            this._rpc({
                model: "activity.dashboard",
                method: "get_sh_crm_activity_overdue_tbl",
                args: [filter_date, filter_user, start_date, end_date, filter_supervisor,current_page,filter_model,filter_record,filter_type],
            }).then(function (messagesData) {
                $("#js_id_sh_crm_activity_overdue_tbl_div").replaceWith(messagesData);
            });
        },
        action_overdue_previous_page: function(ev) {
        	var self = this;
        	ev.stopPropagation();
        	var current_page = parseInt($(ev.currentTarget).attr("data-overdue-previous-page")) - 1;
        	var filter_date = $("#crm_days_filter_list").children("option:selected").val();
            var filter_user = $("#sh_crm_db_user_id").children("option:selected").val();
            var filter_supervisor = $("#sh_crm_db_supervisor_id").children("option:selected").val();
            var filter_model = $('#sh_document_model_id').children("option:selected").val();
            var filter_record = $('#sh_record_id').children("option:selected").val();
            var type_option = $("#activity_type_list").find("[value='" + $("#activity_type_ids").val() + "']");
            var filter_type = type_option.data("id");
            var start_date = $("#start_date").val();
            var end_date = $("#end_date").val();
            this._rpc({
                model: "activity.dashboard",
                method: "get_sh_crm_activity_overdue_tbl",
                args: [filter_date, filter_user, start_date, end_date, filter_supervisor,current_page,filter_model,filter_record,filter_type],
            }).then(function (messagesData) {
                $("#js_id_sh_crm_activity_overdue_tbl_div").replaceWith(messagesData);
            });
        },
        action_cancelled_paging: function(ev) {
        	var self = this;
        	ev.stopPropagation();
        	var current_page = $(ev.currentTarget).find(".cancelled_current_page_value").attr("data-value")
        	var filter_date = $("#crm_days_filter_list").children("option:selected").val();
            var filter_user = $("#sh_crm_db_user_id").children("option:selected").val();
            var filter_supervisor = $("#sh_crm_db_supervisor_id").children("option:selected").val();
            var filter_model = $('#sh_document_model_id').children("option:selected").val();
            var filter_record = $('#sh_record_id').children("option:selected").val();
            var type_option = $("#activity_type_list").find("[value='" + $("#activity_type_ids").val() + "']");
            var filter_type = type_option.data("id");
            var start_date = $("#start_date").val();
            var end_date = $("#end_date").val();
            this._rpc({
                model: "activity.dashboard",
                method: "get_sh_crm_activity_cancelled_tbl",
                args: [filter_date, filter_user, start_date, end_date, filter_supervisor,current_page,filter_model,filter_record,filter_type],
            }).then(function (messagesData) {
                $("#js_id_sh_crm_activity_cancelled_tbl_div").replaceWith(messagesData);
            });
        },
        action_cancelled_next_page: function(ev) {
        	var self = this;
        	ev.stopPropagation();
        	var current_page = parseInt($(ev.currentTarget).attr("data-cancelled-current-page")) + 1;
        	var filter_date = $("#crm_days_filter_list").children("option:selected").val();
            var filter_user = $("#sh_crm_db_user_id").children("option:selected").val();
            var filter_supervisor = $("#sh_crm_db_supervisor_id").children("option:selected").val();
            var filter_model = $('#sh_document_model_id').children("option:selected").val();
            var filter_record = $('#sh_record_id').children("option:selected").val();
            var type_option = $("#activity_type_list").find("[value='" + $("#activity_type_ids").val() + "']");
            var filter_type = type_option.data("id");
            var start_date = $("#start_date").val();
            var end_date = $("#end_date").val();
            this._rpc({
                model: "activity.dashboard",
                method: "get_sh_crm_activity_cancelled_tbl",
                args: [filter_date, filter_user, start_date, end_date, filter_supervisor,current_page,filter_model,filter_record,filter_type],
            }).then(function (messagesData) {
                $("#js_id_sh_crm_activity_cancelled_tbl_div").replaceWith(messagesData);
            });
        },
        action_cancelled_previous_page: function(ev) {
        	var self = this;
        	ev.stopPropagation();
        	var current_page = parseInt($(ev.currentTarget).attr("data-cancelled-previous-page")) - 1;
        	var filter_date = $("#crm_days_filter_list").children("option:selected").val();
            var filter_user = $("#sh_crm_db_user_id").children("option:selected").val();
            var filter_supervisor = $("#sh_crm_db_supervisor_id").children("option:selected").val();
            var filter_model = $('#sh_document_model_id').children("option:selected").val();
            var filter_record = $('#sh_record_id').children("option:selected").val();
            var type_option = $("#activity_type_list").find("[value='" + $("#activity_type_ids").val() + "']");
            var filter_type = type_option.data("id");
            var start_date = $("#start_date").val();
            var end_date = $("#end_date").val();
            this._rpc({
                model: "activity.dashboard",
                method: "get_sh_crm_activity_cancelled_tbl",
                args: [filter_date, filter_user, start_date, end_date, filter_supervisor,current_page,filter_model,filter_record,filter_type],
            }).then(function (messagesData) {
                $("#js_id_sh_crm_activity_cancelled_tbl_div").replaceWith(messagesData);
            });
        },
        
        
        action_view_origin: function(e) {
        	var self = this;
            var today = new moment().utc().format();
            event.stopPropagation();
            event.preventDefault();
            var $el = $(e.target).parents('tr').find("#h_v").attr("value")
            var activity_id = parseInt($el)
            this._rpc({
                model: 'mail.activity',
                method: 'action_view_activity',
                args: [activity_id],
            }).then(function (data) {
            	self.do_action({
                    name: _t("Origin Activity"),
                    type: 'ir.actions.act_window',
                    res_model: data.res_model,
                    res_id: data.res_id,
                    view_type:'form',
                    view_mode: 'form',
                    views: [
                        [false, 'form'],
                        [false, 'list']
                    ],
                    target: 'current'
                }, {

                })
            })
        },

    });
    core.action_registry.add('activity_dashboard.dashboard', ActivityDashboardView);
    return ActivityDashboardView

});