odoo.define('equip3_school_portal.SurveyForm', function (require) {
'use strict';

    var field_utils = require('web.field_utils');
    var publicWidget = require('web.public.widget');
    var session = require('web.session');
    require('survey.form');

    publicWidget.registry.SurveyFormWidget.include({
        _submitForm: function (options) {
            var self = this;
            var params = {};
            if (options.previousPageId) {
                params.previous_page_id = options.previousPageId;
            }
            if (sessionStorage.exam_id !== undefined) {
                params.exam_id = sessionStorage.exam_id;
            }
            if (sessionStorage.assignment_id !== undefined) {
                params.assignment_id = sessionStorage.assignment_id;
            }
            if (sessionStorage.additional_id !== undefined) {
                params.additional_id = sessionStorage.additional_id;
            }
            var route = "/survey/submit";

            if (this.options.isStartScreen) {
                route = "/survey/begin";
                // Hide survey title in 'page_per_question' layout: it takes too much space
                if (this.options.questionsLayout === 'page_per_question') {
                    this.$('.o_survey_main_title').fadeOut(400);
                }
            } else {
                var $form = this.$('form');
                var formData = new FormData($form[0]);

                if (!options.skipValidation) {
                    // Validation pre submit
                    if (!this._validateForm($form, formData)) {
                        return;
                    }
                }

                this._prepareSubmitValues(formData, params);
            }

            // prevent user from submitting more times using enter key
            this.preventEnterSubmit = true;

            if (this.options.sessionInProgress) {
                // reset the fadeInOutDelay when attendee is submitting form
                this.fadeInOutDelay = 400;
                // prevent user from clicking on matrix options when form is submitted
                this.readonly = true;
            }

            var submitPromise = self._rpc({
                route: _.str.sprintf('%s/%s/%s', route, self.options.surveyToken, self.options.answerToken),
                params: params,
            });
            this._nextScreen(submitPromise, options);
        },
        _validateForm: function ($form, formData) {
            var result = this._super.apply(this, arguments);
            if (!$('input.survey_form_submit').prop('checked') && result &&
                $('button[type="submit"]').val() == "finish") {
                $("#submit_modal_survey").modal("show");
            }
            else {
                return result;
            }
        },
    });
});