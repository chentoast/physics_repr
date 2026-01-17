let jsPsychHtmlButtonSliderResponse = (function (jspsych) {
    const info = {
        name: "html-button-slider-response",
        parameters: {
            /** The HTML string to be displayed */
            stimulus: {
                type: jspsych.ParameterType.HTML_STRING,
                pretty_name: "Stimulus",
                default: undefined,
            },
            /** Array containing the label(s) for the button(s). */
            choices: {
                type: jspsych.ParameterType.STRING,
                pretty_name: "Choices",
                default: undefined,
                array: true,
            },
            /** The HTML for creating button. Can create own style. Use the "%choice%" string to indicate where the label from the choices parameter should be inserted. */
            button_html: {
                type: jspsych.ParameterType.HTML_STRING,
                pretty_name: "Button HTML",
                default: '<button class="jspsych-btn">%choice%</button>',
                array: true,
            },
            /** Any content here will be displayed under the button(s). */
            prompt: {
                type: jspsych.ParameterType.HTML_STRING,
                pretty_name: "Prompt",
                default: null,
            },
            /** How long to show the stimulus. */
            stimulus_duration: {
                type: jspsych.ParameterType.INT,
                pretty_name: "Stimulus duration",
                default: null,
            },
            /** How long to show the trial. */
            trial_duration: {
                type: jspsych.ParameterType.INT,
                pretty_name: "Trial duration",
                default: null,
            },
            /** The vertical margin of the button. */
            margin_vertical: {
                type: jspsych.ParameterType.STRING,
                pretty_name: "Margin vertical",
                default: "0px",
            },
            /** The horizontal margin of the button. */
            margin_horizontal: {
                type: jspsych.ParameterType.STRING,
                pretty_name: "Margin horizontal",
                default: "8px",
            },
            /** Sets the minimum value of the slider. */
            min: {
                type: jspsych.ParameterType.INT,
                pretty_name: "Min slider",
                default: 0,
            },
            /** Sets the maximum value of the slider */
            max: {
                type: jspsych.ParameterType.INT,
                pretty_name: "Max slider",
                default: 100,
            },
            /** Sets the starting value of the slider */
            slider_start: {
                type: jspsych.ParameterType.INT,
                pretty_name: "Slider starting value",
                default: 50,
            },
            /** Sets the step of the slider */
            step: {
                type: jspsych.ParameterType.INT,
                pretty_name: "Step",
                default: 1,
            },
            /** Array containing the labels for the slider. Labels will be displayed at equidistant locations along the slider. */
            labels: {
                type: jspsych.ParameterType.HTML_STRING,
                pretty_name: "Labels",
                default: [],
                array: true,
            },
            /** Width of the slider in pixels. */
            slider_width: {
                type: jspsych.ParameterType.INT,
                pretty_name: "Slider width",
                default: null,
            },
            /** Label of the button to advance. */
            button_label: {
                type: jspsych.ParameterType.STRING,
                pretty_name: "Button label",
                default: "Continue",
                array: false,
            },
            /** If true, the participant will have to move the slider before continuing. */
            require_movement: {
                type: jspsych.ParameterType.BOOL,
                pretty_name: "Require movement",
                default: false,
            },
            /** If true, then trial will end when user responds. */
            response_ends_trial: {
                type: jspsych.ParameterType.BOOL,
                pretty_name: "Response ends trial",
                default: true,
            },
        },
    };

    class HtmlButtonSliderResponsePlugin {
        static info = info;

        constructor(jsPsych) {
            this.jsPsych = jsPsych;
        }

        trial(display_element, trial) {
            // display stimulus
            let html =
                '<div id="jspsych-html-button-response-stimulus">' +
                trial.stimulus +
                "</div>";

            //display buttons
            let buttons = [];
            if (Array.isArray(trial.button_html)) {
                if (trial.button_html.length == trial.choices.length) {
                    buttons = trial.button_html;
                } else {
                    console.error(
                        "Error in html-button-response plugin. The length of the button_html array does not equal the length of the choices array"
                    );
                }
            } else {
                for (let i = 0; i < trial.choices.length; i++) {
                    buttons.push(trial.button_html);
                }
            }
            html += '<div id="jspsych-html-button-response-btngroup">';
            for (let i = 0; i < trial.choices.length; i++) {
                let str = buttons[i].replace(/%choice%/g, trial.choices[i]);
                html +=
                    '<div class="jspsych-html-button-response-button" style="display: inline-block; margin:' +
                    trial.margin_vertical +
                    " " +
                    trial.margin_horizontal +
                    '" id="jspsych-html-button-response-button-' +
                    i +
                    '" data-choice="' +
                    i +
                    '">' +
                    str +
                    "</div>";
            }
            html += "</div>";

            //show prompt if there is one
            if (trial.prompt !== null) {
                html += trial.prompt;
            }
            // half of the thumb width value from jspsych.css, used to adjust the label positions
            let half_thumb_width = 7.5;

            html +=
                // '<div id="jspsych-html-slider-response-wrapper" style="margin: 100px 0px;">';
                '<div id="jspsych-html-slider-response-wrapper">';
            // html +=
            //     '<div id="jspsych-html-slider-response-stimulus">' +
            //     trial.stimulus +
            //     "</div>";
            html +=
                '<div class="jspsych-html-slider-response-container" style="position:relative; margin: 1em auto; ';
            if (trial.slider_width !== null) {
                html += "width:" + trial.slider_width + "%;";
            } else {
                html += "width:auto;";
            }
            html += '">';
            html +=
                '<input type="range" class="jspsych-slider" value="' +
                trial.slider_start +
                '" min="' +
                trial.min +
                '" max="' +
                trial.max +
                '" step="' +
                trial.step +
                '" id="jspsych-html-slider-response-response"></input>';
            html += "<div>";
            for (let j = 0; j < trial.labels.length; j++) {
                let label_width_perc = 100 / (trial.labels.length - 1);
                let percent_of_range = j * (100 / (trial.labels.length - 1));
                let percent_dist_from_center =
                    ((percent_of_range - 50) / 50) * 100;
                let offset =
                    (percent_dist_from_center * half_thumb_width) / 100;
                html +=
                    '<div style="border: 1px solid transparent; display: inline-block; position: absolute; ' +
                    "left:calc(" +
                    percent_of_range +
                    "% - (" +
                    label_width_perc +
                    "% / 2) - " +
                    offset +
                    "px); text-align: center; width: " +
                    label_width_perc +
                    '%;">';
                html +=
                    '<span style="text-align: center; font-size: 80%;">' +
                    trial.labels[j] +
                    "</span>";
                html += "</div>";
            }
            html += "</div>";
            html += "</div>";
            html += "</div>";

            // add submit button
            html +=
                '<button id="jspsych-html-slider-response-next" class="jspsych-btn" ' +
                (trial.require_movement ? "disabled" : "") +
                ">" +
                trial.button_label +
                "</button>";
            display_element.innerHTML = html;

            // add event listeners to buttons
            for (let i = 0; i < trial.choices.length; i++) {
                display_element
                    .querySelector("#jspsych-html-button-response-button-" + i)
                    .addEventListener("click", (e) => {
                        let btn_el = e.currentTarget;
                        let choice = btn_el.getAttribute("data-choice"); // don't use dataset for jsdom compatibility
                        button_after_response(choice);
                    });
            }

            // store response
            let response = {
                rt: null,
                button: null,
                response: null,
            };

            // function to handle responses by the subject
            function button_after_response(choice) {
                response.button = parseInt(choice);

                // draw a border around the selected button, and clear any other borders
                display_element.querySelectorAll(
                    "#jspsych-html-button-response-btngroup button"
                ).forEach(e => e.style.border = "");
                display_element.querySelector(
                    "#jspsych-html-button-response-button-" +
                        response.button +
                        " button"
                ).style.border = "2px solid black";
            }

            if (trial.require_movement) {
                const enable_button = () => {
                    console.log(response.button)
                    if (response.button === null) {
                        return;
                    }
                    display_element.querySelector(
                        "#jspsych-html-slider-response-next"
                    ).disabled = false;
                };

                display_element
                    .querySelector("#jspsych-html-slider-response-response")
                    .addEventListener("mousedown", enable_button);

                display_element
                    .querySelector("#jspsych-html-slider-response-response")
                    .addEventListener("touchstart", enable_button);

                display_element
                    .querySelector("#jspsych-html-slider-response-response")
                    .addEventListener("change", enable_button);
            }

            display_element
                .querySelector("#jspsych-html-slider-response-next")
                .addEventListener("click", () => {
                    // measure response time
                    let end_time = performance.now();
                    response.rt = Math.round(end_time - start_time);
                    response.response = display_element.querySelector(
                        "#jspsych-html-slider-response-response"
                    ).valueAsNumber;

                    if (trial.response_ends_trial) {
                        end_trial();
                    } else {
                        display_element.querySelector(
                            "#jspsych-html-slider-response-next"
                        ).disabled = true;
                    }
                });

            // function to end trial when it is time
            const end_trial = () => {
                // kill any remaining setTimeout handlers
                this.jsPsych.pluginAPI.clearAllTimeouts();

                // gather the data to store for the trial
                let trial_data = {
                    rt: response.rt,
                    stimulus: trial.stimulus,
                    choice_response: response.button,
                    slider_response: response.response,
                    slider_start: trial.slider_start,
                };

                // clear the display
                display_element.innerHTML = "";

                // move on to the next trial
                this.jsPsych.finishTrial(trial_data);
            };

            // start time
            let start_time = performance.now();
        }
    }

    return HtmlButtonSliderResponsePlugin;
})(jsPsychModule);

//   // hide image if timing is set
//   if (trial.stimulus_duration !== null) {
//     this.jsPsych.pluginAPI.setTimeout(() => {
//       display_element.querySelector(
//         "#jspsych-html-button-response-stimulus"
//       ).style.visibility = "hidden";
//     }, trial.stimulus_duration);
//   }

//   // end trial if time limit is set
//   if (trial.trial_duration !== null) {
//     this.jsPsych.pluginAPI.setTimeout(end_trial, trial.trial_duration);
//   }
