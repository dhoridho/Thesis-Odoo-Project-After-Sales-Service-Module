odoo.define('equip3_hr_recruitment_extend.custom', ['survey.form'], function (require) {
    "use strict";

    var survey = require('survey.form');
    console.log("survey", survey);

    var DataSet = survey.include({


        _submitForm: function (options) {
            var self = this;
            var params = {};
            if (options.previousPageId) {
                params.previous_page_id = options.previousPageId;
            }

            const queryString = window.location.search;
            const urlParams = new URLSearchParams(queryString);
            params['survey_id'] = parseInt(urlParams.get('surveyId'));
            params['applicant_id'] = parseInt(urlParams.get('applicantId'));
            params['job_position'] = parseInt(urlParams.get('jobPosition'));


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
        }


    });

    return {
        DataSet: DataSet,
    };


});



