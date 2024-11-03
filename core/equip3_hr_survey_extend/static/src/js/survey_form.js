odoo.define('equip3_hr_survey_extend.survey.form', ['survey.form','web.core','web.time'], function (require) {
    "use strict";

    var core = require('web.core');
    var survey = require('survey.form');
    var time = require('web.time');
    var _t = core._t;

    var DataSet = survey.include({

        events: _.extend({}, survey.prototype.events, {
            'click td.o_survey_matrix_btn': '_checkTdRadioButtonClick',
        }),


         getBase64:function(file) {
            return new Promise(function(resolve, reject) {
                var reader = new FileReader();
                reader.onload = function() { resolve(reader.result); };
                reader.onerror = reject;
                reader.readAsDataURL(file);
            });
        },
          

        _checkTdRadioButtonClick: function (ev) {
            if($(ev.target).hasClass('fa')) {
                if ($($(ev.target).parents()[3]).data('question-type') == 'disc') {
                    var indextd = $($(ev.target).parent()).index() +1
                    $($(ev.target).parents()[3]).find('td:nth-child('+indextd+') .o_survey_form_choice_item').prop( "checked", false );
                    $($(ev.target).parents()[3]).find('td:nth-child('+indextd+')').removeClass('o_survey_selected');
                    $($($(ev.target).parent()).find('.o_survey_form_choice_item')).prop( "checked", true );
                    $($(ev.target).parent()).addClass('o_survey_selected')

                }

            }
            else{
                if ($($(ev.target).parents()[2]).data('question-type') == 'disc') {
                    var indextd = $(ev.target).index() +1
                    $($(ev.target).parents()[2]).find('td:nth-child('+indextd+') .o_survey_form_choice_item').prop( "checked", false );
                    $($(ev.target).parents()[2]).find('td:nth-child('+indextd+')').removeClass('o_survey_selected');
                    $($(ev.target).find('.o_survey_form_choice_item')).prop( "checked", true );
                    $(ev.target).addClass('o_survey_selected')

                }
            }
                
        },


        
    
        /**
        * Check if the email has an '@', a left part and a right part
        * @private
        */
        _validateEmail: function (email) {
            var emailParts = email.split('@');
            return emailParts.length === 2 && emailParts[0] && emailParts[1];
        },


        _prepareSubmitValues: function (formData, params) {
        var self = this;
        
        
        

        formData.forEach(function (value, key) {
            switch (key) {
                case 'csrf_token':
                case 'token':
                case 'page_id':
                case 'question_id':
                    params[key] = value;
                    break;
            }
        });
        // Get all question answers by question type
        this.$('[data-question-type]').each(function () {
            switch ($(this).data('questionType')) {
                case 'text_box':
                case 'char_box':
                case 'numerical_box':
                    params[this.name] = this.value;
                    break;
                case 'date':
                    params = self._prepareSubmitDates(params, this.name, this.value, false);
                    break;
                case 'datetime':
                    params = self._prepareSubmitDates(params, this.name, this.value, true);
                    break;
                case 'simple_choice_radio':
                case 'epps':
                case 'papikostick':
                case 'ist':
                case 'mbti':
                case 'vak':
                case 'multiple_choice':
                    params = self._prepareSubmitChoices(params, $(this), $(this).data('name'));
                    break;
                case 'matrix':
                case 'disc':
                    params = self._prepareSubmitAnswersMatrix(params, $(this));
                    break;
                case 'file':
                    var $input = $(this);       
                    var name = this.name
                    var file = $input[0].files[0]; 
                    var reader = new FileReader();
                    if (file) {
                        const reader = new FileReader();
                        reader.onload = function(evt) { 
                          var route = "/survey/save/files";
                          const metadata = `name: ${file.name}, type: ${file.type}, size: ${file.size}, contents:`;
                          const contents = evt.target.result;
                          params['base64'] = String(contents).split(',')[1];;
                          params['file_name'] = file.name
                          params['question'] = name
                          var submitPromise = self._rpc({
                                    route: _.str.sprintf('%s/%s/%s', route, self.options.surveyToken, self.options.answerToken),
                                    params: params,
                                });
                        };
                        reader.readAsDataURL(file);
                      }
                      break;
                // case 'video':
                //     var $input = $(this);       
                //     var name = this.name
                //     var file = $input[0].files[0]; 
                //     var reader = new FileReader();
                //     if (file) {
                //         const reader = new FileReader();
                //         reader.onload = function(evt) { 
                //           var route = "/survey/save/videofiles";
                //           const metadata = `name: ${file.name}, type: ${file.type}, size: ${file.size}, contents:`;
                //           const contents = evt.target.result;
                //           params['base64'] = String(contents).split(',')[1];;
                //           params['file_name'] = file.name
                //           params['question'] = name
                //           var submitPromise = self._rpc({
                //                     route: _.str.sprintf('%s/%s/%s', route, self.options.surveyToken, self.options.answerToken),
                //                     params: params,
                //                 });
                //         };
                //         reader.readAsDataURL(file);
                //       }
                //       break;
            }
        });
    },


        _validateForm: function ($form, formData) {
        var self = this;
        var errors = {};
        var validationEmailMsg = _t("This answer must be an email address.");
        var validationDateMsg = _t("This is not a date");

        this._resetErrors();

        var data = {};
        formData.forEach(function (value, key) {
            data[key] = value;
        });

        var inactiveQuestionIds = this.options.sessionInProgress ? [] : this._getInactiveConditionalQuestionIds();

        $form.find('[data-question-type]').each(function () {

            var $input = $(this);
            var $questionWrapper = $input.closest(".js_question-wrapper");
            var questionId = $questionWrapper.attr('id');

            // If question is inactive, skip validation.
            if (inactiveQuestionIds.includes(parseInt(questionId))) {
                return;
            }

            var questionRequired = $questionWrapper.data('required');
            var constrErrorMsg = $questionWrapper.data('constrErrorMsg');
            var validationErrorMsg = $questionWrapper.data('validationErrorMsg');
            switch ($input.data('questionType')) {
                case 'char_box':
                    if (questionRequired && !$input.val()) {
                        errors[questionId] = constrErrorMsg;
                    } else if ($input.val() && $input.attr('type') === 'email' && !self._validateEmail($input.val())) {
                        errors[questionId] = validationEmailMsg;
                    } else {
                        var lengthMin = $input.data('validationLengthMin');
                        var lengthMax = $input.data('validationLengthMax');
                        var length = $input.val().length;
                        if (lengthMin && (lengthMin > length || length > lengthMax)) {
                            errors[questionId] = validationErrorMsg;
                        }
                    }
                    break;
                case 'numerical_box':
                    if (questionRequired && !data[questionId]) {
                        errors[questionId] = constrErrorMsg;
                    } else {
                        var floatMin = $input.data('validationFloatMin');
                        var floatMax = $input.data('validationFloatMax');
                        var value = parseFloat($input.val());
                        if (floatMin && (floatMin > value || value > floatMax)) {
                            errors[questionId] = validationErrorMsg;
                        }
                    }
                    break;
                case 'date':
                case 'datetime':
                    if (questionRequired && !data[questionId]) {
                        errors[questionId] = constrErrorMsg;
                    } else if (data[questionId]) {
                        var datetimepickerFormat = $input.data('questionType') === 'datetime' ? time.getLangDatetimeFormat() : time.getLangDateFormat();
                        var momentDate = moment($input.val(), datetimepickerFormat);
                        if (!momentDate.isValid()) {
                            errors[questionId] = validationDateMsg;
                        } else {
                            var $dateDiv = $questionWrapper.find('.o_survey_form_date');
                            var maxDate = $dateDiv.data('maxdate');
                            var minDate = $dateDiv.data('mindate');
                            if ((maxDate && momentDate.isAfter(moment(maxDate)))
                                    || (minDate && momentDate.isBefore(moment(minDate)))) {
                                errors[questionId] = validationErrorMsg;
                            }
                        }
                    }
                    break;
                case 'simple_choice_radio':
                case 'epps':
                case 'papikostick':
                case 'ist':
                case 'mbti':
                case 'vak':
                case 'multiple_choice':
                    if (questionRequired) {
                        var $textarea = $questionWrapper.find('textarea');
                        if (!data[questionId]) {
                            errors[questionId] = constrErrorMsg;
                        } else if (data[questionId] === '-1' && !$textarea.val()) {
                            // if other has been checked and value is null
                            errors[questionId] = constrErrorMsg;
                        }
                    }
                    break;
                case 'matrix':
                case 'disc':
                    if (questionRequired) {
                        var subQuestionsIds = $questionWrapper.find('table').data('subQuestions');
                        subQuestionsIds.forEach(function (id) {
                            if (!((questionId + '_' + id) in data)) {
                                errors[questionId] = constrErrorMsg;
                            }
                        });
                    }
                
                case 'file':
                    if (questionRequired && !$input.val()) {
                        errors[questionId] = constrErrorMsg;
                    }    
                    if ($input.val()) {
                        var _validFileExtensions = [".pdf", ".xls", ".rar", ".doc", ".xlsx",".docx",".jpg",".zip",".png",".mp4"];
                        var sFileName = $input[0].value;
                        const fileSize = $input[0].files[0].size / 1024 / 1024;
                        if (fileSize > $input.data('maxFile')) {
                            errors[questionId] = "file cannot be more than " + $input.data('maxFile') + " mb";

                        }
                        if(!$input.data('pdfFile')){
                            _validFileExtensions = _validFileExtensions.filter(function(e) { return e !== '.pdf' });
                        }
                        if(!$input.data('xlsFile')){
                            _validFileExtensions = _validFileExtensions.filter(function(e) { return e !== '.xls' });
                        }
                        if(!$input.data('rarFile')){
                            _validFileExtensions = _validFileExtensions.filter(function(e) { return e !== '.rar' });
                        }
                         if(!$input.data('docFile')){
                            _validFileExtensions = _validFileExtensions.filter(function(e) { return e !== '.doc' });
                        }

                         if(!$input.data('xlsxFile')){
                            _validFileExtensions = _validFileExtensions.filter(function(e) { return e !== '.xlsx' });
                        }

                         if(!$input.data('docxFile')){
                            _validFileExtensions = _validFileExtensions.filter(function(e) { return e !== '.docx' });
                        }
                         if(!$input.data('jpgFile')){
                            _validFileExtensions = _validFileExtensions.filter(function(e) { return e !== '.jpg' });
                        } if(!$input.data('zipFile')){
                            _validFileExtensions = _validFileExtensions.filter(function(e) { return e !== '.zip' });
                        }if(!$input.data('pngFile')){
                            _validFileExtensions = _validFileExtensions.filter(function(e) { return e !== '.png' });
                        }
                        if(!$input.data('mp4File')){
                            _validFileExtensions = _validFileExtensions.filter(function(e) { return e !== '.mp4' });
                        }
                        if (sFileName.length > 0) {
                            var blnValid = false;
                            for (var j = 0; j < _validFileExtensions.length; j++) {
                                var sCurExtension = _validFileExtensions[j];
                                if (sFileName.substr(sFileName.length - sCurExtension.length, sCurExtension.length).toLowerCase() === sCurExtension.toLowerCase()) {
                                    blnValid = true;
                                    break;
                                }
                            }

                            if (!blnValid) {
                                errors[questionId] = "Sorry, " + $input[0].files[0].name + " is invalid, allowed extensions are: " + _validFileExtensions.join(", ");
                            }
                        }


                    }


                    break;
                
            }
        });
        if (_.keys(errors).length > 0) {
            this._showErrors(errors);
            return false;
        }
        return true;
    }


    });

    return {
        DataSet: DataSet,
    };


});



