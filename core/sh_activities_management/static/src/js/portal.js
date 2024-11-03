odoo.define("sh_activities_management.activity", function (require) {
    "use strict";    
    var publicWidget = require("web.public.widget");
    var core = require("web.core");
    var qweb = core.qweb;
    var _t = core._t;
    var rpc = require("web.rpc");
    var Dialog = require("web.Dialog");
    publicWidget.registry.sh_activities_management_activity_portal = publicWidget.Widget.extend({
        selector: ".js_cls_schedule_create,.sh_create_activity_view,.sh_activity_view, .sh_activity_list_view, .sh_activity_kanban_view,.js_cls_activity_form_view",        
        events: {
            'click .activity_kanban_layout': '_openkanbanlayout',
            'click .activity_list_layout': '_openlistlayout',
            'click #click_edit_activity': '_editactivityform',
            'refresh .sh_activities_management_activity_portal': '_setdefaullayout',
            'click #click_create_activity': '_create_activity',
            'click .js_cls_save_view': '_save_view',
            'click .js_cls_done_view': '_done_view',
            "click .js_close_popup": "_onCloseClick",
            "click .js_cls_action_done": "_action_done",
            "click .action_cancel": "_action_close",
            "click .js_cls_schedule_activity": "_action_schedule",
            "click .view_cancel": "_action_cancel",
            "click #create_activity": "_action_schedule_create",
            "click #view_schedule_next_schedule":"_schedule_next_create",           
            "change #relt_doc_name": "relt_document_onchange",
            "change #relt_doc_data": "get_doc_name",            
        },

        start: function () {
            this._setdefaullayout();            
            $(".sh_custom_user_ids").multiselect({
                //includeSelectAllOption: true,
                enableCaseInsensitiveFiltering: true,
                selectedClass: 'active',
            });

            return this._super();
        },

        _openkanbanlayout: function (ev) {
            this.$(".sh_activity_list_view").hide();
            this.$('.sh_activity_kanban_view').show();
            this.$('.activity_list_layout').removeClass("add_focus");
            this.$('.activity_kanban_layout').addClass("add_focus");
            window.sessionStorage.removeItem("list");
            window.sessionStorage.setItem('kanban', 'sh_activity_kanban_view');
        },

        _openlistlayout: function (ev) {
            this.$('.sh_activity_kanban_view').hide();
            this.$('.sh_activity_list_view').show();
            this.$('.activity_kanban_layout').removeClass("add_focus");
            this.$('.activity_list_layout').addClass("add_focus");
            window.sessionStorage.removeItem("kanban");
            window.sessionStorage.setItem('list', 'sh_activity_list_view');
        },

        _setdefaullayout: function (ev) {
            if (window.sessionStorage.getItem('kanban')) {
                this._openkanbanlayout();
            }
            else if (window.sessionStorage.getItem('list')) {
                this._openlistlayout();
            }
            else {
                this._openkanbanlayout();
            }

        },
        _create_activity: function (ev) {
            var form = $('.js_cls_schedule_view').find('.js_cls_schedule_create');
            form.modal("show");
        },
        _save_view: function (ev) {
            var $target = $(ev.currentTarget);
            var id = $target.data('id');
            var form = $(ev.currentTarget).closest('.js_cls_activity_form_view').find('.js_cls_form_input');
            var doc_name = form.find("#doc_name").val();
            var due_date = form.find("#duedate").val();
            var rel_doc_name = form.find("#relt_doc_name").val();
            var duedatereminder = form.find("#duedatereminder").val();
            var link_activity_type_id = form.find("#link_activity_type_id").val();
            var assigned_to = form.find("#assigned_to").val();
            var complete_date = form.find("#complete_date").val();
            var user_ids = form.find("#user_ids").val();
            var summary = form.find("#summary").val();
            var supervisor = form.find("#supervisor").val();
            var reminders = form.find("#reminders").val();
            var activity_tags = form.find("#activity_tags").val();
            var lognote = form.find("#lognote").val();
            var act_id = form.find("#act_id").val();
            var vals = {
                'id': id,
                'doc_name': doc_name,
                'due_date': due_date,
                'rel_doc_name': rel_doc_name,
                'duedatereminder': duedatereminder,
                'link_activity_type_id': link_activity_type_id,
                'assigned_to': assigned_to,
                'complete_date': complete_date,
                'user_ids': user_ids,
                'summary': summary,
                'supervisor': supervisor,
                'reminders': reminders,
                'activity_tags': activity_tags,
                'lognote': lognote,
                'act_id': act_id
            }
            $.ajax({
                url: "/save_record_action",
                data: vals,
                type: "post",
                cache: false,
                success: function (result) {
                    var datas = JSON.parse(result);
                    $(ev.currentTarget).closest('.js_cls_activity_form_view').find('.js_cls_msg').removeClass("d-none");
                }
            });
        },        
        _done_view: function (ev) {
            var form = $(ev.currentTarget).closest('.js_cls_activity_form_view').find('.js_cls_feedback');
            form.modal("show");
            var $target = $(ev.currentTarget);
            var id = $target.data('id');
            var assigned_to = form.find("#assigned_to").val();
            var vals = {
                'id': id,
                'assigned_to': assigned_to,
            }
            form.find('#view_done_schedule_feedback')
                .on('click', function (ev) {

                    var form = $(ev.currentTarget).closest('.js_cls_activity_form_view').find('.js_cls_schedule_form_view');
                    form.modal("show");
                });
        },
        _action_done: function (ev) {
            var $target = $(ev.currentTarget);
            var id = $target.data('id');
            var feedback = $(ev.currentTarget).closest('.js_cls_activity_form_view').find('.js_cls_feedback').find("#feedback").val();
            var assigned_to = $(ev.currentTarget).closest('.js_cls_activity_form_view').find('.js_cls_feedback').find("#assigned_to").val();
            var vals = {
                'id': id,
                'feedback': feedback,
                'assigned_to': assigned_to,
            }
            $.ajax({
                url: "/done-activity",
                data: vals,
                type: "post",
                cache: false,
                success: function (result) {
                    var datas = JSON.parse(result);                    
                    if (datas.hasOwnProperty('success')) {
                        var form = $(ev.currentTarget).closest('.js_cls_activity_form_view').find('.js_cls_feedback');
                        form.modal().hide();                        
                        location.reload();
                    }
                    else {
                        var form = $(ev.currentTarget).closest('.js_cls_activity_form_view').find('.js_cls_feedback');
                        form.find("#alert").append("<b>FeedBack is Required!</b>")
                    }
                }
            });
        },
        _action_close: function (ev) {
            var form = $(ev.currentTarget).closest('.js_cls_activity_form_view').find('.js_cls_feedback');
            form.modal().hide();
            location.reload();
        },
        _action_cancel: function (ev) {
            var $target = $(ev.currentTarget);
            var id = $target.data('id');
            var form = $(ev.currentTarget).closest('.js_cls_activity_form_view');
            var assigned_to = form.find("#assigned_to").val();
            var vals = {
                'id': id,
                'assigned_to': assigned_to,
            }
            $.ajax({
                url: "/cancel-activity",
                data: vals,
                type: "post",
                cache: false,
                success: function (result) {
                    var datas = JSON.parse(result);                    
                    if (datas.hasOwnProperty('success')) {                        
                        location.reload();
                    }
                    else {
                        $(ev.currentTarget).closest('.js_cls_activity_form_view').find('.js_cls_msg').removeClass("d-none");
                    }

                }
            });
        },
        _action_schedule_create: function (ev) {           
            var form = $('.js_cls_schedule_view').find('.js_cls_schedule_create');            
            var doc_name = form.find("#doc_name").val();
            var due_date = form.find("#duedate").val();
            var relt_doc_name = form.find("#relt_doc_name").find(":selected").attr("id");
            var relt_doc_data = form.find("#relt_doc_data").find(":selected").attr("id");
            var duedatereminder = form.find("#duedatereminder").val();
            var link_activity_type_id = form.find("#link_activity_type_id").val();
            var assigned_to = form.find("#assigned_to").val();
            var complete_date = form.find("#complete_date").val();
            var user_ids = form.find("#user_ids").val();
            var summary = form.find("#summary").val();
            var supervisor = form.find("#supervisor").val();
            var reminders = form.find("#reminders").val();
            var activity_tags = form.find("#activity_tags").find(":selected").attr("id");
            var lognote = form.find("#lognote").val();
            var act_id = form.find("#act_id").find(":selected").attr("id");
            var vals = {               
                'doc_name': doc_name,
                'due_date': due_date,
                'rel_doc_name': relt_doc_name,
                'relt_doc_data':relt_doc_data,
                'duedatereminder': duedatereminder,
                'link_activity_type_id': link_activity_type_id,
                'assigned_to': assigned_to,
                'complete_date': complete_date,
                'user_ids': user_ids,
                'summary': summary,
                'supervisor': supervisor,
                'reminders': reminders,
                'activity_tags': activity_tags,
                'lognote': lognote,
                'act_id': act_id
            }            
            $.ajax({
                url: "/create_activity",
                data: vals,
                type: "post",
                cache: false,
                success: function (result) {
                    var datas = JSON.parse(result);
                    if (datas.hasOwnProperty('success')){                       
                        location.reload();
                    }   
                }
            });
        },
        _schedule_next_create:function(ev){
            var form = $(ev.currentTarget).closest('.js_cls_schedule_form_view');            
            var doc_name = form.find("#doc_name").val();
            var due_date = form.find("#duedate").val();
            var relt_doc_name = form.find("#relt_doc_name").val();
            var relt_doc_data = form.find("#relt_doc_data").val();
            var duedatereminder = form.find("#duedatereminder").val();
            var link_activity_type_id = form.find("#link_activity_type_id").val();
            var assigned_to = form.find("#assigned_to").val();
            var complete_date = form.find("#complete_date").val();
            var user_ids = form.find("#user_ids").val();
            var summary = form.find("#summary").val();
            var supervisor = form.find("#supervisor").val();
            var reminders = form.find("#reminders").val();
            var activity_tags = form.find("#activity_tags").find(":selected").attr("id");
            var lognote = form.find("#lognote").val();
            var act_id = form.find("#act_id").find(":selected").attr("id");
            var vals = {               
                'doc_name': doc_name,
                'due_date': due_date,
                'rel_doc_name': relt_doc_name,
                'relt_doc_data':relt_doc_data,
                'duedatereminder': duedatereminder,
                'link_activity_type_id': link_activity_type_id,
                'assigned_to': assigned_to,
                'complete_date': complete_date,
                'user_ids': user_ids,
                'summary': summary,
                'supervisor': supervisor,
                'reminders': reminders,
                'activity_tags': activity_tags,
                'lognote': lognote,
                'act_id': act_id
            }            
            $.ajax({
                url: "/create_activity_next",
                data: vals,
                type: "post",
                cache: false,
                success: function (result) {
                    var datas = JSON.parse(result);
                    if (datas.hasOwnProperty('success')){                        
                        location.reload();
                    }                                     
                }
            });
        },
        _action_schedule: function (ev) {
            var $target = $(ev.currentTarget);
            var id = $target.data('id');
            var form = $(ev.currentTarget).closest('.js_cls_activity_form_view')
            var assigned_to = form.find("#assigned_to").val();
            var vals = {
                'id': id,
                'assigned_to': assigned_to,
            }
            $.ajax({
                url: "/done_schedule_next_activity",
                data: vals,
                type: "post",
                cache: false,
                success: function (result) {
                    var datas = JSON.parse(result);                    
                    if (datas.hasOwnProperty('success')) {
                        var form = $(ev.currentTarget).closest('.js_cls_activity_form_view').find('.js_cls_schedule_form_view');                        
                        form.modal("show");
                    }
                }
            });

        },
        _change_model_data: function (ev) {
            var relt_doc_name = $("#relt_doc_name").find(":selected").attr("id");            
            $.ajax({
                url: "/done-activity",
                data: vals,
                type: "post",
                cache: false,
                success: function (result) {
                    var datas = JSON.parse(result);                    
                    if (datas.hasOwnProperty('success')) {
                        var form = $(ev.currentTarget).closest('.js_cls_activity_form_view').find('.js_cls_feedback');
                        form.modal().hide();
                        location.reload();
                    }
                    else {
                        var form = $(ev.currentTarget).closest('.js_cls_activity_form_view').find('.js_cls_feedback');
                        form.find("#alert").append("<b>FeedBack is Required!</b>")
                    }
                }
            });
        },
        relt_document_onchange: function (event) {
            var self = this;            
            var search_id = $("#relt_doc_name").find(":selected").attr("id");           
            self._rpc({
                route: "/relt_document_onchange",
                params: {            
                    'search_id': search_id,
                },
            }).then(function (result) {
                if (result) {
                    var result = JSON.parse(result);                    
                    $("#relt_doc_data").empty();
                    $("#doc_name").empty();

                    var res_id = $("#relt_doc_data").data("res_id");
                    res_id = res_id + "rec_id";
                    var selected_str = "";
                    for (const [key, value] of Object.entries(result)) {
                        if (res_id == key) {
                            selected_str = "selected";
                        } else {
                            selected_str = "";
                        }
                        $("#relt_doc_data").append("<option " + selected_str + ' value="' + key + '" id="' + key + '">' + value + "</option>");
                    }                   
                }
            });
        },

        get_doc_name: function (event) {
            var doc_name = $("#relt_doc_data").find(":selected").text();
            $(document).find("#doc_name").val(doc_name);
        },

        get_relateddocumentdata: function (event) {
            var self = this;
            var dialog_search_id = $("#relateddocument").find(":selected").attr("id");
            self._rpc({
                route: "/get_relateddocumentdata",
                params: {
                    dialog_search_id: dialog_search_id,
                },
            }).then(function (result) {
                if (result) {
                    var result = JSON.parse(result);
                    self.results = result;

                    $("#relateddocumentdata").empty();
                    $("#documentname").empty();
                    for (const [key, value] of Object.entries(result)) {
                        $("#relateddocumentdata").append('<option value="' + key + '" id="' + key + '">' + value + "</option>");
                    }
                }
            });
        },

        get_documentname: function (event) {

            var documentname = $("#relateddocumentdata").find(":selected").text();
            $(document).find("#documentname").val(documentname);

        },
    });
});
